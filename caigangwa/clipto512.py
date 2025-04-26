import os
from PIL import Image
import argparse
import math


def tile_images(input_folder, output_folder):
    """
    将指定文件夹中的所有JPG图片分割成多个512×512的小块并转换为PNG格式

    参数:
    input_folder -- 包含JPG图片的文件夹路径
    output_folder -- 存储处理后PNG图片的文件夹路径
    """
    # 创建输出文件夹（如果不存在）
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取输入文件夹中的所有文件
    files = os.listdir(input_folder)

    # 计数器
    processed_files = 0
    total_tiles = 0
    skipped = 0

    # 处理每个文件
    for filename in files:
        # 只处理JPG文件
        if filename.lower().endswith(('.jpg', '.jpeg')):
            try:
                # 构建完整的文件路径
                input_path = os.path.join(input_folder, filename)

                # 打开图像
                img = Image.open(input_path)

                # 获取原始图像尺寸
                width, height = img.size

                # 计算需要的行数和列数
                num_cols = math.ceil(width / 512)
                num_rows = math.ceil(height / 512)

                # 创建图片名称的基础部分（不含扩展名）
                base_name = os.path.splitext(filename)[0]

                # 图片计数器
                tile_count = 0

                # 分割图片
                for row in range(num_rows):
                    for col in range(num_cols):
                        # 计算当前小块的左上角和右下角坐标
                        left = col * 512
                        top = row * 512
                        right = min(left + 512, width)
                        bottom = min(top + 512, height)

                        # 裁剪当前小块
                        tile = img.crop((left, top, right, bottom))

                        # 如果裁剪出的小块小于512×512，创建一个新的512×512图像并居中放置
                        if right - left < 512 or bottom - top < 512:
                            new_tile = Image.new(img.mode, (512, 512), (255, 255, 255))  # 白色背景
                            new_tile.paste(tile, (0, 0))
                            tile = new_tile

                        # 生成输出文件名
                        tile_filename = f"{base_name}_tile_{row}_{col}.png"
                        tile_path = os.path.join(output_folder, tile_filename)

                        # 保存为PNG格式
                        tile.save(tile_path, 'PNG')

                        tile_count += 1

                processed_files += 1
                total_tiles += tile_count
                print(f"处理完成: {filename} -> 生成了 {tile_count} 个512×512的小块")

            except Exception as e:
                skipped += 1
                print(f"处理 {filename} 时出错: {str(e)}")
        else:
            skipped += 1
            print(f"跳过非JPG文件: {filename}")

    print(f"\n处理完成! 成功处理了 {processed_files} 个文件, 生成了 {total_tiles} 个小块, 跳过了 {skipped} 个文件。")


if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='将JPG图像分割为多个512×512小块并转换为PNG格式')
    parser.add_argument('--input', '-i', required=True, help='输入文件夹路径')
    parser.add_argument('--output', '-o', required=True, help='输出文件夹路径')

    # 解析命令行参数
    args = parser.parse_args()

    # 执行分割和转换
    tile_images(args.input, args.output)