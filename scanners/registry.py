#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描策略注册表

将「扫描类型 key」映射到「策略类的 import path」，
扫描时根据配置动态 import 对应的类，实现可插拔的扫描策略。
"""

import importlib

# key -> 策略类 import path（按扫描顺序排列）
SCANNER_REGISTRY = {
    # 基本清理
    'temp': 'scanners.temp_files.TempFilesScanner',
    'recycle': 'scanners.recycle_bin.RecycleBinScanner',
    'cache': 'scanners.browser_cache.BrowserCacheScanner',
    'logs': 'scanners.system_logs.SystemLogsScanner',
    'updates': 'scanners.windows_updates.WindowsUpdatesScanner',
    'thumbnails': 'scanners.thumbnails_cache.ThumbnailsCacheScanner',

    # 扩展清理
    'prefetch': 'scanners.prefetch.PrefetchScanner',
    'old_windows': 'scanners.old_windows.OldWindowsScanner',
    'error_reports': 'scanners.error_reports.ErrorReportsScanner',
    'service_packs': 'scanners.service_packs.ServicePacksScanner',
    'memory_dumps': 'scanners.memory_dumps.MemoryDumpsScanner',
    'font_cache': 'scanners.font_cache.FontCacheScanner',
    'disk_cleanup': 'scanners.disk_cleanup_backup.DiskCleanupBackupScanner',

    # 安全清理项
    'app_cache': 'scanners.app_cache.AppCacheScanner',
    'media_cache': 'scanners.media_cache.MediaCacheScanner',
    'search_index': 'scanners.search_index.SearchIndexScanner',
    'backup_temp': 'scanners.backup_temp.BackupTempScanner',
    'update_temp': 'scanners.update_temp.UpdateTempScanner',
    'driver_backup': 'scanners.driver_backup.DriverBackupScanner',
    'app_crash': 'scanners.app_crash.AppCrashScanner',
    'app_logs': 'scanners.app_logs.AppLogsScanner',
    'recent_items': 'scanners.recent_items.RecentItemsScanner',
    'notification': 'scanners.notification_cache.NotificationCacheScanner',
    'dns_cache': 'scanners.dns_cache.DnsCacheScanner',
    'printer_temp': 'scanners.printer_temp.PrinterTempScanner',
    'device_temp': 'scanners.device_temp.DeviceTempScanner',
    'windows_defender': 'scanners.windows_defender.WindowsDefenderScanner',
    'store_cache': 'scanners.store_cache.StoreCacheScanner',
    'onedrive_cache': 'scanners.onedrive_cache.OneDriveCacheScanner',

    # 用户请求的清理项
    'downloads': 'scanners.downloads.DownloadsScanner',
    'installer_cache': 'scanners.installer_cache.InstallerCacheScanner',
    'delivery_opt': 'scanners.delivery_optimization.DeliveryOptimizationScanner',

    # 大文件扫描
    'large_files': 'scanners.large_files.LargeFilesScanner',
}

# 所有扫描结果的 key，与 UI 分类保持一致
ALL_RESULT_KEYS = list(SCANNER_REGISTRY.keys())


def load_strategy_class(key):
    """根据 key 动态加载策略类"""
    path = SCANNER_REGISTRY[key]
    module_name, class_name = path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def build_strategies(config=None):
    """按注册表动态实例化全部策略"""
    config = config or {}
    strategies = []
    for key in SCANNER_REGISTRY:
        cls = load_strategy_class(key)
        strategies.append(cls(config=config))
    return strategies
