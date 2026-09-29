#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描字体缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class FontCacheScanner(ScanStrategy):
    key = 'font_cache'
    display_name = '字体缓存'

    def scan(self, context):
        font_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'ServiceProfiles', 'LocalService', 'AppData', 'Local', 'FontCache'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'FNTCACHE.DAT'),
        ]

        for font_dir in font_cache_dirs:
            if os.path.exists(font_dir) and context.is_safe_path(font_dir):
                try:
                    if os.path.isfile(font_dir):
                        file_size = os.path.getsize(font_dir)
                        if file_size > 0:
                            context.add(self.key, {
                                'path': font_dir,
                                'size': file_size,
                                'type': self.key,
                            })
                    else:
                        total_size = dir_total_size(font_dir)
                        if total_size > 0:
                            context.add(self.key, {
                                'path': font_dir,
                                'size': total_size,
                                'type': self.key,
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问字体缓存 {font_dir}: {e}")
