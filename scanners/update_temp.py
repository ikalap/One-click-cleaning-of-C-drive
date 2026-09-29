#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描更新临时文件"""

import os

from .base import ScanStrategy, dir_total_size, logger


class UpdateTempScanner(ScanStrategy):
    key = 'update_temp'
    display_name = '更新临时文件'

    def scan(self, context):
        update_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'PostRebootEventCache'),
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'Temp'),
            os.path.join('C:', os.sep, 'Windows', 'WinSxS', 'Temp'),
            os.path.join('C:', os.sep, 'Windows', 'Temp', 'TrustedInstaller'),
        ]

        for update_dir in update_temp_dirs:
            if os.path.exists(update_dir) and context.is_safe_path(update_dir):
                try:
                    total_size = dir_total_size(update_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': update_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问更新临时文件目录 {update_dir}: {e}")
