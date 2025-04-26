import json
import os


def labelme2yolo_det(json_dir, labels_dir, class_file=None):
    """
    将labelme格式的JSON文件转换为YOLO格式的TXT文件

    参数:
    json_dir: 存放JSON文件的目录
    labels_dir: 存放输出TXT文件的目录
    class_file: 可选，用于保存类别列表的文件路径

    返回:
    class_list: 所有类别的列表
    """
    # 收集所有类别
    print("第一步：收集所有类别...")
    class_dict = {}  # 使用字典来存储类别和对应索引

    # 首先扫描所有JSON文件以收集所有唯一类别
    for filename in os.listdir(json_dir):
        if not filename.endswith('.json'):
            continue

        json_path = os.path.join(json_dir, filename)
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                file_in = json.load(f)
                shapes = file_in.get("shapes", [])

                for shape in shapes:
                    label = shape.get('label')
                    if label and label not in class_dict:
                        class_dict[label] = len(class_dict)  # 分配新的索引
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")

    class_list = list(class_dict.keys())
    print(f"找到 {len(class_list)} 个唯一类别: {class_list}")

    # 如果指定了类别文件，则保存类别列表
    if class_file:
        with open(class_file, "w", encoding="utf-8") as f:
            for class_name in class_list:
                f.write(f"{class_name}\n")
        print(f"类别列表已保存到: {class_file}")

    # 创建输出目录
    os.makedirs(labels_dir, exist_ok=True)
    print(f"创建输出目录: {labels_dir}")

    # 转换文件
    print("第二步：转换文件...")
    for filename in os.listdir(json_dir):
        if not filename.endswith('.json'):
            continue

        json_path = os.path.join(json_dir, filename)
        txt_filename = os.path.basename(filename).replace(".json", ".txt")
        txt_path = os.path.join(labels_dir, txt_filename)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                file_in = json.load(f)
                shapes = file_in.get("shapes", [])
                img_width = file_in.get("imageWidth", 0)
                img_height = file_in.get("imageHeight", 0)

                if img_width <= 0 or img_height <= 0:
                    print(f"警告: {filename} 中的图像尺寸无效: {img_width}x{img_height}")
                    continue

                with open(txt_path, "w+", encoding="utf-8") as file_handle:
                    valid_shapes = 0
                    for shape in shapes:
                        try:
                            label = shape.get('label')
                            if not label:
                                continue

                            # 获取类别索引
                            class_idx = class_dict.get(label)
                            if class_idx is None:
                                continue  # 不应该发生，但为了安全起见

                            # 检查形状类型和点数量
                            shape_type = shape.get('shape_type', '')
                            points = shape.get('points', [])

                            # 处理矩形（两点）
                            if shape_type == 'rectangle' and len(points) == 2:
                                [[x1, y1], [x2, y2]] = points
                            # 处理多边形类型，找出边界框
                            elif shape_type == 'polygon' and len(points) >= 3:
                                x_coords = [p[0] for p in points]
                                y_coords = [p[1] for p in points]
                                x1, x2 = min(x_coords), max(x_coords)
                                y1, y2 = min(y_coords), max(y_coords)
                            # 跳过其他形状类型
                            else:
                                print(f"警告: {filename} 中有不支持的形状类型: {shape_type}")
                                continue

                            # 归一化坐标
                            x1, x2 = x1 / img_width, x2 / img_width
                            y1, y2 = y1 / img_height, y2 / img_height

                            # 计算YOLO格式: <class_idx> <center_x> <center_y> <width> <height>
                            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2  # 中心点
                            w, h = abs(x2 - x1), abs(y2 - y1)  # 宽高

                            # 写入YOLO格式
                            line = f"{class_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n"
                            file_handle.write(line)
                            valid_shapes += 1

                        except Exception as e:
                            print(f"处理文件 {filename} 中的标注时出错: {e}")

                    print(f"转换完成: {txt_filename} (处理了 {valid_shapes} 个标注)")

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")

    print("转换完成！")
    return class_list


if __name__ == "__main__":
    # 设置路径
    json_folder = r"D:\Y.work\code\data\changsha\jsonlabel"  # 替换为你的JSON文件目录
    output_folder = r"D:\Y.work\code\data\changsha\label"  # 替换为你的输出目录
    class_file_path = r"D:\Y.work\code\data\changsha\classes.txt"  # 类别文件保存路径

    # 执行转换
    classes = labelme2yolo_det(json_folder, output_folder, class_file_path)
    print(f"总共找到 {len(classes)} 个类别")