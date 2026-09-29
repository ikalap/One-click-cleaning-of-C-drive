#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描备份临时文件"""

import os
import datetime

from .base import ScanStrategy, logger


class BackupTempScanner(ScanStrategy):
    key = 'backup_temp'
    display_name = '备份临时文件'

    def scan(self, context):
        backup_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Temp', 'WindowsBackup'),
            os.path.join('C:', os.sep, 'Windows', 'Logs', 'WindowsBackup'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WindowsBackup'),
        ]

        for backup_dir in backup_temp_dirs:
            if os.path.exists(backup_dir) and context.is_safe_path(backup_dir):
                try:
                    for root, _, files in os.walk(backup_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                    if (datetime.datetime.now() - mod_time).days > 30:
                                        context.add(self.key, {
                                            'path': file_path,
                                            'size': os.path.getsize(file_path),
                                            'type': self.key,
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问备份临时文件目录 {backup_dir}: {e}")
