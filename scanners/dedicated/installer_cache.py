#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描安装程序缓存(安全版)"""

import os
import datetime

from scanners.base import ScanStrategy, logger


class InstallerCacheScanner(ScanStrategy):
    key = 'installer_cache'
    display_name = '安装程序缓存(30天前)'

    def scan(self, context):
        installer_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Installer', 'Temp'),
            os.path.join('C:', os.sep, 'ProgramData', 'Package Cache', 'Temp'),
            os.path.join('C:', os.sep, 'Windows', 'Downloaded Program Files', 'Temp'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Package Cache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'Downloaded Installations'),
        ]

        safe_extensions = ['.tmp', '.temp', '.msi.cache', '.exe.cache', '.log', '.old']
        very_old_threshold = datetime.datetime.now() - datetime.timedelta(days=30)

        for installer_dir in installer_cache_dirs:
            if os.path.exists(installer_dir) and context.is_safe_path(installer_dir):
                try:
                    for root, _, files in os.walk(installer_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    is_safe_temp = any(file.lower().endswith(ext) for ext in safe_extensions)

                                    is_very_old = False
                                    if not is_safe_temp:
                                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                        is_very_old = mod_time < very_old_threshold

                                    if is_safe_temp or is_very_old:
                                        subtype = "temp_installer" if is_safe_temp else "very_old_installer"
                                        context.add(self.key, {
                                            'path': file_path,
                                            'size': os.path.getsize(file_path),
                                            'type': self.key,
                                            'subtype': subtype,
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问安装程序缓存目录 {installer_dir}: {e}")

        # 特殊处理Windows Installer目录
        windows_installer = os.path.join('C:', os.sep, 'Windows', 'Installer')
        if os.path.exists(windows_installer) and context.is_safe_path(windows_installer):
            try:
                for root, _, files in os.walk(windows_installer):
                    for file in files:
                        try:
                            if file.lower().endswith(('.msp.cache', '.msi.cache', '.tmp', '.temp')):
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    context.add(self.key, {
                                        'path': file_path,
                                        'size': os.path.getsize(file_path),
                                        'type': self.key,
                                        'subtype': 'windows_installer_cache',
                                    })
                        except (PermissionError, FileNotFoundError):
                            pass
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问Windows Installer目录 {windows_installer}: {e}")
