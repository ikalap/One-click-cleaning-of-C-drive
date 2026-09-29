#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描下载文件夹(立即清理)"""

import os

from .base import ScanStrategy, logger


class DownloadsScanner(ScanStrategy):
    key = 'downloads'
    display_name = '下载文件夹(立即清理)'

    def scan(self, context):
        download_dirs = [
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'Downloads'),
            os.path.join(os.path.expanduser('~'), 'Downloads'),
        ]

        for download_dir in download_dirs:
            if os.path.exists(download_dir) and context.is_safe_path(download_dir):
                try:
                    total_size = 0
                    file_count = 0
                    for root, _, files in os.walk(download_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                                    file_count += 1
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        context.add(self.key, {
                            'path': download_dir,
                            'size': total_size,
                            'type': self.key,
                            'file_count': file_count,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问下载文件夹 {download_dir}: {e}")
