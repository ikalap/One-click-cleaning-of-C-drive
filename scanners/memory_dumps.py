#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描内存转储文件"""

import os

from .base import ScanStrategy, dir_total_size, logger


class MemoryDumpsScanner(ScanStrategy):
    key = 'memory_dumps'
    display_name = '内存转储文件'

    def scan(self, context):
        memory_dump_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Minidump'),
            os.path.join('C:', os.sep, 'Windows', 'MEMORY.DMP'),
            os.path.join('C:', os.sep, 'Windows', 'memory.dmp'),
        ]

        for dump_dir in memory_dump_dirs:
            if os.path.exists(dump_dir) and context.is_safe_path(dump_dir):
                try:
                    if os.path.isfile(dump_dir):
                        file_size = os.path.getsize(dump_dir)
                        if file_size > 0:
                            context.add(self.key, {
                                'path': dump_dir,
                                'size': file_size,
                                'type': self.key,
                            })
                    else:
                        total_size = dir_total_size(dump_dir)
                        if total_size > 0:
                            context.add(self.key, {
                                'path': dump_dir,
                                'size': total_size,
                                'type': self.key,
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问内存转储文件 {dump_dir}: {e}")
