#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描旧Windows文件"""

import os

from .base import ScanStrategy, dir_total_size, logger


class OldWindowsScanner(ScanStrategy):
    key = 'old_windows'
    display_name = '旧Windows文件'

    def scan(self, context):
        old_windows_dirs = [
            os.path.join('C:', os.sep, 'Windows.old'),
            os.path.join('C:', os.sep, '$Windows.~BT'),
            os.path.join('C:', os.sep, '$Windows.~WS'),
        ]

        for old_dir in old_windows_dirs:
            if os.path.exists(old_dir) and context.is_safe_path(old_dir):
                try:
                    total_size = dir_total_size(old_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': old_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问旧Windows文件夹 {old_dir}: {e}")
