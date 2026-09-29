#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描预读取文件"""

import os

from .base import ScanStrategy, logger


class PrefetchScanner(ScanStrategy):
    key = 'prefetch'
    display_name = '预读取文件'

    def scan(self, context):
        prefetch_dir = os.path.join('C:', os.sep, 'Windows', 'Prefetch')
        if not os.path.exists(prefetch_dir) or not context.is_safe_path(prefetch_dir):
            return

        try:
            for root, _, files in os.walk(prefetch_dir):
                for file in files:
                    if file.endswith('.pf'):
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
            logger.warning(f"无法访问预读取文件夹 {prefetch_dir}: {e}")
