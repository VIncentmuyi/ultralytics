import os
import glob

# 设置参数 - 直接在这里修改
LABEL_DIR = "D:/Y.work/code/data/changsha/crops/labels"  # 修改为你的标注文件目录


# 处理所有标注文件
def convert_to_buildings():
    # 获取所有标注文件
    label_files = glob.glob(os.path.join(LABEL_DIR, "*.txt"))
    print(f"找到 {len(label_files)} 个标注文件")

    # 创建或更新classes.txt文件
    classes_file = os.path.join(LABEL_DIR, "classes.txt")
    with open(classes_file, 'w', encoding='utf-8') as f:
        f.write("buildings\n")
    print(f"已创建/更新类别文件: {classes_file}")

    # 处理每个标注文件
    for i, label_file in enumerate(label_files):
        # 跳过classes.txt文件
        if os.path.basename(label_file) == "classes.txt":
            continue

        try:
            # 读取文件内容
            with open(label_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 修改内容
            modified_lines = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:  # 确保行有足够的数据
                    parts[0] = "0"  # 将类别ID修改为0
                    modified_lines.append(" ".join(parts) + "\n")

            # 写回原文件
            with open(label_file, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

            # 显示进度
            if (i + 1) % 100 == 0 or (i + 1) == len(label_files):
                print(f"已处理 {i + 1}/{len(label_files)} 个文件")

        except Exception as e:
            print(f"处理文件 {label_file} 出错: {e}")

    print("完成! 所有标注文件已修改为'buildings'类别(ID: 0)")


if __name__ == "__main__":
    # 执行转换
    answer = input("此操作将修改原始标注文件，确定继续? (y/n): ")
    if answer.lower() == 'y':
        convert_to_buildings()
    else:
        print("操作已取消")