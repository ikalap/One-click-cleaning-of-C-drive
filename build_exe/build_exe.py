"""
打包C盘清理工具为EXE文件
"""

import os
import shutil
import subprocess
import sys

# 脚本所在目录（build_exe）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根目录（build_exe 的上一级）
BASE_DIR = os.path.dirname(SCRIPT_DIR)

def build_exe():
    """使用PyInstaller打包应用为EXE文件"""
    print("开始打包C盘清理工具为EXE文件...")

    # 切换到项目根目录，确保后续相对路径正确
    os.chdir(BASE_DIR)

    main_py = os.path.join(BASE_DIR, 'main.py')
    icon_path = os.path.join(BASE_DIR, 'icons', 'cleaner.ico')

    # 创建输出目录
    if not os.path.exists('dist'):
        os.makedirs('dist')

    # 清理旧的构建文件
    if os.path.exists('build'):
        shutil.rmtree('build')

    # 根据平台选择路径分隔符
    add_data = '--add-data=icons;icons' if sys.platform.startswith('win') else '--add-data=icons:icons'

    # 使用PyInstaller打包
    cmd = [
        'pyinstaller',
        '--name=C盘清理工具',
        '--windowed',  # 无控制台窗口
        '--icon=' + icon_path,  # 图标
        add_data,  # 包含图标文件夹
        '--hidden-import=mftparser',  # MFT 扩展（try/except 导入，显式声明）
        '--collect-submodules=scanners',  # build_dedicated_strategies 用 importlib 动态导入 dedicated 模块
        '--noconfirm',  # 不询问覆盖
        '--clean',  # 清理临时文件
        '--specpath=dist',  # spec文件输出到dist目录
        main_py  # 主脚本
    ]

    # 执行打包命令
    subprocess.call(cmd)

    print("打包完成！")
    print(f"EXE文件位于: {os.path.abspath('dist/C盘清理工具/C盘清理工具.exe')}")

    # 创建ZIP文件
    shutil.make_archive(os.path.join('dist', 'C盘清理工具'), 'zip', 'dist/C盘清理工具')
    print(f"已创建ZIP文件: {os.path.abspath(os.path.join('dist', 'C盘清理工具.zip'))}")

if __name__ == '__main__':
    build_exe()
