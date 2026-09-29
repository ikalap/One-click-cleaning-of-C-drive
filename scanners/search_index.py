#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描搜索索引临时文件"""

import os

from .base import ScanStrategy, logger


class SearchIndexScanner(ScanStrategy):
    key = 'search_index'
    display_name = '搜索索引临时文件'

    def scan(self, context):
        search_index_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Search', 'Data', 'Temp'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Search', 'Data', 'Applications', 'Windows'),
            os.path.join('C:', os.sep, 'Windows', 'ServiceProfiles', 'LocalService', 'AppData', 'Local', 'Microsoft', 'Windows', 'Search'),
        ]

        temp_extensions = ['.tmp', '.old', '.bak', '.log']

        for index_dir in search_index_dirs:
            if os.path.exists(index_dir) and context.is_safe_path(index_dir):
                try:
                    for root, _, files in os.walk(index_dir):
                        for file in files:
                            try:
                                if any(file.endswith(ext) for ext in temp_extensions):
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
                    logger.warning(f"无法访问搜索索引目录 {index_dir}: {e}")
