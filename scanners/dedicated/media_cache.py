#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""扫描媒体播放器缓存"""

import os
import glob

from scanners.scan_strategy import ScanStrategy, logger


class MediaCacheScanner(ScanStrategy):
    key = 'media_cache'
    display_name = '媒体播放器缓存'

    def scan(self, context):
        media_cache_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Media Player'),
            os.path.join(os.environ.get('APPDATA', ''), 'vlc', 'art'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Spotify', 'Storage'),
            os.path.join(os.environ.get('APPDATA', ''), 'Spotify', 'cache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer', 'iconcache*'),
        ]

        for cache_dir in media_cache_dirs:
            if '*' in cache_dir:
                try:
                    for matched_path in glob.glob(cache_dir):
                        if os.path.exists(matched_path) and context.is_safe_path(matched_path):
                            try:
                                if os.path.isfile(matched_path):
                                    file_size = os.path.getsize(matched_path)
                                    if file_size > 0:
                                        context.add(self.key, {
                                            'path': matched_path,
                                            'size': file_size,
                                            'type': self.key,
                                        })
                            except (PermissionError, FileNotFoundError) as e:
                                logger.warning(f"无法访问媒体缓存文件 {matched_path}: {e}")
                except Exception as e:
                    logger.warning(f"处理通配符模式时出错 {cache_dir}: {e}")
                continue

            if os.path.exists(cache_dir) and context.is_safe_path(cache_dir):
                try:
                    total_size = dir_total_size(cache_dir)
                    if total_size > 0:
                        context.add(self.key, {
                            'path': cache_dir,
                            'size': total_size,
                            'type': self.key,
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问媒体缓存 {cache_dir}: {e}")

def dir_total_size(path):
    """递归计算目录内所有文件的总大小（跳过无权限/已消失的文件）"""
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
            except (PermissionError, FileNotFoundError):
                pass
    return total
