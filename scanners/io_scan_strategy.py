#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""通用目录/文件扫描器

按 targets.SCAN_TARGETS 中的配置规格执行扫描，覆盖绝大多数清理项：

- mode='files'：递归收集目录下的文件（可按扩展名、修改时间过滤），
  每个文件作为一条结果记录；
- mode='path'：把每个路径作为一条结果记录，目录取其内所有文件的总大小
  （可选附带文件数量），文件取自身大小。

配置字段说明见 scan_targets_config.py 顶部文档。
"""

import os
import re
import glob
import datetime

from .scan_strategy import ScanStrategy, logger

# 匹配 %ENVVAR% 形式的环境变量
_ENV_VAR_RE = re.compile(r'%([^%]+)%')
# glob 通配符
_GLOB_CHARS = ('*', '?', '[')


class DirectoryScanner(ScanStrategy):
    """配置驱动的通用扫描器"""

    def __init__(self, key=None, spec=None):
        self.key = key or ''
        self.spec = spec or {}
        self.display_name = self.spec.get('display_name', self.key)

        self.mode = self.spec.get('mode', 'files')
        self.paths = self.spec.get('paths', [])
        self.extensions = {e.lower() for e in self.spec.get('extensions', [])}
        self.count_files = self.spec.get('count_files', False)

        # 修改时间阈值（早于该时间才收集）
        older_than_days = self.spec.get('older_than_days')
        self._mtime_threshold = (
            datetime.datetime.now() - datetime.timedelta(days=older_than_days)
            if older_than_days else None
        )

    # ------------------------------------------------------------------
    def scan(self, context):
        for path in self._iter_paths():
            if not os.path.exists(path) or not context.is_safe_path(path):
                continue
            try:
                if self.mode == 'files':
                    self._scan_files(path, context)
                else:
                    self._scan_path(path, context)
            except (PermissionError, FileNotFoundError, OSError) as e:
                logger.warning(f"无法访问 {path}: {e}")

    # ------------------------------------------------------------------
    # 路径展开
    # ------------------------------------------------------------------
    def _iter_paths(self):
        """展开环境变量与 glob 通配符，逐个产出候选路径"""
        for raw in self.paths:
            expanded = _ENV_VAR_RE.sub(
                lambda m: os.environ.get(m.group(1), ''), raw
            )
            if not expanded:
                continue
            if any(ch in expanded for ch in _GLOB_CHARS):
                for matched in glob.glob(expanded):
                    yield matched
            else:
                yield expanded

    # ------------------------------------------------------------------
    # mode='files'：逐文件收集
    # ------------------------------------------------------------------
    def _scan_files(self, path, context):
        if os.path.isfile(path):
            self._add_file(path, context)
            return

        for root, _, files in os.walk(path):
            for name in files:
                self._add_file(os.path.join(root, name), context)

    def _add_file(self, file_path, context):
        try:
            if not os.path.isfile(file_path):
                return

            if self.extensions:
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in self.extensions:
                    return

            if self._mtime_threshold is not None:
                mod_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                )
                if mod_time >= self._mtime_threshold:
                    return

            context.add(self.key, {
                'path': file_path,
                'size': os.path.getsize(file_path),
                'type': self.key,
            })
        except (PermissionError, FileNotFoundError, OSError):
            pass

    # ------------------------------------------------------------------
    # mode='path'：每个路径一条记录
    # ------------------------------------------------------------------
    def _scan_path(self, path, context):
        if os.path.isfile(path):
            total_size, file_count = os.path.getsize(path), 1
        else:
            total_size, file_count = self._dir_size_and_count(path)

        if total_size <= 0:
            return

        item = {
            'path': path,
            'size': total_size,
            'type': self.key,
        }
        if self.count_files:
            item['file_count'] = file_count
        context.add(self.key, item)

    @staticmethod
    def _dir_size_and_count(path):
        """递归统计目录内文件总大小与文件数量"""
        total_size = 0
        file_count = 0
        for root, _, files in os.walk(path):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                except (PermissionError, FileNotFoundError, OSError):
                    pass
        return total_size, file_count
