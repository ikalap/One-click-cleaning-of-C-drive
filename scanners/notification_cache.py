#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描Windows通知缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class NotificationCacheScanner(ScanStrategy):
    key = 'notification'
    display_name = 'Windows通知缓存'

    def scan(self, context):
        notification_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Notifications'),
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'ActionCenterCache'),
        ]

        for notification_dir in notification_dirs:
            if os.path.exists(notification_dir) and context.is_safe_path(notification_dir):
                try:
                    total_size = dir_total_size(notification_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': notification_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows通知缓存 {notification_dir}: {e}")
