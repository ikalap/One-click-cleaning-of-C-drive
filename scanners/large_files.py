#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描C盘中的大文件"""

import os
import datetime

from .base import ScanStrategy, logger


class LargeFilesScanner(ScanStrategy):
    key = 'large_files'
    display_name = '大文件 (>100MB)'

    def scan(self, context):
        min_size = 100 * 1024 * 1024

        scan_dirs = [
            'C:\\Users',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
            'C:\\ProgramData',
        ]

        exclude_dirs = [
            'C:\\Windows',
            'C:\\Program Files\\WindowsApps',
            'C:\\Program Files (x86)\\WindowsApps',
            'C:\\$Recycle.Bin',
        ]

        exclude_extensions = [
            '.sys', '.dll', '.exe', '.msi', '.mui', '.idx', '.cat', '.db',
        ]

        large_files = []

        for scan_dir in scan_dirs:
            if os.path.exists(scan_dir) and context.is_safe_path(scan_dir):
                try:
                    for root, dirs, files in os.walk(scan_dir):
                        dirs[:] = [d for d in dirs if os.path.join(root, d) not in exclude_dirs]

                        for file in files:
                            try:
                                if any(file.lower().endswith(ext) for ext in exclude_extensions):
                                    continue

                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path) and context.is_safe_path(file_path):
                                    file_size = os.path.getsize(file_path)
                                    if file_size >= min_size:
                                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                        _, ext = os.path.splitext(file_path)

                                        large_files.append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': self.key,
                                            'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                                            'extension': ext.lower() if ext else '',
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法扫描目录 {scan_dir}: {e}")

        large_files.sort(key=lambda x: x['size'], reverse=True)
        large_files = large_files[:100]
        context.extend(self.key, large_files)

        logger.info(f"找到 {len(large_files)} 个大文件")
