#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描错误报告"""

import os

from .base import ScanStrategy, dir_total_size, logger


class ErrorReportsScanner(ScanStrategy):
    key = 'error_reports'
    display_name = '错误报告'

    def scan(self, context):
        error_report_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows', 'WER'),
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'WER'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER'),
        ]

        for error_dir in error_report_dirs:
            if os.path.exists(error_dir) and context.is_safe_path(error_dir):
                try:
                    total_size = dir_total_size(error_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': error_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问错误报告文件夹 {error_dir}: {e}")
