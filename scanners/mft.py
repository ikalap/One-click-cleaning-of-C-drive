#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""基于 NTFS 主文件表（MFT）的通用扫描后端

对整卷 C 盘只解析一次 MFT，得到所有活跃文件条目，再按
targets.SCAN_TARGETS 中的通用规则一次性分发，产出各分类结果。

MftDirectoryScanner 与 generic.DirectoryScanner 功能等价，但优先使用 MFT；
当 mftparser 未安装、缺少管理员权限或磁盘非 NTFS 时，
MftDirectoryScanner 会自动回退到 os.walk 的 DirectoryScanner。
"""

import os
import re
import fnmatch
import datetime
import threading

from .base import ScanStrategy, logger
from .generic import DirectoryScanner
from .targets import SCAN_TARGETS

try:
    import mftparser
except ImportError:  # 未安装 mftparser 时统一回退到目录遍历
    mftparser = None

# mftparser.ScanVolume() 返回元组的字段索引（实测顺序）
IDX_PATH = 6      # 文件完整路径
IDX_SIZE = 7      # 文件大小（字节）
IDX_IS_DIR = 8    # 是否为目录

_GLOB_CHARS = ('*', '?', '[')
_ENV_VAR_RE = re.compile(r'%([^%]+)%')


def _expand_env(raw):
    """展开 %ENVVAR% 形式的环境变量，变量缺失时返回空串"""
    return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), ''), raw)


def _has_glob(path):
    return any(ch in path for ch in _GLOB_CHARS)


class MftBackend:
    """进程级 MFT 后端（全盘只扫描一次，结果供所有通用扫描器共享）"""

    _lock = threading.Lock()
    _initialized = False
    _available = False
    _entries = None     # MFT 原始条目（供 large_files 等复用）
    _results = None     # {key: [items]} 通用扫描项结果

    @classmethod
    def ensure(cls, context):
        """确保后端已初始化，返回 MFT 是否可用"""
        if cls._initialized:
            return cls._available

        with cls._lock:
            if cls._initialized:
                return cls._available

            entries = cls._load_entries()
            if entries is None:
                cls._available = False
            else:
                cls._entries = entries
                cls._results = _distribute(entries, context)
                cls._available = True
            cls._initialized = True
            return cls._available

    @classmethod
    def _load_entries(cls):
        if mftparser is None:
            logger.info("未安装 mftparser，使用目录遍历方式扫描")
            return None
        try:
            logger.info("使用 MFT 扫描 C 盘...")
            entries = mftparser.ScanVolume('C:', only_active=True)
            logger.info(f"MFT 扫描完成，共 {len(entries)} 个活跃条目")
            return entries
        except Exception as e:
            logger.warning(
                f"MFT 扫描失败，改用目录遍历"
                f"（可能需要管理员权限，或磁盘不是 NTFS）: {e}"
            )
            return None

    @classmethod
    def available(cls):
        return cls._available

    @classmethod
    def entries(cls):
        return cls._entries

    @classmethod
    def results(cls):
        return cls._results or {}

    @classmethod
    def reset(cls):
        """重置缓存（测试用）"""
        with cls._lock:
            cls._initialized = False
            cls._available = False
            cls._entries = None
            cls._results = None


def _distribute(entries, context):
    """按 SCAN_TARGETS 的通用规则，把 MFT 条目一次分发给各分类"""
    rules = {key: spec for key, spec in SCAN_TARGETS.items() if 'dedicated' not in spec}
    if not rules:
        return {}

    # 归一化路径 -> [(key, 原始路径, mode, 路径索引)]
    root_map = {}
    # glob 模式 -> [(小写模式, (key, 原始路径, mode, 路径索引))]
    glob_rules = []

    for key, spec in rules.items():
        mode = spec.get('mode', 'files')
        for index, raw in enumerate(spec.get('paths', [])):
            path = _expand_env(raw)
            if not path or not context.is_safe_path(path):
                continue
            rule = (key, path, mode, index)
            if _has_glob(path):
                glob_rules.append((path.lower(), rule))
            else:
                root_map.setdefault(os.path.normpath(path).lower(), []).append(rule)

    ext_sets = {
        key: {e.lower() for e in spec.get('extensions', [])}
        for key, spec in rules.items()
    }
    age_thresholds = {}
    for key, spec in rules.items():
        days = spec.get('older_than_days')
        if days:
            age_thresholds[key] = datetime.datetime.now() - datetime.timedelta(days=days)

    file_items = {key: [] for key in rules}
    aggregates = {}   # (key, 路径索引) -> [总大小, 文件数, 原始路径, spec]

    for entry in entries:
        try:
            is_dir = entry[IDX_IS_DIR]
            path = entry[IDX_PATH]
            size = entry[IDX_SIZE]
        except (IndexError, TypeError):
            continue
        if not path:
            continue

        lower = path.lower()
        matched = []

        # glob 规则（如 thumbcache_*.db）
        for pattern, rule in glob_rules:
            if fnmatch.fnmatchcase(lower, pattern):
                matched.append(rule)

        # 精确匹配：配置路径本身是一个文件
        matched.extend(root_map.get(lower, ()))

        # 祖先目录匹配：配置路径是一个目录
        parent = lower
        while True:
            pos = parent.rfind('\\')
            if pos <= 2:   # 已到 "c:"
                break
            parent = parent[:pos]
            rules_here = root_map.get(parent)
            if rules_here:
                matched.extend(rules_here)

        if not matched:
            continue

        # 去重：同一分类下相同路径的冗余配置不应产生重复记录
        deduped = {}
        for rule in matched:
            deduped.setdefault((rule[0], rule[1]), rule)

        for key, original_path, mode, index in deduped.values():
            if is_dir:
                continue
            if mode == 'files':
                exts = ext_sets[key]
                if exts and os.path.splitext(path)[1].lower() not in exts:
                    continue
                file_items[key].append({'path': path, 'size': size, 'type': key})
            else:
                slot = aggregates.get((key, index))
                if slot is None:
                    slot = [0, 0, original_path, rules[key]]
                    aggregates[(key, index)] = slot
                slot[0] += size
                slot[1] += 1

    # 修改时间过滤：MFT 时间字段索引不稳定，仅对需要的项用 stat 复核
    for key, threshold in age_thresholds.items():
        items = file_items.get(key)
        if not items:
            continue
        kept = []
        for it in items:
            try:
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(it['path']))
            except OSError:
                continue
            if mod_time < threshold:
                kept.append(it)
        file_items[key] = kept

    # 汇总 mode='path' 的聚合结果
    results = {key: list(items) for key, items in file_items.items() if items}
    for (key, _index), (total_size, file_count, original_path, spec) in aggregates.items():
        if total_size <= 0:
            continue
        item = {'path': original_path, 'size': total_size, 'type': key}
        if spec.get('count_files'):
            item['file_count'] = file_count
        results.setdefault(key, []).append(item)

    return results


class MftDirectoryScanner(ScanStrategy):
    """通用扫描器：优先 MFT，MFT 不可用时回退到 os.walk

    实际结果由 MftBackend 一次性构建，本类只负责取回自己 key 的结果；
    回退时复用 generic.DirectoryScanner 的完整逻辑。
    """

    def __init__(self, key=None, spec=None):
        self.key = key or ''
        self.spec = spec or {}
        self.display_name = self.spec.get('display_name', self.key)
        self._fallback = DirectoryScanner(key=key, spec=spec)

    def scan(self, context):
        if MftBackend.ensure(context):
            context.extend(self.key, MftBackend.results().get(self.key, []))
        else:
            self._fallback.scan(context)
