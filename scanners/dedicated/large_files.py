#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描 C 盘中的大文件

优先通过 NTFS 主文件表（MFT）直接读取全盘的文件条目，
无需递归遍历目录即可获得所有活跃文件的大小与路径，速度更快。

当 mftparser 不可用（未安装）或读取 MFT 失败（例如缺少管理员权限）时，
自动回退到基于 os.scandir 的目录遍历方案，保证功能可用。

MFT 可用性由 ScanStrategyContext 统一判断（context.mft_entries() 不可用时返回 None），
本模块只负责拿到条目后的业务处理与回退。
"""

import os
import datetime
import heapq
import itertools
import threading
import concurrent.futures

from scanners.scan_strategy import ScanStrategy, logger
from scanners.mft_scan_strategy import IDX_PATH, IDX_SIZE, IDX_IS_DIR


class LargeFilesScanner(ScanStrategy):
    key = 'large_files'
    display_name = '大文件 (>100MB)'

    MIN_SIZE = 100 * 1024 * 1024   # 只关注 >= 100MB 的文件
    MAX_RESULTS = 100              # 最多保留 100 个结果

    # 不统计的文件类型（小写，含点）
    _EXCLUDE_EXTENSIONS = {
        '.sys', '.dll', '.exe', '.msi', '.mui', '.idx', '.cat', '.db',
    }

    def scan(self, context):
        entries = context.mft_entries()
        if entries is not None:
            items = self._select_from_entries(entries, context)
        else:
            logger.info("MFT 方式不可用，回退到目录遍历扫描大文件")
            items = self._scan_walk(context)

        context.extend(self.key, items)
        logger.info(f"找到 {len(items)} 个大文件")

    # ------------------------------------------------------------------
    # 方式一：MFT（推荐，需管理员权限 + mftparser）
    # ------------------------------------------------------------------
    def _select_from_entries(self, entries, context):
        """从全盘 MFT 条目中挑出最大的若干文件"""
        exclude_exact, exclude_prefixes = self._build_excludes(context)

        candidates = []
        for entry in entries:
            try:
                if entry[IDX_IS_DIR]:
                    continue
                size = entry[IDX_SIZE]
                if size < self.MIN_SIZE:
                    continue
                path = entry[IDX_PATH]
            except (IndexError, TypeError):
                continue

            if not path:
                continue

            ext = os.path.splitext(path)[1].lower()
            if ext in self._EXCLUDE_EXTENSIONS:
                continue

            lower = path.lower()
            if lower in exclude_exact or lower.startswith(exclude_prefixes):
                continue

            candidates.append({
                'path': path,
                'size': size,
                'type': self.key,
                'extension': ext,
            })

        items = heapq.nlargest(self.MAX_RESULTS, candidates, key=lambda it: it['size'])
        self._attach_modified(items)
        return items

    def _build_excludes(self, context):
        """构建需要排除的目录集合（系统目录 + 安全目录）"""
        dirs = {
            os.path.join('C:', os.sep, 'Windows'),
            os.path.join('C:', os.sep, 'Program Files', 'WindowsApps'),
            os.path.join('C:', os.sep, 'Program Files (x86)', 'WindowsApps'),
            os.path.join('C:', os.sep, '$Recycle.Bin'),
        }
        for p in context.safe_paths:
            if p:
                dirs.add(os.path.normpath(p))

        # 精确匹配目录本身 + 前缀匹配其子路径
        exact = {d.lower() for d in dirs}
        prefixes = tuple(d.lower() + os.sep for d in dirs)
        return exact, prefixes

    @staticmethod
    def _attach_modified(items):
        """用文件系统时间补充修改时间（仅对最终保留的少量结果做 stat）"""
        for it in items:
            try:
                mtime = os.stat(it['path']).st_mtime
            except OSError:
                continue
            it['modified'] = datetime.datetime.fromtimestamp(mtime).strftime(
                '%Y-%m-%d %H:%M:%S'
            )

    # ------------------------------------------------------------------
    # 方式二：目录遍历（回退方案）
    # ------------------------------------------------------------------
    def _scan_walk(self, context):
        """基于 os.scandir 的目录遍历（MFT 不可用时使用）

        性能要点：
        1. 复用 DirEntry 已缓存的 stat 信息，避免多次系统调用；
        2. 进入目录前剪枝排除目录与安全目录；
        3. 用最小堆只保留最大的 N 个文件；
        4. 多个根目录并行遍历，隐藏磁盘 I/O 延迟。
        """
        scan_dirs = [
            os.path.join('C:', os.sep, 'Users'),
            os.path.join('C:', os.sep, 'Program Files'),
            os.path.join('C:', os.sep, 'Program Files (x86)'),
            os.path.join('C:', os.sep, 'ProgramData'),
        ]

        # 直接跳过的目录（统一小写比较，避免大小写差异）
        exclude_dirs = {
            os.path.join('C:', os.sep, 'Windows').lower(),
            os.path.join('C:', os.sep, 'Program Files', 'WindowsApps').lower(),
            os.path.join('C:', os.sep, 'Program Files (x86)', 'WindowsApps').lower(),
            os.path.join('C:', os.sep, '$Recycle.Bin').lower(),
        }

        # 安全目录：遍历时直接剪枝
        safe_roots = {
            os.path.normpath(p).lower() for p in context.safe_paths if p
        }
        prune_prefixes = tuple(r + os.sep for r in safe_roots)

        # 最小堆维护最大的 MAX_RESULTS 个文件：(size, seq, item)
        heap = []
        heap_lock = threading.Lock()
        seq = itertools.count()

        def record(item):
            with heap_lock:
                if len(heap) < self.MAX_RESULTS:
                    heapq.heappush(heap, (item['size'], next(seq), item))
                elif item['size'] > heap[0][0]:
                    heapq.heapreplace(heap, (item['size'], next(seq), item))

        def walk(root):
            """基于 os.scandir 的迭代式遍历"""
            stack = [root]
            while stack:
                current = stack.pop()
                try:
                    with os.scandir(current) as entries:
                        for entry in entries:
                            try:
                                if entry.is_dir(follow_symlinks=False):
                                    # 跳过符号链接/联接点，避免循环
                                    if entry.is_symlink():
                                        continue
                                    lower = entry.path.lower()
                                    if lower in exclude_dirs or lower in safe_roots \
                                            or lower.startswith(prune_prefixes):
                                        continue
                                    stack.append(entry.path)

                                elif entry.is_file(follow_symlinks=False):
                                    ext = os.path.splitext(entry.name)[1].lower()
                                    if ext in self._EXCLUDE_EXTENSIONS:
                                        continue
                                    # DirEntry.stat 在 Windows 上读取的是目录枚举时缓存的
                                    # 元数据，几乎不产生额外系统调用
                                    stat = entry.stat(follow_symlinks=False)
                                    size = stat.st_size
                                    if size >= self.MIN_SIZE:
                                        record({
                                            'path': entry.path,
                                            'size': size,
                                            'type': self.key,
                                            'modified': datetime.datetime.fromtimestamp(
                                                stat.st_mtime
                                            ).strftime('%Y-%m-%d %H:%M:%S'),
                                            'extension': ext,
                                        })
                            except (PermissionError, FileNotFoundError, OSError):
                                continue
                except (PermissionError, FileNotFoundError, OSError) as e:
                    logger.warning(f"无法扫描目录 {current}: {e}")

        # 逐个检查根目录是否可扫描（保持原有安全策略）
        targets = [
            d for d in scan_dirs
            if os.path.exists(d) and context.is_safe_path(d)
        ]

        if targets:
            # 各根目录并行遍历（I/O 密集）
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(len(targets), 4)
            ) as executor:
                list(executor.map(walk, targets))

        return [
            item for _, _, item in sorted(heap, key=lambda x: x[0], reverse=True)
        ]
