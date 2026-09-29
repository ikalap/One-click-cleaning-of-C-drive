#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描最近使用的文件列表缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class RecentItemsScanner(ScanStrategy):
    key = 'recent_items'
    display_name = '最近使用的文件列表'

    def scan(self, context):
        recent_dirs = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Recent'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Office', 'Recent'),
        ]

        for recent_dir in recent_dirs:
            if os.path.exists(recent_dir) and context.is_safe_path(recent_dir):
                try:
                    total_size = dir_total_size(recent_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': recent_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问最近使用的文件列表缓存 {recent_dir}: {e}")
