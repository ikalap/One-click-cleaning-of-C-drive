#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略基础设施

- ScanStrategy：策略模式抽象基类
- ScanContext：扫描上下文，携带共享结果与安全路径判断
- ScanHandler / StrategyScanHandler / ScanChain：责任链模式实现
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


class ScanHandler(ABC):
    """责任链节点抽象基类（责任链模式）"""

    def __init__(self):
        self._next = None

    def set_next(self, handler):
        self._next = handler
        return handler

    @abstractmethod
    def can_handle(self, config):
        """判断当前节点是否需要处理"""

    @abstractmethod
    def handle(self, context):
        """执行当前节点的实际处理逻辑"""

    def process(self, context, config=None):
        """责任链入口：能处理则处理，然后传递给下一个节点"""
        if self.can_handle(config):
            self.handle(context)
        if self._next is not None:
            self._next.process(context, config)


class StrategyScanHandler(ScanHandler):
    """将扫描策略包装为责任链节点"""

    def __init__(self, strategy):
        super().__init__()
        self.strategy = strategy

    def can_handle(self, config):
        return self.strategy.is_enabled(config)

    def handle(self, context):
        self.strategy.scan(context)


class ScanChain:
    """扫描责任链：按注册顺序串联各策略节点"""

    def __init__(self, strategies):
        self.handlers = []
        self.head = None
        tail = None
        for strategy in strategies:
            handler = StrategyScanHandler(strategy)
            self.handlers.append(handler)
            if tail is None:
                self.head = handler
            else:
                tail.set_next(handler)
            tail = handler

    def enabled_handlers(self, config=None):
        """返回所有按配置启用的节点（可并发执行）"""
        return [h for h in self.handlers if h.can_handle(config)]

    def run(self, context, config=None):
        """顺序执行整条责任链"""
        if self.head is not None:
            self.head.process(context, config)
