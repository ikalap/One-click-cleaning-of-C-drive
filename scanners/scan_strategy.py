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

    key = ''            # 单 key 策略的结果键；多 key 策略留空
    display_name = ''   # 显示名称

    @property
    def keys(self):
        """本策略负责的全部结果 key（单 key 策略默认返回 [key]）"""
        return [self.key] if self.key else []

    @abstractmethod
    def scan(self, context):
        """执行扫描，将结果写入 context.results"""
