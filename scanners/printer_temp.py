#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描打印机临时文件"""

import os

from .base import ScanStrategy, dir_total_size, logger


class PrinterTempScanner(ScanStrategy):
    key = 'printer_temp'
    display_name = '打印机临时文件'

    def scan(self, context):
        printer_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'spool', 'PRINTERS'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'spool', 'SERVERS'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'spool', 'drivers', 'color'),
        ]

        for printer_dir in printer_temp_dirs:
            if os.path.exists(printer_dir) and context.is_safe_path(printer_dir):
                try:
                    total_size = dir_total_size(printer_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': printer_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问打印机临时文件目录 {printer_dir}: {e}")
