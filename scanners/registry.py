#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描策略注册表

所有扫描目标集中定义在 targets.py（单一数据源）：

- 通用目标：由单个 mft.MftDirectoryScanner 实例统一负责，
  优先使用 MFT，不支持时自动回退到 os.walk
- 专用目标：通过 dedicated 字段动态 import 独立策略类

build_strategies() 只实例化「1 个通用策略 + N 个专用策略」，
不再为每个分类 key 各创建一个实例。
"""

import importlib

from .targets import SCAN_TARGETS
from .mft import MftDirectoryScanner

# 所有扫描结果的 key，与 UI 分类保持一致（顺序即展示顺序）
ALL_RESULT_KEYS = list(SCAN_TARGETS.keys())


def build_strategies():
    """实例化全部策略：1 个通用策略 + 各专用策略各 1 个"""
    strategies = [MftDirectoryScanner()]

    for spec in SCAN_TARGETS.values():
        path = spec.get('dedicated')
        if not path:
            continue
        module_name, class_name = path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        strategies.append(getattr(module, class_name)())

    return strategies
