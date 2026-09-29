#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描Windows Defender缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class WindowsDefenderScanner(ScanStrategy):
    key = 'windows_defender'
    display_name = 'Windows Defender缓存'

    def scan(self, context):
        defender_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows Defender', 'Scans', 'History'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows Defender', 'Quarantine'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows Defender', 'Support'),
        ]

        for defender_dir in defender_dirs:
            if os.path.exists(defender_dir) and context.is_safe_path(defender_dir):
                try:
                    total_size = dir_total_size(defender_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': defender_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows Defender缓存目录 {defender_dir}: {e}")
