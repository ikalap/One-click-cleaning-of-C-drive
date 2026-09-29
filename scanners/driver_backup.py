#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描驱动备份"""

import os

from .base import ScanStrategy, dir_total_size, logger


class DriverBackupScanner(ScanStrategy):
    key = 'driver_backup'
    display_name = '驱动备份'

    def scan(self, context):
        driver_backup_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'inf', 'OLD'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'DriverStore', 'Temp'),
        ]

        for driver_dir in driver_backup_dirs:
            if os.path.exists(driver_dir) and context.is_safe_path(driver_dir):
                try:
                    total_size = dir_total_size(driver_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': driver_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问驱动备份目录 {driver_dir}: {e}")
