#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描回收站"""

import os

from .base import ScanStrategy, logger


class RecycleBinScanner(ScanStrategy):
    key = 'recycle'
    display_name = '回收站'

    def scan(self, context):
        recycle_bin = os.path.join('C:', os.sep, '$Recycle.Bin')
        if not os.path.exists(recycle_bin):
            return

        total_size = 0
        try:
            for root, _, files in os.walk(recycle_bin):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            total_size += os.path.getsize(file_path)
                    except (PermissionError, FileNotFoundError):
                        pass

            if total_size > 0:
                context.add(self.key, {
                    'path': recycle_bin,
                    'size': total_size,
                    'type': self.key,
                })
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"无法访问回收站: {e}")
