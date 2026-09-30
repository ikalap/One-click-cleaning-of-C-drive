#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描浏览器缓存"""

import os

from scanners.base import ScanStrategy, logger


class BrowserCacheScanner(ScanStrategy):
    key = 'cache'
    display_name = '浏览器缓存'

    def scan(self, context):
        chrome_cache = os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Google', 'Chrome', 'User Data', 'Default', 'Cache',
        )
        edge_cache = os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Microsoft', 'Edge', 'User Data', 'Default', 'Cache',
        )
        firefox_profiles = os.path.join(
            os.environ.get('APPDATA', ''),
            'Mozilla', 'Firefox', 'Profiles',
        )

        cache_dirs = [chrome_cache, edge_cache]

        if os.path.exists(firefox_profiles):
            try:
                for profile in os.listdir(firefox_profiles):
                    profile_cache = os.path.join(firefox_profiles, profile, 'cache2')
                    if os.path.exists(profile_cache):
                        cache_dirs.append(profile_cache)
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问Firefox配置文件: {e}")

        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir) and context.is_safe_path(cache_dir):
                total_size = 0
                try:
                    for root, _, files in os.walk(cache_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        context.add(self.key, {
                            'path': cache_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问缓存目录 {cache_dir}: {e}")
