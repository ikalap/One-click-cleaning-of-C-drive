#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描设备临时文件"""

import os

from .base import ScanStrategy, dir_total_size, logger


class DeviceTempScanner(ScanStrategy):
    key = 'device_temp'
    display_name = '设备临时文件'

    def scan(self, context):
        device_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'INF', 'setupapi.dev.log'),
            os.path.join('C:', os.sep, 'Windows', 'INF', 'setupapi.log'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'LogFiles', 'setupapi'),
        ]

        for device_dir in device_temp_dirs:
            if os.path.exists(device_dir) and context.is_safe_path(device_dir):
                try:
                    if os.path.isfile(device_dir):
                        file_size = os.path.getsize(device_dir)
                        if file_size > 0:
                            context.add(self.key, {
                                'path': device_dir,
                                'size': file_size,
                                'type': self.key,
                            })
                    else:
                        total_size = dir_total_size(device_dir)
                        if total_size > 0:
                            context.add(self.key, {
                                'path': device_dir,
                                'size': total_size,
                                'type': self.key,
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问设备临时文件目录 {device_dir}: {e}")
