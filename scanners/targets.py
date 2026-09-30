#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描目标定义（单一数据源）

集中维护所有扫描项：

- display_name：显示名称，UI 分类名由此生成（= CATEGORY_NAMES）
- 通用扫描项：由 DirectoryScanner 按配置驱动，字段包括
    mode             'files' 逐文件收集 / 'path' 每个路径一条记录
    paths            路径列表，支持 %ENVVAR% 环境变量与 glob 通配符
    extensions       可选，仅收集这些扩展名（小写，含点）
    older_than_days  可选，仅收集修改时间早于 N 天前的文件
    count_files      可选，为 'path' 记录附带文件数量
- 专用扫描项：dedicated = 策略类的 import path，用于无法用配置表达的逻辑
    （浏览器缓存、媒体缓存、应用日志、安装程序缓存、大文件）

新增「按路径扫描目录或文件」的清理项时，只需在 SCAN_TARGETS 中加一条配置，
无需再新增 Python 文件。
"""

SCAN_TARGETS = {
    # ------------------------------------------------------------------
    # 基本清理
    # ------------------------------------------------------------------
    'temp': {
        'display_name': '临时文件',
        'mode': 'files',
        'paths': ['%TEMP%', r'C:\Windows\Temp'],
    },
    'recycle': {
        'display_name': '回收站',
        'mode': 'path',
        'paths': [r'C:\$Recycle.Bin'],
    },
    'cache': {
        'display_name': '浏览器缓存',
        'dedicated': 'scanners.dedicated.browser_cache.BrowserCacheScanner',
    },
    'logs': {
        'display_name': '系统日志',
        'mode': 'files',
        'paths': [r'C:\Windows\Logs', r'C:\Windows\debug'],
        'extensions': ['.log', '.etl', '.dmp'],
    },
    'updates': {
        'display_name': 'Windows更新缓存',
        'mode': 'path',
        'paths': [
            r'C:\Windows\SoftwareDistribution\Download',
            r'C:\Windows\SoftwareDistribution\DataStore',
        ],
    },
    'thumbnails': {
        'display_name': '缩略图缓存',
        'mode': 'files',
        'paths': [
            r'%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db',
            r'C:\Users\%USERNAME%\AppData\Local\Microsoft\Windows\Explorer\thumbcache_*.db',
        ],
    },

    # ------------------------------------------------------------------
    # 扩展清理
    # ------------------------------------------------------------------
    'prefetch': {
        'display_name': '预读取文件',
        'mode': 'files',
        'paths': [r'C:\Windows\Prefetch'],
        'extensions': ['.pf'],
    },
    'old_windows': {
        'display_name': '旧Windows文件',
        'mode': 'path',
        'paths': [r'C:\Windows.old', r'C:\$Windows.~BT', r'C:\$Windows.~WS'],
    },
    'error_reports': {
        'display_name': '错误报告',
        'mode': 'path',
        'paths': [
            r'C:\ProgramData\Microsoft\Windows\WER',
            r'C:\Users\%USERNAME%\AppData\Local\Microsoft\Windows\WER',
            r'%LOCALAPPDATA%\Microsoft\Windows\WER',
        ],
    },
    'service_packs': {
        'display_name': '服务包备份',
        'mode': 'path',
        'paths': [r'C:\Windows\$NtServicePackUninstall$', r'C:\Windows\$hf_mig$'],
    },
    'memory_dumps': {
        'display_name': '内存转储文件',
        'mode': 'path',
        'paths': [r'C:\Windows\Minidump', r'C:\Windows\MEMORY.DMP', r'C:\Windows\memory.dmp'],
    },
    'font_cache': {
        'display_name': '字体缓存',
        'mode': 'path',
        'paths': [
            r'C:\Windows\ServiceProfiles\LocalService\AppData\Local\FontCache',
            r'C:\Windows\System32\FNTCACHE.DAT',
        ],
    },
    'disk_cleanup': {
        'display_name': '磁盘清理备份',
        'mode': 'path',
        'paths': [
            r'C:\Windows\System32\LogFiles\setupapi',
            r'C:\Windows\Temp\CheckSur',
            r'C:\Windows\Logs\CBS',
        ],
    },

    # ------------------------------------------------------------------
    # 安全清理项
    # ------------------------------------------------------------------
    'app_cache': {
        'display_name': '应用程序缓存',
        'mode': 'path',
        'paths': [
            r'%APPDATA%\Adobe\Common',
            r'%LOCALAPPDATA%\Microsoft\Office\Recent',
            r'%LOCALAPPDATA%\Microsoft\Office\OTele',
            r'%LOCALAPPDATA%\Google\DriveFS',
            r'%LOCALAPPDATA%\Microsoft\Teams\Cache',
            r'%APPDATA%\Slack\Cache',
            r'%APPDATA%\discord\Cache',
            r'%LOCALAPPDATA%\Microsoft\Windows\INetCache\IE',
        ],
    },
    'media_cache': {
        'display_name': '媒体播放器缓存',
        'dedicated': 'scanners.dedicated.media_cache.MediaCacheScanner',
    },
    'search_index': {
        'display_name': '搜索索引临时文件',
        'mode': 'files',
        'paths': [
            r'C:\ProgramData\Microsoft\Search\Data\Temp',
            r'C:\ProgramData\Microsoft\Search\Data\Applications\Windows',
            r'C:\Windows\ServiceProfiles\LocalService\AppData\Local\Microsoft\Windows\Search',
        ],
        'extensions': ['.tmp', '.old', '.bak', '.log'],
    },
    'backup_temp': {
        'display_name': '备份临时文件',
        'mode': 'files',
        'paths': [
            r'C:\Windows\Temp\WindowsBackup',
            r'C:\Windows\Logs\WindowsBackup',
            r'%LOCALAPPDATA%\Microsoft\Windows\WindowsBackup',
        ],
        'older_than_days': 30,
    },
    'update_temp': {
        'display_name': '更新临时文件',
        'mode': 'path',
        'paths': [
            r'C:\Windows\SoftwareDistribution\PostRebootEventCache',
            r'C:\Windows\SoftwareDistribution\Temp',
            r'C:\Windows\WinSxS\Temp',
            r'C:\Windows\Temp\TrustedInstaller',
        ],
    },
    'driver_backup': {
        'display_name': '驱动备份',
        'mode': 'path',
        'paths': [r'C:\Windows\inf\OLD', r'C:\Windows\System32\DriverStore\Temp'],
    },
    'app_crash': {
        'display_name': '应用程序崩溃转储',
        'mode': 'path',
        'paths': [
            r'C:\ProgramData\Microsoft\Windows\WER\ReportArchive',
            r'C:\ProgramData\Microsoft\Windows\WER\ReportQueue',
            r'%LOCALAPPDATA%\CrashDumps',
            r'%LOCALAPPDATA%\Microsoft\Windows\WER\ReportArchive',
            r'%LOCALAPPDATA%\Microsoft\Windows\WER\ReportQueue',
        ],
    },
    'app_logs': {
        'display_name': '应用程序日志',
        'dedicated': 'scanners.dedicated.app_logs.AppLogsScanner',
    },
    'recent_items': {
        'display_name': '最近使用的文件列表',
        'mode': 'path',
        'paths': [
            r'%APPDATA%\Microsoft\Windows\Recent',
            r'%APPDATA%\Microsoft\Office\Recent',
        ],
    },
    'notification': {
        'display_name': 'Windows通知缓存',
        'mode': 'path',
        'paths': [
            r'%LOCALAPPDATA%\Microsoft\Windows\Notifications',
            r'C:\Users\%USERNAME%\AppData\Local\Microsoft\Windows\ActionCenterCache',
        ],
    },
    'dns_cache': {
        'display_name': 'DNS缓存',
        'mode': 'path',
        'paths': [r'C:\Windows\System32\dnsrslvr.log', r'C:\Windows\System32\dns\cache.dns'],
    },
    'printer_temp': {
        'display_name': '打印机临时文件',
        'mode': 'path',
        'paths': [
            r'C:\Windows\System32\spool\PRINTERS',
            r'C:\Windows\System32\spool\SERVERS',
            r'C:\Windows\System32\spool\drivers\color',
        ],
    },
    'device_temp': {
        'display_name': '设备临时文件',
        'mode': 'path',
        'paths': [
            r'C:\Windows\INF\setupapi.dev.log',
            r'C:\Windows\INF\setupapi.log',
            r'C:\Windows\System32\LogFiles\setupapi',
        ],
    },
    'windows_defender': {
        'display_name': 'Windows Defender缓存',
        'mode': 'path',
        'paths': [
            r'C:\ProgramData\Microsoft\Windows Defender\Scans\History',
            r'C:\ProgramData\Microsoft\Windows Defender\Quarantine',
            r'C:\ProgramData\Microsoft\Windows Defender\Support',
        ],
    },
    'store_cache': {
        'display_name': 'Windows Store缓存',
        'mode': 'path',
        'paths': [
            r'%LOCALAPPDATA%\Packages\Microsoft.WindowsStore_8wekyb3d8bbwe\LocalCache',
            r'%LOCALAPPDATA%\Packages\Microsoft.WindowsStore_8wekyb3d8bbwe\LocalState',
            r'%LOCALAPPDATA%\Packages\Microsoft.WindowsStore_8wekyb3d8bbwe\TempState',
        ],
    },
    'onedrive_cache': {
        'display_name': 'OneDrive缓存',
        'mode': 'path',
        'paths': [
            r'%LOCALAPPDATA%\Microsoft\OneDrive\logs',
            r'%LOCALAPPDATA%\Microsoft\OneDrive\settings\Personal\logs',
        ],
    },

    # ------------------------------------------------------------------
    # 用户请求的清理项
    # ------------------------------------------------------------------
    'downloads': {
        'display_name': '下载文件夹(立即清理)',
        'mode': 'path',
        'paths': [r'C:\Users\%USERNAME%\Downloads', r'%USERPROFILE%\Downloads'],
        'count_files': True,
    },
    'installer_cache': {
        'display_name': '安装程序缓存(30天前)',
        'dedicated': 'scanners.dedicated.installer_cache.InstallerCacheScanner',
    },
    'delivery_opt': {
        'display_name': 'Windows传递优化缓存(立即清理)',
        'mode': 'path',
        'paths': [
            r'C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache',
            r'C:\Windows\SoftwareDistribution\DeliveryOptimization\Cache',
        ],
    },

    # ------------------------------------------------------------------
    # 大文件扫描
    # ------------------------------------------------------------------
    'large_files': {
        'display_name': '大文件 (>100MB)',
        'dedicated': 'scanners.dedicated.large_files.LargeFilesScanner',
    },
}

# 结果分类 key -> 显示名称（UI 使用，与 SCAN_TARGETS 单一来源）
CATEGORY_NAMES = {key: spec['display_name'] for key, spec in SCAN_TARGETS.items()}
