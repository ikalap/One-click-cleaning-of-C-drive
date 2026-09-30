#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 核心清理逻辑

扫描部分使用「策略模式」组织，各扫描类型位于 scanners/ 包下：
- scanners/scan_strategy.py      ：ScanStrategy（策略接口）
- scanners/scan_strategy_context.py ：管理策略实例并协调 MFT/IO 后端，含专用策略动态加载
- scanners/*.py         ：每个扫描类型一个类，独立文件
"""

import os
import errno
import shutil
import tempfile
import logging
import datetime

from scanners import ScanStrategyContext
from app_config import get as get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='cleaner.log'
)
logger = logging.getLogger('CCleaner')


class FileInUseError(Exception):
    """文件/目录正被其他进程占用，无法删除。

    属于预期内可安全跳过的情况（如 Temp 下正在使用的 .tmp），
    不应作为清理错误上报。
    """


def is_file_in_use_error(exc):
    """判断异常是否表示文件被占用/拒绝访问"""
    if isinstance(exc, PermissionError):
        return True
    if getattr(exc, 'winerror', None) in (32, 33):  # 占用 / 锁定
        return True
    return getattr(exc, 'errno', None) in (errno.EACCES, errno.EPERM, errno.EBUSY)


class CleanerLogic:
    """清理逻辑核心类"""

    def __init__(self):
        """初始化清理器"""
        self.options = {
            'backup': True,     # 默认备份文件
        }

        # 安全路径列表 - 这些路径不会被扫描或清理
        self.safe_paths = [
            os.path.join('C:', os.sep, 'Windows', 'System32'),
            os.path.join('C:', os.sep, 'Windows', 'SysWOW64'),
            os.path.join('C:', os.sep, 'Program Files'),
            os.path.join('C:', os.sep, 'Program Files (x86)'),
        ]

        # 默认备份目录
        default_backup_dir = os.path.join(tempfile.gettempdir(), 'CCleaner_Backup')

        # 尝试找到非C盘的默认备份位置
        try:
            # 获取所有磁盘
            import string
            import ctypes

            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(letter + ':')
                bitmask >>= 1

            # 如果有非C盘，使用第一个非C盘作为默认备份位置
            for drive in drives:
                if drive.upper() != 'C:' and os.path.exists(drive):
                    default_backup_dir = os.path.join(drive, 'CCleaner_Backup')
                    break
        except Exception as e:
            logger.warning(f"无法获取非C盘作为备份位置: {e}")

        # 设置备份目录
        self.backup_dir = default_backup_dir

        # 备份限制
        self.max_backups = 5  # 最多保留几个备份
        self.max_backup_size = 1024 * 1024 * 1024  # 1GB

        # 上次扫描因被占用/无权限而跳过的文件数（供界面展示）
        self.last_skipped_locked = 0

        # 确保备份目录存在
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)

    def set_options(self, options):
        """设置选项"""
        self.options.update(options)

        # 如果设置了自定义备份目录
        if 'backup_dir' in options and options['backup_dir']:
            self.backup_dir = options['backup_dir']
            # 确保备份目录存在
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir, exist_ok=True)

        # 如果设置了备份限制
        if 'max_backups' in options:
            self.max_backups = options['max_backups']
        if 'max_backup_size' in options:
            self.max_backup_size = options['max_backup_size']

    def get_disk_info(self):
        """获取C盘信息"""
        try:
            # 使用os.statvfs替代psutil
            # 但Windows不支持statvfs，所以我们使用ctypes调用Windows API
            import ctypes

            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)

            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p('C:'),
                None,
                ctypes.pointer(total_bytes),
                ctypes.pointer(free_bytes)
            )

            total = total_bytes.value / (1024 * 1024 * 1024)  # GB
            free = free_bytes.value / (1024 * 1024 * 1024)    # GB
            used = total - free
            percent = (used / total) * 100 if total > 0 else 0

            return {
                'total': total,
                'used': used,
                'free': free,
                'percent': round(percent, 1)
            }
        except Exception as e:
            logger.error(f"获取磁盘信息失败: {e}")
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent': 0
            }

    def get_backup_info(self):
        """获取备份信息"""
        try:
            if not os.path.exists(self.backup_dir):
                return {
                    'backup_dir': self.backup_dir,
                    'backup_count': 0,
                    'total_size': 0,
                    'backups': []
                }

            # 获取所有备份文件夹
            backups = []
            total_size = 0

            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                if os.path.isdir(item_path):
                    # 计算备份大小
                    backup_size = 0
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    backup_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    # 尝试从文件夹名解析时间
                    try:
                        backup_time = datetime.datetime.strptime(item, '%Y%m%d_%H%M%S')
                        backup_time_str = backup_time.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        backup_time = datetime.datetime.fromtimestamp(os.path.getctime(item_path))
                        backup_time_str = backup_time.strftime('%Y-%m-%d %H:%M:%S')

                    backups.append({
                        'name': item,
                        'path': item_path,
                        'size': backup_size,
                        'time': backup_time_str,
                        'timestamp': backup_time.timestamp()
                    })

                    total_size += backup_size

            # 按时间排序，最新的在前面
            backups.sort(key=lambda x: x['timestamp'], reverse=True)

            return {
                'backup_dir': self.backup_dir,
                'backup_count': len(backups),
                'total_size': total_size,
                'backups': backups
            }
        except Exception as e:
            logger.error(f"获取备份信息失败: {e}")
            return {
                'backup_dir': self.backup_dir,
                'backup_count': 0,
                'total_size': 0,
                'backups': []
            }

    def clean_old_backups(self):
        """清理旧备份"""
        try:
            backup_info = self.get_backup_info()
            backups = backup_info['backups']

            # 如果备份数量超过限制，删除最旧的备份
            if len(backups) > self.max_backups:
                # 按时间排序，最旧的在后面
                backups_to_delete = backups[self.max_backups:]

                for backup in backups_to_delete:
                    try:
                        shutil.rmtree(backup['path'])
                        logger.info(f"删除旧备份: {backup['name']}")
                    except Exception as e:
                        logger.error(f"删除旧备份失败: {backup['path']}, {e}")

            # 如果备份总大小超过限制，从最旧的开始删除
            if backup_info['total_size'] > self.max_backup_size and backups:
                # 按时间排序，最旧的在后面
                remaining_size = backup_info['total_size']

                for backup in reversed(backups):  # 从最旧的开始删除
                    if remaining_size <= self.max_backup_size:
                        break

                    try:
                        shutil.rmtree(backup['path'])
                        logger.info(f"删除超大备份: {backup['name']}")
                        remaining_size -= backup['size']
                    except Exception as e:
                        logger.error(f"删除超大备份失败: {backup['path']}, {e}")

            return True
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return False

    def restore_backup(self, backup_path):
        """恢复备份"""
        try:
            if not os.path.exists(backup_path) or not os.path.isdir(backup_path):
                logger.error(f"备份路径不存在或不是目录: {backup_path}")
                return False

            # 遍历备份目录中的所有文件
            restored_count = 0
            for root, _, files in os.walk(backup_path):
                for file in files:
                    try:
                        # 备份文件路径
                        backup_file_path = os.path.join(root, file)

                        # 计算相对路径
                        rel_path = os.path.relpath(backup_file_path, backup_path)

                        # 原始文件路径
                        original_file_path = os.path.join('C:', os.sep, rel_path)

                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(original_file_path), exist_ok=True)

                        # 复制文件
                        shutil.copy2(backup_file_path, original_file_path)
                        restored_count += 1
                    except Exception as e:
                        logger.error(f"恢复文件失败: {backup_file_path}, {e}")

            logger.info(f"恢复完成，共恢复 {restored_count} 个文件")
            return True
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False

    def scan_system(self, progress_callback=None):
        """扫描系统中可清理的文件

        具体的策略实例管理与 MFT/IO 后端协调由 ScanStrategyContext 负责。

        参数：
            progress_callback: 可选，扫描进度回调。扫描器开始/完成时各调用一次，
                          签名为 callback(completed, total, active, finished_key, items)：
                          completed 已完成的扫描器数量，total 扫描器总数，
                          active 当前正在扫描的扫描器键列表，
                          finished_key 刚完成的扫描器键（开始通知时为 None），
                          items 该扫描器找到的项目列表（开始通知时为 []）。
        """
        strategy_context = ScanStrategyContext(
            safe_paths=self.safe_paths,
            prefer_mft=bool(get_config('fast_scan')),
            skip_locked=bool(get_config('skip_locked_files')),
        )
        results = strategy_context.scan(progress_callback=progress_callback)
        # 记录本次扫描跳过的被占用/无权限文件数，供界面展示
        self.last_skipped_locked = strategy_context.skipped_locked
        return results

    def clean_selected(self, items, progress_callback=None):
        """清理选中的项目"""
        logger.info(f"开始清理 {len(items)} 个项目")

        results = {
            'cleaned_items': [],
            'errors': [],
            'skipped': [],
            'freed_space': 0
        }

        # 创建当前备份目录
        if self.options['backup']:
            current_backup_dir = os.path.join(
                self.backup_dir,
                datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            os.makedirs(current_backup_dir, exist_ok=True)

            # 清理旧备份
            self.clean_old_backups()

        for i, item in enumerate(items):
            try:
                path = item['path']
                item_type = item.get('type', 'unknown')

                # 更新进度
                if progress_callback:
                    progress_callback.emit(path, i + 1)

                # 检查路径安全性
                if not self._is_safe_path(path):
                    logger.warning(f"跳过不安全路径: {path}")
                    results['errors'].append({
                        'path': path,
                        'error': '不安全的路径'
                    })
                    continue

                # 处理不同类型的项目
                if item_type == 'recycle':
                    # 清空回收站
                    self._empty_recycle_bin()
                    results['freed_space'] += item['size']
                    results['cleaned_items'].append(path)
                elif os.path.isdir(path):
                    # 清理目录
                    freed = self._clean_directory(
                        path,
                        current_backup_dir if self.options['backup'] else None,
                        results['skipped'],
                    )
                    results['freed_space'] += freed
                    results['cleaned_items'].append(path)
                elif os.path.isfile(path):
                    # 清理文件
                    try:
                        freed = self._clean_file(path, current_backup_dir if self.options['backup'] else None)
                    except FileInUseError:
                        logger.info(f"跳过正在使用的文件: {path}")
                        results['skipped'].append({'path': path, 'reason': '文件正在使用'})
                        continue
                    results['freed_space'] += freed
                    results['cleaned_items'].append(path)

            except Exception as e:
                logger.error(f"清理项目 {item['path']} 时出错: {e}")
                results['errors'].append({
                    'path': item['path'],
                    'error': str(e)
                })

        logger.info(
            f"清理完成，释放空间: {results['freed_space']} 字节，"
            f"错误: {len(results['errors'])}，跳过(占用): {len(results['skipped'])}"
        )
        return results

    def _clean_file(self, file_path, backup_dir=None):
        """清理单个文件。文件被占用时抛出 FileInUseError 供调用方跳过。"""
        try:
            if not os.path.exists(file_path):
                return 0

            file_size = os.path.getsize(file_path)

            # 备份文件
            if backup_dir:
                try:
                    rel_path = os.path.basename(file_path)
                    backup_path = os.path.join(backup_dir, rel_path)
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    shutil.copy2(file_path, backup_path)
                    logger.info(f"已备份文件: {file_path} -> {backup_path}")
                except Exception as e:
                    logger.warning(f"备份文件 {file_path} 失败: {e}")

            # 安全删除文件（优先移入回收站，失败则直接删除）
            self._delete_file(file_path)
            return file_size
        except FileInUseError:
            raise
        except Exception as e:
            logger.error(f"清理文件 {file_path} 失败: {e}")
            raise

    def _delete_file(self, file_path):
        """删除单个文件：先尝试移入回收站，失败后直接删除。

        文件被占用时抛出 FileInUseError，调用方可安全跳过。
        """
        # 尝试使用 Windows API 移动到回收站，失败则回退到直接删除
        try:
            import ctypes
            from ctypes import windll
            from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL

            SHFileOperationW = windll.shell32.SHFileOperationW

            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", HWND),
                    ("wFunc", UINT),
                    ("pFrom", LPCWSTR),
                    ("pTo", LPCWSTR),
                    ("fFlags", UINT),
                    ("fAnyOperationsAborted", BOOL),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", LPCWSTR),
                ]

            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x40  # 允许撤销（移动到回收站）
            FOF_NOCONFIRMATION = 0x10  # 不显示确认对话框
            FOF_SILENT = 0x04  # 不显示进度对话框
            FOF_NOERRORUI = 0x0400  # 不弹出系统错误对话框（占用等由本程序处理）

            # 添加结束空字符和额外的空字符
            path = file_path + '\0\0'

            fileop = SHFILEOPSTRUCTW(
                None,  # hwnd
                FO_DELETE,  # wFunc
                path,  # pFrom
                None,  # pTo
                FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI,  # fFlags
                None,  # fAnyOperationsAborted
                None,  # hNameMappings
                None,  # lpszProgressTitle
            )

            if SHFileOperationW(ctypes.byref(fileop)) == 0:
                logger.info(f"已删除文件到回收站: {file_path}")
                return
        except FileInUseError:
            raise
        except Exception as e:
            logger.warning(f"移入回收站失败，尝试直接删除 {file_path}: {e}")

        # 回退：直接删除
        try:
            os.remove(file_path)
            logger.info(f"已直接删除文件: {file_path}")
        except FileNotFoundError:
            return  # 已经被删除，视为成功
        except (PermissionError, OSError) as e:
            if is_file_in_use_error(e):
                raise FileInUseError(file_path) from e
            raise

    def _clean_directory(self, dir_path, backup_dir=None, skipped=None):
        """清理目录。被占用的文件记入 skipped（若提供），不作为错误。"""
        try:
            if not os.path.exists(dir_path):
                return 0

            total_freed = 0

            # 实际清理目录
            for root, dirs, files in os.walk(dir_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # 备份文件
                        if backup_dir:
                            try:
                                rel_path = os.path.relpath(file_path, dir_path)
                                backup_path = os.path.join(backup_dir, rel_path)
                                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                                shutil.copy2(file_path, backup_path)
                            except Exception as e:
                                logger.warning(f"备份文件 {file_path} 失败: {e}")

                        # 删除文件
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            total_freed += file_size
                            logger.info(f"已删除文件: {file_path}")
                    except FileNotFoundError:
                        pass
                    except (PermissionError, OSError) as e:
                        if is_file_in_use_error(e):
                            logger.info(f"跳过正在使用的文件: {file_path}")
                            if skipped is not None:
                                skipped.append({'path': file_path, 'reason': '文件正在使用'})
                        else:
                            logger.warning(f"删除文件 {file_path} 失败: {e}")

                # 删除空目录
                for dir_name in dirs:
                    try:
                        dir_to_remove = os.path.join(root, dir_name)
                        if os.path.exists(dir_to_remove) and not os.listdir(dir_to_remove):
                            os.rmdir(dir_to_remove)
                            logger.info(f"已删除空目录: {dir_to_remove}")
                    except (PermissionError, FileNotFoundError, OSError) as e:
                        logger.warning(f"删除目录 {os.path.join(root, dir_name)} 失败: {e}")

            return total_freed
        except Exception as e:
            logger.error(f"清理目录 {dir_path} 失败: {e}")
            raise

    def _empty_recycle_bin(self):
        """清空回收站"""
        try:
            # 使用PowerShell清空回收站
            import subprocess
            subprocess.run(['powershell.exe', '-Command', 'Clear-RecycleBin', '-Force', '-ErrorAction', 'SilentlyContinue'],
                          check=False,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
            logger.info("已清空回收站")
            return True
        except Exception as e:
            logger.error(f"清空回收站失败: {e}")
            return False

    def _is_safe_path(self, path):
        """检查路径是否安全（不在系统关键目录中）"""
        # 检查路径是否在安全路径列表中
        for safe_path in self.safe_paths:
            if path.startswith(safe_path):
                # 如果是系统目录的子目录，需要特别小心
                return False

        # 检查是否是系统目录
        system_dirs = [
            os.path.join('C:', os.sep, 'Windows'),
            os.path.join('C:', os.sep, 'Program Files'),
            os.path.join('C:', os.sep, 'Program Files (x86)'),
            os.path.join('C:', os.sep, 'ProgramData')
        ]

        for sys_dir in system_dirs:
            if path == sys_dir:
                return False

        return True
