#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 安全高效地清理C盘不必要的文件
"""

import sys
import os
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from config import APP_NAME, VERSION
from cleaner_logic import CleanerLogic
from ui.backup_manager import BackupManagerWindow
from ui.settings_dialog import SettingsDialog
from scanners import ALL_RESULT_KEYS, CATEGORY_NAMES

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='cleaner.log'
)
logger = logging.getLogger('CCleaner')

class CleanerApp(tk.Tk):
    """基于tkinter的C盘清理工具主应用程序"""

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("800x600")
        self.minsize(800, 600)

        self.cleaner = CleanerLogic()
        self.scan_results = {}
        self.selected_items = []
        # 已在结果树中展示的分类：key -> Treeview 节点 id
        self._tree_category_ids = {}
        # 扫描进度状态与计时
        self._scan_start_time = None
        self._scan_ticking = False
        self._scan_progress = {'completed': 0, 'total': 0, 'active': []}

        self.create_widgets()
        self.update_disk_info()

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 系统信息区域
        info_frame = ttk.LabelFrame(main_frame, text="系统信息", padding="5")
        info_frame.pack(fill=tk.X, pady=5)

        self.disk_info_label = ttk.Label(info_frame, text="C盘使用情况: 正在加载...")
        self.disk_info_label.pack(anchor=tk.W)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.scan_button = ttk.Button(button_frame, text="扫描系统", command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        self.clean_all_button = ttk.Button(button_frame, text="一键清理", command=self.start_clean_all)
        self.clean_all_button.pack(side=tk.LEFT, padx=5)

        self.clean_button = ttk.Button(button_frame, text="清理选中项", command=self.start_clean, state=tk.DISABLED)
        self.clean_button.pack(side=tk.LEFT, padx=5)

        self.select_all_button = ttk.Button(button_frame, text="全选", command=self.select_all_items, state=tk.DISABLED)
        self.select_all_button.pack(side=tk.LEFT, padx=5)

        self.deselect_all_button = ttk.Button(button_frame, text="取消全选", command=self.deselect_all_items, state=tk.DISABLED)
        self.deselect_all_button.pack(side=tk.LEFT, padx=5)

        self.settings_button = ttk.Button(button_frame, text="配置", command=self.open_settings)
        self.settings_button.pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=5)

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.pack_forget()  # 初始隐藏

        self.status_label = ttk.Label(self.progress_frame, text="", wraplength=760, justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W)

        # 结果区域
        result_frame = ttk.LabelFrame(main_frame, text="扫描结果", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 创建Treeview用于显示结果
        columns = ("name", "size", "path")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="tree headings")

        # 设置列标题
        self.result_tree.heading("name", text="项目")
        self.result_tree.heading("size", text="大小")
        self.result_tree.heading("path", text="路径")

        # 设置列宽
        self.result_tree.column("name", width=200)
        self.result_tree.column("size", width=100)
        self.result_tree.column("path", width=400)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)

        # 放置Treeview和滚动条
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 选中变化时同步"清理选中项"按钮的可用状态
        self.result_tree.bind("<<TreeviewSelect>>", self._on_tree_selection_change)

        # 安全选项区域
        safety_frame = ttk.LabelFrame(main_frame, text="安全选项", padding="5")
        safety_frame.pack(fill=tk.X, pady=5)

        # 备份选项
        backup_frame = ttk.Frame(safety_frame)
        backup_frame.pack(fill=tk.X, pady=2)

        self.backup_var = tk.BooleanVar(value=True)
        self.backup_check = ttk.Checkbutton(backup_frame, text="删除前备份文件",
                                           variable=self.backup_var)
        self.backup_check.pack(side=tk.LEFT)

        self.backup_manager_button = ttk.Button(backup_frame, text="备份管理", command=self.open_backup_manager)
        self.backup_manager_button.pack(side=tk.LEFT, padx=10)

        # 备份目录选项
        backup_dir_frame = ttk.Frame(safety_frame)
        backup_dir_frame.pack(fill=tk.X, pady=2)

        ttk.Label(backup_dir_frame, text="备份目录:").pack(side=tk.LEFT, padx=5)

        self.backup_dir_var = tk.StringVar(value=self.cleaner.backup_dir)
        backup_dir_entry = ttk.Entry(backup_dir_frame, textvariable=self.backup_dir_var, width=40)
        backup_dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_button = ttk.Button(backup_dir_frame, text="浏览...", command=self.browse_backup_dir)
        browse_button.pack(side=tk.LEFT, padx=5)

    def update_disk_info(self):
        """更新磁盘信息"""
        disk_info = self.cleaner.get_disk_info()
        self.disk_info_label.config(
            text=f"C盘总空间: {disk_info['total']:.2f} GB | "
                 f"已用空间: {disk_info['used']:.2f} GB ({disk_info['percent']}%) | "
                 f"可用空间: {disk_info['free']:.2f} GB"
        )

    def start_scan(self):
        """开始扫描系统"""
        self.scan_button.config(state=tk.DISABLED)
        self.clean_button.config(state=tk.DISABLED)
        self.select_all_button.config(state=tk.DISABLED)
        self.deselect_all_button.config(state=tk.DISABLED)
        self.result_tree.delete(*self.result_tree.get_children())
        self._tree_category_ids = {}
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()

        # 预估扫描器总数，先显示 0/总数
        total = len(ALL_RESULT_KEYS)

        # 初始化扫描进度与计时，并启动实时刷新
        self._scan_start_time = time.monotonic()
        self._scan_progress = {'completed': 0, 'total': total, 'active': []}
        self._scan_ticking = True
        self._render_scan_status()
        self.after(100, self._tick_scan_status)

        # 创建一个队列用于线程通信
        self.scan_queue = queue.Queue()
        
        # 创建并启动扫描线程
        scan_thread = threading.Thread(target=self._scan_thread_task)
        scan_thread.daemon = True  # 设置为守护线程，随主线程退出而退出
        scan_thread.start()
        
        # 定期检查队列
        self.after(100, self._check_scan_queue)

    def _scan_thread_task(self):
        """在单独的线程中执行扫描任务"""
        try:
            def on_progress(completed, total, active, finished_key, items):
                # 通过队列把扫描进度安全地传回主线程
                self.scan_queue.put(
                    ('progress', (completed, total, active, finished_key, items))
                )

            # 执行扫描
            results = self.cleaner.scan_system(progress_callback=on_progress)
            # 将结果放入队列
            self.scan_queue.put(('success', results))
        except Exception as e:
            # 出现异常时，将异常信息放入队列
            logger.error(f"扫描过程中出错: {e}")
            self.scan_queue.put(('error', str(e)))

    def _tick_scan_status(self):
        """定时刷新扫描状态栏，让耗时持续累加"""
        if not self._scan_ticking:
            return
        self._render_scan_status()
        self.after(100, self._tick_scan_status)

    def _render_scan_status(self):
        """根据当前扫描进度渲染状态栏文本"""
        progress = self._scan_progress
        text = f"扫描中 {progress['completed']}/{progress['total']}"

        # 实时显示当前正在扫描的项目
        active = progress.get('active') or []
        if active:
            shown = active[:5]
            names = "、".join(CATEGORY_NAMES.get(k, k) for k in shown)
            if len(active) > len(shown):
                names += f" 等{len(active)}项"
            text += f" · 当前扫描项目: {names}"

        # 实时累加已耗时
        if self._scan_start_time is not None:
            elapsed = time.monotonic() - self._scan_start_time
            text += f" · 耗时 {elapsed:.1f}s"

        self.status_label.config(text=text)

    def _check_scan_queue(self):
        """检查扫描线程队列（实时处理进度与结果）"""
        finished = False
        try:
            # 一次性清空当前队列，避免进度消息积压
            while True:
                status, data = self.scan_queue.get_nowait()

                if status == 'progress':
                    completed, total, active, finished_key, items = data
                    # 仅更新进度状态并立即刷新一次，耗时的持续累加由定时器负责
                    self._scan_progress = {
                        'completed': completed,
                        'total': total,
                        'active': active,
                    }
                    self._render_scan_status()
                    # 扫描器一完成就立即把它发现的项目展示到列表
                    if finished_key and items:
                        self.add_category_to_tree(finished_key, items)

                elif status == 'success':
                    self.scan_results = data
                    self.on_scan_finished()
                    finished = True
                    break

                elif status == 'error':
                    self._scan_ticking = False
                    messagebox.showerror("扫描错误", f"扫描过程中出错: {data}")
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
                    self.scan_button.config(state=tk.NORMAL)
                    finished = True
                    break

        except queue.Empty:
            # 队列为空，说明扫描还在进行，继续等待
            pass

        if not finished:
            self.after(100, self._check_scan_queue)

    def on_scan_finished(self):
        """扫描完成后的处理"""
        # 停止耗时累加，冻结总耗时
        self._scan_ticking = False
        elapsed = 0.0
        if self._scan_start_time is not None:
            elapsed = time.monotonic() - self._scan_start_time
            self._scan_start_time = None
        elapsed_text = f" · 耗时 {elapsed:.1f}s"

        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_button.config(state=tk.NORMAL)

        # 扫描阶段被跳过（被占用/无权限）的文件数
        skipped_locked = getattr(self.cleaner, 'last_skipped_locked', 0)
        skipped_text = f" · 已忽略 {skipped_locked} 个被占用/无权限文件" if skipped_locked else ""

        if not any(self.scan_results.values()):
            self.status_label.config(
                text=f"扫描完成，未发现可清理项目{skipped_text}{elapsed_text}"
            )
            return

        # 计算总大小
        total_size = sum(item['size'] for category in self.scan_results.values() for item in category)
        self.status_label.config(
            text=f"扫描完成，发现可释放空间: {self.format_size(total_size)}"
                 f"{skipped_text}{elapsed_text}"
        )

        # 扫描过程中已实时展示结果，这里仅补齐可能遗漏的分类
        for key, items in self.scan_results.items():
            if key not in self._tree_category_ids:
                self.add_category_to_tree(key, items)

        self.clean_button.config(state=tk.NORMAL)
        self.select_all_button.config(state=tk.NORMAL)
        self.deselect_all_button.config(state=tk.NORMAL)

        # 更新磁盘信息
        self.update_disk_info()

    def populate_results_tree(self):
        """填充结果树（全量重建）"""
        self.result_tree.delete(*self.result_tree.get_children())
        self._tree_category_ids = {}
        for category, items in self.scan_results.items():
            self.add_category_to_tree(category, items)

    def add_category_to_tree(self, category, items):
        """将一个扫描分类的结果实时添加到结果树中"""
        if not items:
            return None

        # 已展示过则不重复添加
        existing = self._tree_category_ids.get(category)
        if existing and self.result_tree.exists(existing):
            return existing

        # 计算类别总大小
        category_size = sum(item['size'] for item in items)
        category_name = CATEGORY_NAMES.get(category, category)

        # 添加类别节点
        category_id = self.result_tree.insert(
            "", "end", text=category_name,
            values=(category_name, self.format_size(category_size), "")
        )
        self._tree_category_ids[category] = category_id

        # 添加文件节点
        for item in items:
            file_name = os.path.basename(item['path'])

            # 大文件显示更多信息
            if category == 'large_files' and 'modified' in item and 'extension' in item:
                file_info = f"{file_name} [修改时间: {item['modified']}] [类型: {item['extension']}]"
                self.result_tree.insert(
                    category_id, "end", text=file_name,
                    values=(file_info, self.format_size(item['size']), item['path']),
                    tags=("item",)
                )
            else:
                self.result_tree.insert(
                    category_id, "end", text=file_name,
                    values=(file_name, self.format_size(item['size']), item['path']),
                    tags=("item",)
                )

        self.result_tree.item(category_id, open=True)
        self._reorder_tree_categories()
        return category_id

    def _reorder_tree_categories(self):
        """按扫描器注册表顺序排列结果树中的分类节点"""
        index = 0
        for key in ALL_RESULT_KEYS:
            node_id = self._tree_category_ids.get(key)
            if node_id and self.result_tree.exists(node_id):
                self.result_tree.move(node_id, "", index)
                index += 1

    def _on_tree_selection_change(self, event=None):
        """根据当前选中的文件节点更新"清理选中项"按钮状态"""
        has_selected_file = any(
            self.result_tree.parent(item_id)
            for item_id in self.result_tree.selection()
        )
        self.clean_button.config(
            state=tk.NORMAL if has_selected_file else tk.DISABLED
        )

    def start_clean(self):
        """开始清理选中的项目"""
        # 获取选中的项目（基于 Treeview 实际选中行）
        self.selected_items = []
        
        # 分类节点 id -> 结果 key（避免依赖显示名称反查）
        id_to_key = {cid: key for key, cid in self._tree_category_ids.items()}

        for item_id in self.result_tree.selection():
            # 仅处理文件节点（有父节点即为文件/子项，分类节点无父节点）
            category_id = self.result_tree.parent(item_id)
            category_key = id_to_key.get(category_id)
            if not category_key:
                continue
            item_path = self.result_tree.item(item_id, 'values')[2]  # 路径在第三列
            for item in self.scan_results.get(category_key, []):
                if item['path'] == item_path:
                    self.selected_items.append(item)
                    break

        if not self.selected_items:
            messagebox.showinfo("清理", "请先选择需要清理的项目")
            return

        # 获取选项
        options = {
            'backup': self.backup_var.get(),
            'backup_dir': self.backup_dir_var.get()
        }
        self.cleaner.set_options(options)

        # 确认清理
        confirm = messagebox.askyesno("确认清理", 
                                    f"您确定要清理选中的 {len(self.selected_items)} 个项目吗？\n"
                                    f"这将永久删除这些文件。")
        if not confirm:
            return

        # 禁用按钮
        self.scan_button.config(state=tk.DISABLED)
        self.clean_button.config(state=tk.DISABLED)
        self.clean_all_button.config(state=tk.DISABLED)
        self.select_all_button.config(state=tk.DISABLED)
        self.deselect_all_button.config(state=tk.DISABLED)

        # 显示进度
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()
        self.status_label.config(text="正在清理，请稍候...")

        # 创建一个队列用于线程通信
        self.clean_queue = queue.Queue()
        
        # 创建并启动清理线程
        clean_thread = threading.Thread(target=self._clean_thread_task)
        clean_thread.daemon = True
        clean_thread.start()
        
        # 定期检查队列
        self.after(100, self._check_clean_queue)

    def _clean_thread_task(self):
        """在单独的线程中执行清理任务"""
        try:
            results = self.cleaner.clean_selected(self.selected_items)
            self.clean_queue.put(('success', results))
        except Exception as e:
            logger.error(f"清理过程中出错: {e}")
            self.clean_queue.put(('error', str(e)))

    def _check_clean_queue(self):
        """检查清理线程队列"""
        try:
            status, data = self.clean_queue.get_nowait()
            
            if status == 'success':
                self.on_clean_finished(data)
            elif status == 'error':
                messagebox.showerror("清理错误", f"清理过程中出错: {data}")
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
                self.scan_button.config(state=tk.NORMAL)
                self.clean_button.config(state=tk.NORMAL)
                self.clean_all_button.config(state=tk.NORMAL)
                self.select_all_button.config(state=tk.NORMAL)
                self.deselect_all_button.config(state=tk.NORMAL)
                
        except queue.Empty:
            self.after(100, self._check_clean_queue)

    def perform_clean(self):
        """已弃用的方法，保留以防止引用错误"""
        pass

    def start_clean_all(self):
        """开始一键清理所有项目"""
        if not any(self.scan_results.values()):
            messagebox.showinfo("清理", "没有可清理的项目")
            return

        # 将所有项目加入选择列表
        all_items = []
        for category, items in self.scan_results.items():
            all_items.extend(items)

        if not all_items:
            messagebox.showinfo("清理", "没有可清理的项目")
            return

        # 获取选项
        options = {
            'backup': self.backup_var.get(),
            'backup_dir': self.backup_dir_var.get()
        }
        self.cleaner.set_options(options)

        # 确认清理
        confirm = messagebox.askyesno("确认一键清理", 
                                    f"您确定要清理所有 {len(all_items)} 个项目吗？\n"
                                    f"这将永久删除这些文件。")
        if not confirm:
            return

        # 禁用按钮
        self.scan_button.config(state=tk.DISABLED)
        self.clean_button.config(state=tk.DISABLED)
        self.clean_all_button.config(state=tk.DISABLED)
        self.select_all_button.config(state=tk.DISABLED)
        self.deselect_all_button.config(state=tk.DISABLED)

        # 显示进度
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()
        self.status_label.config(text="正在清理，请稍候...")

        # 创建一个队列用于线程通信
        self.clean_all_queue = queue.Queue()
        
        # 创建并启动清理线程
        clean_all_thread = threading.Thread(target=lambda: self._clean_all_thread_task(all_items))
        clean_all_thread.daemon = True
        clean_all_thread.start()
        
        # 定期检查队列
        self.after(100, self._check_clean_all_queue)

    def _clean_all_thread_task(self, items):
        """在单独的线程中执行一键清理任务"""
        try:
            results = self.cleaner.clean_selected(items)
            self.clean_all_queue.put(('success', results))
        except Exception as e:
            logger.error(f"一键清理过程中出错: {e}")
            self.clean_all_queue.put(('error', str(e)))

    def _check_clean_all_queue(self):
        """检查一键清理线程队列"""
        try:
            status, data = self.clean_all_queue.get_nowait()
            
            if status == 'success':
                self.on_clean_all_finished(data)
            elif status == 'error':
                messagebox.showerror("清理错误", f"一键清理过程中出错: {data}")
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
                self.scan_button.config(state=tk.NORMAL)
                self.clean_button.config(state=tk.NORMAL)
                self.clean_all_button.config(state=tk.NORMAL)
                self.select_all_button.config(state=tk.NORMAL)
                self.deselect_all_button.config(state=tk.NORMAL)
                
        except queue.Empty:
            self.after(100, self._check_clean_all_queue)

    def perform_clean_all(self):
        """已弃用的方法，保留以防止引用错误"""
        pass

    def on_clean_finished(self, results):
        """清理完成后的处理"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_button.config(state=tk.NORMAL)
        self.clean_all_button.config(state=tk.NORMAL)

        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])
        skipped = results.get('skipped', [])

        message = f"清理完成，已释放空间: {self.format_size(freed_space)}"
        if skipped:
            message += f"，{len(skipped)} 个文件正在使用已跳过"
        if errors:
            message += f"，{len(errors)} 个错误"

        self.status_label.config(text=message)

        # 被占用的文件属于预期内的跳过，不算错误
        if skipped:
            messagebox.showinfo(
                "清理完成",
                f"有 {len(skipped)} 个项目正被其他程序使用，已自动跳过。\n\n"
                f"这类文件通常会在相关程序退出后自动清理。",
            )

        # 仅真正的失败才弹错误警告
        if errors:
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            messagebox.showwarning("清理错误", f"清理过程中发生 {len(errors)} 个错误\n\n{error_details}")

        # 更新磁盘信息
        self.update_disk_info()

    def on_clean_all_finished(self, results):
        """一键清理完成后的处理"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_button.config(state=tk.NORMAL)
        self.clean_all_button.config(state=tk.NORMAL)

        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])
        skipped = results.get('skipped', [])

        message = f"一键清理完成，已释放空间: {self.format_size(freed_space)}"
        if skipped:
            message += f"，{len(skipped)} 个文件正在使用已跳过"
        if errors:
            message += f"，{len(errors)} 个错误"

        self.status_label.config(text=message)

        # 仅真正的失败才弹错误警告
        if errors:
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            messagebox.showwarning("清理错误", f"清理过程中发生 {len(errors)} 个错误\n\n{error_details}")

        # 显示清理结果
        result = messagebox.askquestion("清理完成", 
                                     f"一键清理完成\n\n已释放空间: {self.format_size(freed_space)}\n"
                                     f"跳过(正在使用): {len(skipped)}\n错误数量: {len(errors)}\n\n是否需要重新扫描系统?")
        # 更新磁盘信息
        self.update_disk_info()
        
        # 仅当用户确认时才重新扫描
        if result == 'yes':
            self.start_scan()

    @staticmethod
    def format_size(size_bytes):
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"

    def browse_backup_dir(self):
        """浏览选择备份目录"""
        backup_dir = filedialog.askdirectory(
            title="选择备份目录",
            initialdir=self.cleaner.backup_dir
        )

        if backup_dir:
            self.backup_dir_var.set(backup_dir)
            # 更新清理器的备份目录
            self.cleaner.set_options({'backup_dir': backup_dir})

    def open_backup_manager(self):
        """打开备份管理窗口"""
        BackupManagerWindow(self, self.cleaner)

    def open_settings(self):
        """打开软件配置弹窗（已打开则前置）"""
        dialog = getattr(self, '_settings_dialog', None)
        if dialog is not None and dialog.winfo_exists():
            dialog.lift()
            dialog.focus_set()
            return
        self._settings_dialog = SettingsDialog(self)

    def select_all_items(self):
        """全选所有项目"""
        # 选中所有类别
        for category_id in self.result_tree.get_children():
            # 设置类别项为选中状态
            self.result_tree.item(category_id, open=True)  # 展开类别

            # 选中该类别下的所有文件
            for item_id in self.result_tree.get_children(category_id):
                self.result_tree.selection_add(item_id)

        # 更新清理按钮状态
        self.clean_button.config(state=tk.NORMAL)

    def deselect_all_items(self):
        """取消全选"""
        # 取消选中所有项目
        self.result_tree.selection_remove(self.result_tree.selection())

        # 更新清理按钮状态
        self.clean_button.config(state=tk.DISABLED)


def main():
    """应用程序入口点"""
    logger.info(f"启动 {APP_NAME} v{VERSION}")

    app = CleanerApp()
    app.mainloop()

    logger.info(f"{APP_NAME} 已退出")

if __name__ == "__main__":
    main()