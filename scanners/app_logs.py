#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描应用程序日志"""

import os
import glob
import datetime

from .base import ScanStrategy, logger


class AppLogsScanner(ScanStrategy):
    key = 'app_logs'
    display_name = '应用程序日志'

    def scan(self, context):
        app_log_dirs = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Teams', 'logs.txt'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Teams', 'logs'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Office', '*.log'),
            os.path.join(os.environ.get('APPDATA', ''), 'Slack', 'logs'),
            os.path.join(os.environ.get('APPDATA', ''), 'discord', 'logs'),
        ]

        old_threshold = datetime.datetime.now() - datetime.timedelta(days=30)

        for log_dir in app_log_dirs:
            if '*' in log_dir:
                try:
                    for matched_path in glob.glob(log_dir):
                        if os.path.exists(matched_path) and context.is_safe_path(matched_path):
                            try:
                                if os.path.isfile(matched_path):
                                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(matched_path))
                                    if mod_time < old_threshold:
                                        file_size = os.path.getsize(matched_path)
                                        if file_size > 0:
                                            context.add(self.key, {
                                                'path': matched_path,
                                                'size': file_size,
                                                'type': self.key,
                                            })
                            except (PermissionError, FileNotFoundError) as e:
                                logger.warning(f"无法访问应用程序日志文件 {matched_path}: {e}")
                except Exception as e:
                    logger.warning(f"处理通配符模式时出错 {log_dir}: {e}")
                continue

            if os.path.exists(log_dir) and context.is_safe_path(log_dir):
                try:
                    if os.path.isfile(log_dir):
                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(log_dir))
                        if mod_time < old_threshold:
                            file_size = os.path.getsize(log_dir)
                            if file_size > 0:
                                context.add(self.key, {
                                    'path': log_dir,
                                    'size': file_size,
                                    'type': self.key,
                                })
                    else:
                        for root, _, files in os.walk(log_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                        if mod_time < old_threshold:
                                            context.add(self.key, {
                                                'path': file_path,
                                                'size': os.path.getsize(file_path),
                                                'type': self.key,
                                            })
                                except (PermissionError, FileNotFoundError):
                                    pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问应用程序日志 {log_dir}: {e}")
