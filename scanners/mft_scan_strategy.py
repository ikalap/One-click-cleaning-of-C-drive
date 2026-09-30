#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""基于 NTFS 主文件表（MFT）的通用扫描后端
对整卷 C 盘只解析一次 MFT，得到所有活跃文件条目，再按
targets.SCAN_TARGETS 中的通用规则一次性分发，产出各分类结果。
"""

import os
import re
import fnmatch
import datetime

from .scan_strategy import ScanStrategy, logger
from .scan_targets_config import SCAN_TARGETS

try:
    import mftparser
except ImportError:  # 未安装 mftparser 时由 ScanStrategyContext 负责回退
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

# 由通用扫描器负责的全部结果 key（SCAN_TARGETS 中未标 dedicated 的项）
GENERAL_KEYS = [key for key, spec in SCAN_TARGETS.items() if 'dedicated' not in spec]


class MftBackend:
    """MFT 业务逻辑：解析卷主文件表并按配置分发结果

    只负责业务逻辑，不做可用性判断、不处理回退：mftparser 未安装、
    缺少管理员权限或磁盘非 NTFS 时直接抛出异常，
    由 ScanStrategyContext 捕获并决定是否回退到 IO(os.walk) 扫描。
    """

    @staticmethod
    def load_entries(volume='C:'):
        """解析指定卷的 MFT，返回活跃文件条目（失败时抛出异常）"""
        logger.info(f"使用 MFT 扫描 {volume} 盘...")
        entries = mftparser.ScanVolume(volume, only_active=True)
        logger.info(f"MFT 扫描完成，共 {len(entries)} 个活跃条目")
        return entries

    @staticmethod
    def distribute(entries, context):
        """按 SCAN_TARGETS 的通用规则分发条目，返回 {key: [items]}"""
        return _distribute(entries, context)


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


class MftScanStrategy(ScanStrategy):
    """通用扫描器：使用 MFT 一次性产出所有通用分类结果

    扫描上下文（ScanStrategyContext）负责 MFT 可用性判断、条目缓存与回退；
    本策略只做业务：拿缓存的条目按配置分发到各分类。
    """

    display_name = '通用扫描'

    @property
    def keys(self):
        return list(GENERAL_KEYS)

    def scan(self, context):
        entries = context.mft_entries()
        if entries is None:
            return

        results = MftBackend.distribute(entries, context)
        for key in GENERAL_KEYS:
            context.extend(key, results.get(key, []))
