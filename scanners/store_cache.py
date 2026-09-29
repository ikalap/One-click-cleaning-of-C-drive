#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描Windows Store缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class StoreCacheScanner(ScanStrategy):
    key = 'store_cache'
    display_name = 'Windows Store缓存'

    def scan(self, context):
        store_cache_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', 'Microsoft.WindowsStore_8wekyb3d8bbwe', 'LocalCache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', 'Microsoft.WindowsStore_8wekyb3d8bbwe', 'LocalState'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', 'Microsoft.WindowsStore_8wekyb3d8bbwe', 'TempState'),
        ]

        for store_dir in store_cache_dirs:
            if os.path.exists(store_dir) and context.is_safe_path(store_dir):
                try:
                    total_size = dir_total_size(store_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': store_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows Store缓存目录 {store_dir}: {e}")
