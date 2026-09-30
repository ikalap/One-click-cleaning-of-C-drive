#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略基础设施

- ScanStrategy：策略模式抽象基类
- ScanContext：扫描上下文，携带共享结果与安全路径判断
"""

import os
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger('CCleaner')


def dir_total_size(path):
    """递归计算目录内所有文件的总大小（跳过无权限/已消失的文件）"""
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
            except (PermissionError, FileNotFoundError):
                pass
    return total


class ScanContext:
    """扫描上下文：所有扫描策略共享的结果容器与工具方法"""

    def __init__(self, results=None, safe_paths=None):
        self.results = results if results is not None else {}
        self.safe_paths = safe_paths or []

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


class ScanStrategy(ABC):
    """扫描策略抽象基类（策略模式）

    每个子类对应一种扫描类型，必须设置 key（结果字典键）并实现 scan()。
    """

    key = ''            # 结果字典中的键，与 UI 的分类一致
    display_name = ''   # 显示名称

    def __init__(self, config=None):
        self.config = config or {}

    @abstractmethod
    def scan(self, context):
        """执行扫描，将结果写入 context.results[self.key]"""

    def is_enabled(self, config=None):
        """根据配置判断该策略是否启用，默认启用

        config 支持两种形式：
        - dict：{'temp': True, 'cache': False}，缺省视为启用
        - set/list：{'temp', 'cache'}，在集合中的视为启用，其余禁用
        """
        cfg = config if config is not None else self.config
        if cfg is None:
            return True
        if isinstance(cfg, dict):
            return cfg.get(self.key, True)
        return self.key in cfg
