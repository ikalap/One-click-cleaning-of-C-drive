#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描策略上下文

集中管理扫描策略实例，并协调通用扫描后端（MFT 或 IO）的选择：

- 策略实例管理：维护「通用策略 + 各专用策略」的实例集合；
- 后端协调：通用扫描优先使用 MFT 策略（MftDirectoryScanner），当 mftparser
  缺失、缺少管理员权限或磁盘非 NTFS 时，回退到 IO(os.walk) 策略
  （按通用 key 逐个创建 DirectoryScanner）；
- 扫描调度：提供统一的 scan() 入口，负责并发执行各策略并按 key 上报进度。

原 CleanerLogic.scan_system() 中的策略调度逻辑已迁移至此，
CleanerLogic 只需创建一个 ScanStrategyContext 并调用 scan()。
"""

import os
import logging
import importlib
import threading
import concurrent.futures

from .scan_targets_config import SCAN_TARGETS
from .io_scan_strategy import IoScanStrategy
from .mft_scan_strategy import (
    MftBackend,
    MftScanStrategy,
    GENERAL_KEYS,
    mftparser,
)

logger = logging.getLogger('CCleaner')

# 所有扫描结果的 key，与 UI 分类保持一致（顺序即展示顺序）
ALL_RESULT_KEYS = list(SCAN_TARGETS.keys())


def build_dedicated_strategies():
    """按 SCAN_TARGETS 的 dedicated 字段实例化各专用策略"""
    strategies = []

    for spec in SCAN_TARGETS.values():
        path = spec.get('dedicated')
        if not path:
            continue
        module_name, class_name = path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        strategies.append(getattr(module, class_name)())

    return strategies


class ScanProgress:
    """扫描进度追踪与上报

    集中管理进度状态（总数 / 已完成 / 进行中）与线程安全，并通过 callback
    统一上报。扫描调度代码只需调用 start()/finish()/notify()，
    无需关心状态细节，从而与上报逻辑解耦。

    callback 签名与 UI 约定一致：
        callback(completed, total, active, finished_key, items)
    """

    def __init__(self, total, callback=None):
        self.total = total
        self.callback = callback
        self._lock = threading.Lock()
        self._completed = 0
        self._active = set()

    def _emit(self, finished_key=None, items=None):
        """以当前状态快照调用一次 callback"""
        if not self.callback:
            return
        with self._lock:
            completed = self._completed
            active = sorted(self._active)
        self.callback(completed, self.total, active, finished_key, items or [])

    def notify(self):
        """主动上报当前进度快照（如扫描起始状态）"""
        self._emit()

    def start(self, keys):
        """标记一组 key 进入扫描中"""
        with self._lock:
            self._active.update(keys)
        self._emit()

    def finish(self, key, items):
        """标记单个 key 扫描完成，并上报该分类的结果"""
        with self._lock:
            self._active.discard(key)
            self._completed += 1
        self._emit(key, items)


class ScanStrategyContext:
    """扫描策略上下文

    职责：
    1. 管理扫描策略实例（1 个通用策略 + N 个专用策略）；
    2. 协调通用扫描使用 MFT 策略还是 IO(os.walk) 策略；
    3. 作为扫描上下文，向各策略提供共享结果容器与安全路径判断；
    4. 统一执行扫描、并发调度并向 UI 上报进度，最终返回扫描结果。
    """

    def __init__(self, safe_paths=None, results=None, prefer_mft=True):
        """
        参数：
            safe_paths: 安全路径列表，用于过滤系统关键目录
            results:    结果字典，缺省时按 ALL_RESULT_KEYS 初始化
            prefer_mft: 是否优先使用 MFT 策略（False 时直接走 IO）
        """
        self.safe_paths = safe_paths or []
        self.results = (
            results if results is not None
            else {key: [] for key in ALL_RESULT_KEYS}
        )
        self.prefer_mft = prefer_mft

        # MFT 后端状态：懒加载，当前上下文只探测/加载一次
        self._mft_lock = threading.Lock()
        self._mft_checked = False
        self._mft_entries = None

        # 策略实例（build_strategies() 后填充）
        self.general_strategies = []
        self.dedicated_strategies = []

    # ------------------------------------------------------------------
    # 结果容器与安全路径判断（所有扫描策略共享）
    # ------------------------------------------------------------------
    def add(self, key, item):
        """向结果字典中追加一条记录"""
        self.results.setdefault(key, []).append(item)

    def extend(self, key, items):
        """向结果字典中批量追加记录"""
        self.results.setdefault(key, []).extend(items)

    def is_safe_path(self, path):
        """检查路径是否安全（不在系统关键目录中）"""
        for safe_path in self.safe_paths:
            if path.startswith(safe_path):
                return False

        system_dirs = [
            os.path.join('C:', os.sep, 'Windows'),
            os.path.join('C:', os.sep, 'Program Files'),
            os.path.join('C:', os.sep, 'Program Files (x86)'),
            os.path.join('C:', os.sep, 'ProgramData'),
        ]
        for sys_dir in system_dirs:
            if path == sys_dir:
                return False
        return True

    # ------------------------------------------------------------------
    # 策略实例管理
    # ------------------------------------------------------------------
    @property
    def strategies(self):
        """全部策略实例：通用策略 + 专用策略"""
        return list(self.general_strategies) + list(self.dedicated_strategies)

    def build_strategies(self):
        """实例化全部策略，返回策略列表

        - 通用策略由 _select_general_strategies() 协调（MFT 或 IO）；
        - 专用策略复用本模块的 build_dedicated_strategies()。
        """
        self.general_strategies = self._select_general_strategies()
        self.dedicated_strategies = build_dedicated_strategies()
        return self.strategies

    def _select_general_strategies(self):
        """协调通用扫描策略：优先 MFT，不可用则回退 IO(os.walk)"""
        if self.prefer_mft and self._mft_supported():
            logger.info("通用扫描使用 MFT 策略")
            return [MftScanStrategy()]

        logger.info("通用扫描使用 IO(os.walk) 策略")
        # 通用扫描没有单一 IO 策略类，按通用 key 各建一个 DirectoryScanner
        return [
            IoScanStrategy(key=key, spec=SCAN_TARGETS[key])
            for key in GENERAL_KEYS
        ]

    # ------------------------------------------------------------------
    # MFT 可用性协调（统一委托到本上下文处理）
    # ------------------------------------------------------------------
    @staticmethod
    def _mft_supported():
        """是否具备使用 MFT 的基本条件：mftparser 是否已安装"""
        return mftparser is not None

    def _ensure_mft_entries(self):
        """加载 MFT 条目并缓存（当前上下文只做一次）

        返回 True 表示 MFT 可用；False 表示不可用（已记录原因），
        调用方据此决定是否回退到 IO(os.walk) 扫描。
        """
        with self._mft_lock:
            if self._mft_checked:
                return self._mft_entries is not None

            self._mft_checked = True
            if not self._mft_supported():
                logger.info("未安装 mftparser，使用目录遍历方式扫描")
                return False

            try:
                self._mft_entries = MftBackend.load_entries()
            except Exception as e:
                logger.warning(
                    "MFT 扫描失败，改用目录遍历"
                    f"（可能需要管理员权限，或磁盘不是 NTFS）: {e}"
                )
                self._mft_entries = None

            return self._mft_entries is not None

    def mft_entries(self):
        """获取 MFT 原始条目（供通用扫描与大文件策略复用）；不可用时返回 None"""
        self._ensure_mft_entries()
        return self._mft_entries

    # ------------------------------------------------------------------
    # 扫描调度
    # ------------------------------------------------------------------
    def scan(self, progress_callback=None):
        """执行全部扫描策略，返回结果字典

        参数：
            progress_callback: 可选，扫描进度回调。扫描器开始/完成时各调用一次，
                          签名为 callback(completed, total, active, finished_key, items)：
                          completed 已完成的扫描器数量，total 扫描器总数，
                          active 当前正在扫描的扫描器键列表，
                          finished_key 刚完成的扫描器键（开始通知时为 None），
                          items 该扫描器找到的项目列表（开始通知时为 []）。
        """
        logger.info("开始扫描系统")

        # 协调并实例化各扫描策略（scanners/*.py）
        # 一个策略可负责多个结果 key，进度按 key 数统计
        strategies = self.build_strategies()
        progress = ScanProgress(
            total=sum(len(s.keys) for s in strategies),
            callback=progress_callback,
        )

        # 通知起始状态（0/total）
        progress.notify()

        # 并发执行全部扫描策略
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_strategy = {
                executor.submit(self._run_strategy, strategy, progress): strategy
                for strategy in strategies
            }

            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    future.result()  # 任务期间发生的任何异常
                    logger.info(f"Task {strategy.keys} completed successfully.")
                except Exception as exc:
                    logger.error(
                        f'Task {strategy.keys} generated an exception: {exc}'
                    )

        results = self.results
        logger.info(
            f"扫描完成，找到 "
            f"{sum(len(items) for items in results.values())} 个可清理项目"
        )
        return results

    def _run_strategy(self, strategy, progress):
        """执行单个扫描策略，并把各 key 的进度交由 progress 上报"""
        keys = strategy.keys
        progress.start(keys)
        try:
            if isinstance(strategy, MftScanStrategy) and not self._ensure_mft_entries():
                # 协调：MFT 通用策略不可用时回退到 IO(os.walk)
                self._scan_general_with_io(keys)
            else:
                strategy.scan(self)
        finally:
            # 无论成功与否都算完成，并实时上报该分类结果
            for key in keys:
                progress.finish(key, list(self.results.get(key, [])))

    def _scan_general_with_io(self, keys):
        """通用扫描回退：按 key 逐个使用 IO(os.walk) 策略扫描"""
        for key in keys:
            IoScanStrategy(key=key, spec=SCAN_TARGETS[key]).scan(self)
