#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描Windows更新缓存"""

import os

from .base import ScanStrategy, logger


class WindowsUpdatesScanner(ScanStrategy):
    key = 'updates'
    display_name = 'Windows更新缓存'

    def scan(self, context):
        update_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'Download'),
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'DataStore'),
        ]

        for update_dir in update_dirs:
            if os.path.exists(update_dir) and context.is_safe_path(update_dir):
                total_size = 0
                try:
                    for root, _, files in os.walk(update_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        context.add(self.key, {
                            'path': update_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows更新缓存 {update_dir}: {e}")
