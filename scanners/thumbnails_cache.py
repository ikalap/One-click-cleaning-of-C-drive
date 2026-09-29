#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描缩略图缓存"""

import os
import glob

from .base import ScanStrategy, logger


class ThumbnailsCacheScanner(ScanStrategy):
    key = 'thumbnails'
    display_name = '缩略图缓存'

    def scan(self, context):
        thumbnail_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer'),
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer'),
        ]

        for thumb_dir in thumbnail_dirs:
            if os.path.exists(thumb_dir) and context.is_safe_path(thumb_dir):
                try:
                    thumb_db = os.path.join(thumb_dir, 'thumbcache_*.db')
                    for thumb_file in glob.glob(thumb_db):
                        try:
                            if os.path.isfile(thumb_file):
                                context.add(self.key, {
                                    'path': thumb_file,
                                    'size': os.path.getsize(thumb_file),
                                    'type': self.key,
                                })
                        except (PermissionError, FileNotFoundError):
                            pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问缩略图缓存 {thumb_dir}: {e}")
