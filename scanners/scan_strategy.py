#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略基础设施

- ScanStrategy：策略模式抽象基类
"""

import logging
from abc import ABC, abstractmethod
logger = logging.getLogger('CCleaner')

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
