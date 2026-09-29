#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描Windows传递优化缓存"""

import os

from .base import ScanStrategy, dir_total_size, logger


class DeliveryOptimizationScanner(ScanStrategy):
    key = 'delivery_opt'
    display_name = 'Windows传递优化缓存(立即清理)'

    def scan(self, context):
        delivery_opt_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'ServiceProfiles', 'NetworkService', 'AppData', 'Local', 'Microsoft', 'Windows', 'DeliveryOptimization', 'Cache'),
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'DeliveryOptimization', 'Cache'),
        ]

        for opt_dir in delivery_opt_dirs:
            if os.path.exists(opt_dir) and context.is_safe_path(opt_dir):
                try:
                    total_size = dir_total_size(opt_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': opt_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows传递优化缓存 {opt_dir}: {e}")
