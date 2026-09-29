#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描磁盘清理备份"""

import os

from .base import ScanStrategy, dir_total_size, logger


class DiskCleanupBackupScanner(ScanStrategy):
    key = 'disk_cleanup'
    display_name = '磁盘清理备份'

    def scan(self, context):
        cleanup_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'LogFiles', 'setupapi'),
            os.path.join('C:', os.sep, 'Windows', 'Temp', 'CheckSur'),
            os.path.join('C:', os.sep, 'Windows', 'Logs', 'CBS'),
        ]

        for cleanup_dir in cleanup_dirs:
            if os.path.exists(cleanup_dir) and context.is_safe_path(cleanup_dir):
                try:
                    total_size = dir_total_size(cleanup_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': cleanup_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问磁盘清理备份 {cleanup_dir}: {e}")
