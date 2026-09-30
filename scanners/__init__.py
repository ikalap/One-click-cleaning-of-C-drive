#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略包

- scan_strategy.py     ：ScanStrategy（策略接口）、ScanContext
- scan_targets_config.py  ：所有扫描目标与路径配置（单一数据源）
- io_scan_strategy.py  ：配置驱动的通用目录/文件扫描器（os.walk）
- mft_scan_strategy.py      ：MFT 后端与 MFT 优先的通用扫描器（不支持时回退 generic）
- registry.py ：按 targets 配置实例化全部扫描策略
- dedicated/  ：无法用配置表达的专用扫描器（浏览器缓存、媒体缓存、
                应用日志、安装程序缓存、大文件等）
"""

from .scan_strategy import (
    ScanStrategy,
    ScanContext,
)
from .scan_targets_config import (
    SCAN_TARGETS,
    CATEGORY_NAMES,
)
from .io_scan_strategy import DirectoryScanner
from .mft_scan_strategy import (
    MftBackend,
    MftDirectoryScanner,
)
from .registry import (
    ALL_RESULT_KEYS,
    build_strategies,
)

__all__ = [
    'ScanStrategy',
    'ScanContext',
    'SCAN_TARGETS',
    'CATEGORY_NAMES',
    'DirectoryScanner',
    'MftBackend',
    'MftDirectoryScanner',
    'ALL_RESULT_KEYS',
    'build_strategies',
]
