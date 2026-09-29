#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描系统日志"""

import os

from .base import ScanStrategy, logger


class SystemLogsScanner(ScanStrategy):
    key = 'logs'
    display_name = '系统日志'

    def scan(self, context):
        log_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Logs'),
            os.path.join('C:', os.sep, 'Windows', 'debug'),
        ]

        for log_dir in log_dirs:
            if os.path.exists(log_dir) and context.is_safe_path(log_dir):
                try:
                    for root, _, files in os.walk(log_dir):
                        for file in files:
                            if file.endswith('.log') or file.endswith('.etl') or file.endswith('.dmp'):
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        context.add(self.key, {
                                            'path': file_path,
                                            'size': os.path.getsize(file_path),
                                            'type': self.key,
                                        })
                                except (PermissionError, FileNotFoundError):
                                    pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问日志目录 {log_dir}: {e}")
