#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描DNS缓存"""

import os

from .base import ScanStrategy, logger


class DnsCacheScanner(ScanStrategy):
    key = 'dns_cache'
    display_name = 'DNS缓存'

    def scan(self, context):
        dns_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'dnsrslvr.log'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'dns', 'cache.dns'),
        ]

        for dns_dir in dns_cache_dirs:
            if os.path.exists(dns_dir) and context.is_safe_path(dns_dir):
                try:
                    if os.path.isfile(dns_dir):
                        file_size = os.path.getsize(dns_dir)
                        if file_size > 0:
                            context.add(self.key, {
                                'path': dns_dir,
                                'size': file_size,
                                'type': self.key,
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问DNS缓存 {dns_dir}: {e}")
