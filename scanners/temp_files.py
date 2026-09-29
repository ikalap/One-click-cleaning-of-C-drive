#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描临时文件"""

import os

from .base import ScanStrategy, logger


class TempFilesScanner(ScanStrategy):
    key = 'temp'
    display_name = '临时文件'

    def scan(self, context):
        temp_dirs = [
            os.environ.get('TEMP', os.path.join('C:', os.sep, 'Windows', 'Temp')),
            os.path.join('C:', os.sep, 'Windows', 'Temp'),
        ]

        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir) and context.is_safe_path(temp_dir):
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                file_size = os.path.getsize(file_path)
                                context.add(self.key, {
                                    'path': file_path,
                                    'size': file_size,
                                    'type': self.key,
                                })
                        except (PermissionError, FileNotFoundError) as e:
                            logger.warning(f"无法访问文件 {file_path}: {e}")
