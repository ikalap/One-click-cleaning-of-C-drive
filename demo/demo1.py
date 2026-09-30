import mftparser


if __name__ == '__main__':
    # 扫描C盘，返回所有活跃条目
    results = mftparser.ScanVolume("C:", only_active=True)

    # 筛选大于1GB的文件
    print("扫描开始")
    large_files = []
    for entry in results:
        # entry[7] 是文件大小，entry[6] 是路径，entry[8] 是是否为目录
        if not entry[8] and entry[7] > 1073741824:
            large_files.append((entry[6], entry[7]))
    print("扫描结束")

    for path, size in sorted(large_files, key=lambda x: x[1], reverse=True):
        print(f"{size / (1024**3):.2f} GB - {path}")
