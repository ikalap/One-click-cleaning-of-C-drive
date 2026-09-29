#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略包

使用策略模式 + 责任链模式组织各扫描类型：
- 策略模式：每个扫描类型是一个 ScanStrategy 子类（scanners/ 下的独立文件）
- 责任链模式：ScanChain 将启用的策略串成链，按配置依次处理
- 动态加载：registry.py 通过 key -> import path 的映射，按配置动态获取策略类
"""

from .base import (
    ScanStrategy,
    ScanContext,
    ScanHandler,
    StrategyScanHandler,
    ScanChain,
    dir_total_size,
)
from .registry import (
    SCANNER_REGISTRY,
    ALL_RESULT_KEYS,
    load_strategy_class,
    build_strategies,
    build_scan_chain,
)

__all__ = [
    'ScanStrategy',
    'ScanContext',
    'ScanHandler',
    'StrategyScanHandler',
    'ScanChain',
    'dir_total_size',
    'SCANNER_REGISTRY',
    'ALL_RESULT_KEYS',
    'load_strategy_class',
    'build_strategies',
    'build_scan_chain',
]
