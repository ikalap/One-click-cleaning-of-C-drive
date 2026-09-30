#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略包

- scan_strategy.py     ：ScanStrategy（策略接口）
- scan_targets_config.py  ：所有扫描目标与路径配置（单一数据源）
- io_scan_strategy.py  ：配置驱动的通用目录/文件扫描器（os.walk）
- mft_scan_strategy.py      ：MFT 后端与 MFT 优先的通用扫描器（不支持时回退 generic）
- scan_strategy_context.py ：扫描策略上下文，管理策略实例、协调 MFT/IO 后端并上报进度，
                含结果 key 定义（ALL_RESULT_KEYS）与专用策略实例化
- dedicated/  ：无法用配置表达的专用扫描器（浏览器缓存、媒体缓存、
                应用日志、安装程序缓存、大文件等）
"""

from .scan_strategy import (
    ScanStrategy,
)
from .scan_targets_config import (
    SCAN_TARGETS,
    CATEGORY_NAMES,
)
from .io_scan_strategy import IoScanStrategy
from .mft_scan_strategy import (
    MftBackend,
    MftScanStrategy,
)
from .scan_strategy_context import (
    ALL_RESULT_KEYS,
    build_dedicated_strategies,
    ScanStrategyContext,
    ScanProgress,
)

__all__ = [
    'ScanStrategy',
    'SCAN_TARGETS',
    'CATEGORY_NAMES',
    'IoScanStrategy',
    'MftBackend',
    'MftScanStrategy',
    'ALL_RESULT_KEYS',
    'build_dedicated_strategies',
    'ScanStrategyContext',
    'ScanProgress',
]
