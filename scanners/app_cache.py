#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描应用程序缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class AppCacheScanner(ScanStrategy):
    key = 'app_cache'
    display_name = '应用程序缓存'

    def scan(self, context):
        app_cache_dirs = [
            os.path.join(os.environ.get('APPDATA', ''), 'Adobe', 'Common'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Office', 'Recent'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Office', 'OTele'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'DriveFS'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Teams', 'Cache'),
            os.path.join(os.environ.get('APPDATA', ''), 'Slack', 'Cache'),
            os.path.join(os.environ.get('APPDATA', ''), 'discord', 'Cache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'INetCache', 'IE'),
        ]

        for cache_dir in app_cache_dirs:
            if os.path.exists(cache_dir) and context.is_safe_path(cache_dir):
                try:
                    total_size = dir_total_size(cache_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': cache_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问应用程序缓存 {cache_dir}: {e}")
