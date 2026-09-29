#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描应用程序崩溃转储"""

import os

from .base import ScanStrategy, dir_total_size, logger


class AppCrashScanner(ScanStrategy):
    key = 'app_crash'
    display_name = '应用程序崩溃转储'

    def scan(self, context):
        app_crash_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows', 'WER', 'ReportArchive'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows', 'WER', 'ReportQueue'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CrashDumps'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER', 'ReportArchive'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER', 'ReportQueue'),
        ]

        for crash_dir in app_crash_dirs:
            if os.path.exists(crash_dir) and context.is_safe_path(crash_dir):
                try:
                    total_size = dir_total_size(crash_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': crash_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问应用程序崩溃转储目录 {crash_dir}: {e}")
