import os
import json
import math
from PIL import Image
import argparse
import numpy as np
import shutil


def crop_images_and_labels(json_dir, image_dir, label_dir, output_image_dir, output_label_dir, crop_size=640):
    """
    以每个标注位置为中心，同时裁剪图像和对应的标注文件

    参数:
    json_dir -- 包含labelme JSON文件的文件夹路径
    image_dir -- 包含原始图像的文件夹路径
    label_dir -- 包含YOLO格式标注文件的文件夹路径
    output_image_dir -- 输出裁剪图像的文件夹路径
    output_label_dir -- 输出裁剪标注的文件夹路径
    crop_size -- 裁剪图像的大小（宽度和高度），默认为640
    """
    # 创建输出文件夹
    os.makedirs(output_image_dir, exist_ok=True)
    os.makedirs(output_label_dir, exist_ok=True)

    # 统计计数器
    processed_files = 0
    total_crops = 0
    skipped_files = 0
    skipped_annotations = 0

    # 遍历JSON文件
    for filename in os.listdir(json_dir):
        if not filename.endswith('.json'):
            continue

        json_path = os.path.join(json_dir, filename)
        base_name = os.path.splitext(filename)[0]

        # 查找对应的图像文件
        img_filename = None
        potential_image_extensions = ['.jpg', '.jpeg', '.JPG', '.JPEG']

        for ext in potential_image_extensions:
            potential_img_path = os.path.join(image_dir, base_name + ext)
            if os.path.exists(potential_img_path):
                img_filename = base_name + ext
                break

        if img_filename is None:
            print(f"无法找到对应的图像文件: {base_name}.*")
            skipped_files += 1
            continue

        img_path = os.path.join(image_dir, img_filename)

        # 查找对应的标注文件
        label_filename = base_name + '.txt'
        label_path = os.path.join(label_dir, label_filename)

        if not os.path.exists(label_path):
            print(f"无法找到对应的标注文件: {label_filename}")
            skipped_files += 1
            continue

        try:
            # 读取JSON文件以获取标注位置
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # 读取图像
            img = Image.open(img_path)
            img_width, img_height = img.size

            # 读取YOLO格式标注文件
            with open(label_path, 'r', encoding='utf-8') as f:
                yolo_labels = f.readlines()

            # 处理每个标注
            crops_count = 0
            processed_annotations = set()  # 用于跟踪已处理的标注中心点

            for i, shape in enumerate(json_data.get('shapes', [])):
                try:
                    # 获取标注类型和点
                    shape_type = shape.get('shape_type', '')
                    points = shape.get('points', [])
                    label = shape.get('label', 'unknown')

                    # 计算中心点
                    if shape_type == 'rectangle' and len(points) == 2:
                        # 矩形: 两个点分别是左上角和右下角
                        [[x1, y1], [x2, y2]] = points
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                    elif shape_type == 'polygon' and len(points) >= 3:
                        # 多边形: 计算所有点的平均位置
                        x_coords = [p[0] for p in points]
                        y_coords = [p[1] for p in points]
                        center_x = sum(x_coords) / len(x_coords)
                        center_y = sum(y_coords) / len(y_coords)
                    else:
                        print(f"跳过不支持的标注类型 {shape_type} 在文件 {filename}")
                        skipped_annotations += 1
                        continue

                    # 四舍五入到整数
                    center_x = int(round(center_x))
                    center_y = int(round(center_y))

                    # 检查是否已经处理过该中心点附近的区域（防止重复裁剪）
                    threshold = crop_size // 4
                    is_duplicate = False

                    for processed_x, processed_y in processed_annotations:
                        if abs(processed_x - center_x) < threshold and abs(processed_y - center_y) < threshold:
                            is_duplicate = True
                            break

                    if is_duplicate:
                        continue

                    # 记录已处理的中心点
                    processed_annotations.add((center_x, center_y))

                    # 计算裁剪框的左上角和右下角
                    half_size = crop_size // 2
                    left = center_x - half_size
                    top = center_y - half_size
                    right = left + crop_size
                    bottom = top + crop_size

                    # 处理边界情况
                    if left < 0:
                        right -= left  # 向右移动裁剪框
                        left = 0
                    if top < 0:
                        bottom -= top  # 向下移动裁剪框
                        top = 0
                    if right > img_width:
                        left -= (right - img_width)  # 向左移动裁剪框
                        right = img_width
                    if bottom > img_height:
                        top -= (bottom - img_height)  # 向上移动裁剪框
                        bottom = img_height

                    # 二次边界检查，确保裁剪框不会超出图像范围
                    left = max(0, left)
                    top = max(0, top)
                    right = min(img_width, right)
                    bottom = min(img_height, bottom)

                    # 确保裁剪框是有效的
                    if right - left < crop_size or bottom - top < crop_size:
                        # 如果裁剪框小于所需的大小，我们需要调整边界并可能填充
                        actual_width = right - left
                        actual_height = bottom - top

                        # 如果裁剪区域太小，跳过
                        if actual_width < crop_size / 2 or actual_height < crop_size / 2:
                            print(f"裁剪区域太小，跳过: {actual_width}x{actual_height} 在文件 {filename}")
                            continue

                    # 裁剪图像
                    crop = img.crop((left, top, right, bottom))

                    # 如果裁剪出的图像小于crop_size×crop_size，创建新的图像并居中放置
                    padding_x, padding_y = 0, 0
                    if crop.width < crop_size or crop.height < crop_size:
                        new_crop = Image.new(img.mode, (crop_size, crop_size), (0, 0, 0))  # 黑色背景
                        padding_x = (crop_size - crop.width) // 2
                        padding_y = (crop_size - crop.height) // 2
                        new_crop.paste(crop, (padding_x, padding_y))
                        crop = new_crop

                    # 生成输出文件名
                    crop_img_filename = f"{base_name}_crop_{i}_{label}_{center_x}_{center_y}.jpg"
                    crop_label_filename = f"{base_name}_crop_{i}_{label}_{center_x}_{center_y}.txt"

                    crop_img_path = os.path.join(output_image_dir, crop_img_filename)
                    crop_label_path = os.path.join(output_label_dir, crop_label_filename)

                    # 保存裁剪后的图像
                    crop.save(crop_img_path, 'JPEG', quality=95)

                    # 调整YOLO标注坐标
                    new_labels = []
                    for yolo_line in yolo_labels:
                        yolo_line = yolo_line.strip()
                        if not yolo_line:
                            continue

                        parts = yolo_line.split()
                        if len(parts) != 5:
                            continue

                        cls_id, x_center, y_center, width, height = parts

                        # 将归一化坐标转回像素坐标
                        x_center = float(x_center) * img_width
                        y_center = float(y_center) * img_height
                        width = float(width) * img_width
                        height = float(height) * img_height

                        # 计算边界框的左上角和右下角
                        box_left = x_center - width / 2
                        box_top = y_center - height / 2
                        box_right = x_center + width / 2
                        box_bottom = y_center + height / 2

                        # 检查标注框是否与裁剪区域有重叠
                        if box_right < left or box_left > right or box_bottom < top or box_top > bottom:
                            # 标注框完全在裁剪区域外，跳过
                            continue

                        # 裁剪标注框到裁剪区域
                        box_left = max(box_left, left)
                        box_top = max(box_top, top)
                        box_right = min(box_right, right)
                        box_bottom = min(box_bottom, bottom)

                        # 如果裁剪后的标注框太小，也跳过
                        if box_right - box_left < 1 or box_bottom - box_top < 1:
                            continue

                        # 调整坐标到裁剪图像中的位置
                        box_left -= left - padding_x
                        box_top -= top - padding_y
                        box_right -= left - padding_x
                        box_bottom -= top - padding_y

                        # 转回YOLO格式的归一化坐标
                        new_x_center = (box_left + box_right) / 2 / crop_size
                        new_y_center = (box_top + box_bottom) / 2 / crop_size
                        new_width = (box_right - box_left) / crop_size
                        new_height = (box_bottom - box_top) / crop_size

                        # 确保坐标在[0,1]范围内
                        new_x_center = max(0, min(1, new_x_center))
                        new_y_center = max(0, min(1, new_y_center))
                        new_width = max(0, min(1, new_width))
                        new_height = max(0, min(1, new_height))

                        # 添加到新标注列表
                        new_labels.append(
                            f"{cls_id} {new_x_center:.6f} {new_y_center:.6f} {new_width:.6f} {new_height:.6f}")

                    # 保存新的标注文件
                    with open(crop_label_path, 'w', encoding='utf-8') as f:
                        for new_label in new_labels:
                            f.write(new_label + '\n')

                    crops_count += 1

                except Exception as e:
                    print(f"处理标注 {i} 时出错 在文件 {filename}: {str(e)}")
                    skipped_annotations += 1

            processed_files += 1
            total_crops += crops_count
            print(f"处理完成: {filename} -> 生成了 {crops_count} 个 {crop_size}×{crop_size} 的裁剪图像和标注")

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            skipped_files += 1

    # 复制classes.txt文件到输出标注目录，如果存在的话
    classes_path = os.path.join(label_dir, 'classes.txt')
    if os.path.exists(classes_path):
        shutil.copy(classes_path, os.path.join(output_label_dir, 'classes.txt'))
        print(f"已复制classes.txt文件到输出目录: {output_label_dir}")

    print(
        f"\n处理完成! 成功处理了 {processed_files} 个文件, 生成了 {total_crops} 个裁剪图像和标注, 跳过了 {skipped_files} 个文件和 {skipped_annotations} 个标注。")


if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='以标注位置为中心裁剪图像和标注文件')
    parser.add_argument('--json_dir', '-j', required=True, help='包含labelme JSON文件的文件夹路径')
    parser.add_argument('--image_dir', '-i', required=True, help='包含原始图像的文件夹路径')
    parser.add_argument('--label_dir', '-l', required=True, help='包含YOLO格式标注文件的文件夹路径')
    parser.add_argument('--output_image_dir', '-oi', required=True, help='输出裁剪图像的文件夹路径')
    parser.add_argument('--output_label_dir', '-ol', required=True, help='输出裁剪标注的文件夹路径')
    parser.add_argument('--crop_size', '-s', type=int, default=640, help='裁剪图像的大小 (默认: 640)')

    # 解析命令行参数
    args = parser.parse_args()

    # 执行裁剪
    crop_images_and_labels(
        args.json_dir,
        args.image_dir,
        args.label_dir,
        args.output_image_dir,
        args.output_label_dir,
        args.crop_size
    )

#  python clipto512.py --json_dir D:\Y.work\code\data\changsha\jsonlabel --image_dir D:\Y.work\code\data\changsha\image --label_dir D:\Y.work\code\data\changsha\label --output_image_dir D:\Y.work\code\data\changsha\crops\images --output_label_dir D:\Y.work\code\data\changsha\crops\labels --crop_size 640