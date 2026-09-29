#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描OneDrive缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class OneDriveCacheScanner(ScanStrategy):
    key = 'onedrive_cache'
    display_name = 'OneDrive缓存'

    def scan(self, context):
        onedrive_cache_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'OneDrive', 'logs'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'OneDrive', 'settings', 'Personal', 'logs'),
        ]

        for onedrive_dir in onedrive_cache_dirs:
            if os.path.exists(onedrive_dir) and context.is_safe_path(onedrive_dir):
                try:
                    total_size = dir_total_size(onedrive_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': onedrive_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问OneDrive缓存目录 {onedrive_dir}: {e}")
