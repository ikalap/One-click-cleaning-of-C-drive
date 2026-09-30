#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描策略注册表

所有扫描目标集中定义在 targets.py（单一数据源）：

- 通用目标：优先由 mft.MftDirectoryScanner 使用 MFT 扫描，
  不支持 MFT 时自动回退到 generic.DirectoryScanner 的目录遍历
- 专用目标：通过 dedicated 字段动态 import 独立策略类

build_strategies() 按 SCAN_TARGETS 的顺序实例化全部策略，
该顺序同时决定 UI 中分类的展示顺序。
"""

import importlib

from .targets import SCAN_TARGETS
from .mft import MftDirectoryScanner

# 所有扫描结果的 key，与 UI 分类保持一致（顺序即展示顺序）
ALL_RESULT_KEYS = list(SCAN_TARGETS.keys())


def load_strategy_class(key):
    """根据 key 获取策略类

    通用目标返回绑定好配置的 MftDirectoryScanner（内部按需回退到目录遍历）。
    """
    spec = SCAN_TARGETS[key]

    if 'dedicated' in spec:
        module_name, class_name = spec['dedicated'].rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    class _ConfiguredScanner(MftDirectoryScanner):
        def __init__(self):
            super().__init__(key=key, spec=spec)

    return _ConfiguredScanner


def build_strategies():
    """按注册表顺序实例化全部策略"""
    return [
        load_strategy_class(key)()
        for key in SCAN_TARGETS
    ]
