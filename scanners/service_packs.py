#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描服务包备份"""

import os

from .base import ScanStrategy, dir_total_size, logger


class ServicePacksScanner(ScanStrategy):
    key = 'service_packs'
    display_name = '服务包备份'

    def scan(self, context):
        service_pack_dirs = [
            os.path.join('C:', os.sep, 'Windows', '$NtServicePackUninstall$'),
            os.path.join('C:', os.sep, 'Windows', '$hf_mig$'),
        ]

        for sp_dir in service_pack_dirs:
            if os.path.exists(sp_dir) and context.is_safe_path(sp_dir):
                try:
                    total_size = dir_total_size(sp_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': sp_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问服务包备份文件夹 {sp_dir}: {e}")
