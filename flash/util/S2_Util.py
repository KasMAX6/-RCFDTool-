import hashlib
import os
import shutil
import subprocess

import rasterio
from rasterio.transform import from_bounds
from PIL import Image
import numpy as np

import rasterio
import numpy as np
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

from flash.model.Sentinel2Image import Sentinel2Image


def generate_md5_filename(original_filename):
    """
    根据原始文件名生成一个MD5哈希值作为新文件名，并保留原始扩展名。

    Args:
        original_filename (str): 原始文件名，例如 "my_document.pdf"。

    Returns:
        str: 基于MD5的新文件名，例如 "e8d939689b912c29b62eab8682b68d7c.pdf"。
    """
    # 1. 确保文件名是字符串类型
    if not isinstance(original_filename, str):
        raise TypeError("Filename must be a string.")

    # 2. 分离文件名和扩展名
    # os.path.splitext("my_doc.txt") 会返回 ('my_doc', '.txt')
    _, file_extension = os.path.splitext(original_filename)

    # 3. 将原始文件名编码为字节串（哈希函数要求）
    encoded_filename = original_filename.encode('utf-8')

    # 4. 计算MD5哈希值
    md5_hash = hashlib.md5(encoded_filename).hexdigest()

    # 5. 组合新的文件名
    new_filename = f"{md5_hash}{file_extension}"

    return new_filename


def create_mosaic_with_gdal(image_list, base_path, write_thumbnail_to_file_callback, gdal_bin_path,pixel_size):
    """
    使用 GDAL 工具链创建影像镶嵌。

    :param image_list: 包含影像信息的对象列表 (例如您的 image_tuple)。
    :param base_path: 存放影像的根目录 (例如 'E:\\pysiderLearn\\...\\bylk')。
    :param output_vrt_path: 输出的 VRT 文件的完整路径。
    :param output_tif_path: (可选) 输出的最终 GeoTIFF 文件的完整路径。
    """
    os.makedirs(os.path.join(base_path, 'mosaic'), exist_ok=True)  ###性能优化，这里一直调用
    output_vrt_path = os.path.join(base_path, 'mosaic', 'mosaic.vrt').replace('\\', '/')
    output_tif_path = os.path.join(base_path, 'mosaic')
    # 1. 生成所有待镶嵌影像的完整路径列表
    file_paths = []
    print("正在收集文件路径...")
    for image in image_list:
        tif_path = os.path.join(base_path, image.tile, image.id + f'_{pixel_size}.tif')
        if os.path.exists(tif_path):
            file_paths.append(tif_path)
        else:
            print(f"警告：文件不存在，将跳过: {tif_path}")

    if not file_paths:
        print("错误：没有找到任何有效的影像文件进行镶嵌。")
        return

    # 2. 构建并执行 gdalbuildvrt 命令
    # -overwrite: 如果输出文件已存在，则覆盖它
    # -input_file_list: 从一个文本文件中读取输入文件列表，避免命令行过长

    # 为了处理大量文件，最好将文件列表写入一个临时文件
    file_list_txt = 'file_list.txt'
    with open(file_list_txt, 'w') as f:
        f.write('\n'.join(file_paths))
    ## if file_paths is one 那么直接复制即可不需要镶嵌mosaic
    # if len(file_paths) == 1:
    #     shutil.copy(file_paths[0], output_tif_path)
    #     file_name_new = generate_md5_filename(os.path.basename(output_tif_path))
    #     file_name_new = os.path.join(output_tif_path, file_name_new).replace('\\', '/')
    #     write_thumbnail_to_file_callback(
    #         [{'thumbnail_url': file_name_new, 'item_ids': os.path.basename(output_tif_path)}])
    #     return

    print(f"即将创建虚拟栅格 (VRT) 文件到: {output_vrt_path}")
    vrt_command = [
        os.path.join(gdal_bin_path, 'gdalbuildvrt'),
        '-overwrite',
        '-input_file_list', file_list_txt,
        output_vrt_path
    ]

    try:
        # 使用 subprocess.run 来执行命令，并捕获输出
        result = subprocess.run(vrt_command, check=True, capture_output=True, text=True)
        print("VRT 文件创建成功！")
        # print(result.stdout) # 如果需要可以打印详细输出
    except FileNotFoundError:
        print("错误: 'gdalbuildvrt' 命令未找到。请确保 GDAL 已经安装并且其路径已添加到系统环境变量中。")
        return
    except subprocess.CalledProcessError as e:
        print(f"创建 VRT 文件时出错:\n{e.stderr}")
        return
    finally:
        os.remove(file_list_txt)  # 删除临时文件

    # 3. (可选) 如果提供了输出 TIF 路径，则将 VRT 转换为 GeoTIFF
    if output_tif_path:
        item_ids = ','.join(os.path.basename(obj.id) for obj in image_list)
        file_name = os.path.join(output_tif_path, item_ids + '.tif').replace('\\', '/')
        file_name_new = generate_md5_filename(file_name)
        file_name_new = os.path.join(output_tif_path, file_name_new).replace('\\', '/')
        print(f"正在将 VRT 转换为真实的 GeoTIFF 文件到: {file_name_new}")
        # -co "COMPRESS=LZW": 使用 LZW 无损压缩，减小文件体积
        # -co "TILED=YES": 使用瓦片存储，提高读取效率
        # -co "BIGTIFF=YES": 如果输出文件可能超过 4GB，则使用 BIGTIFF
        translate_command = [
            os.path.join(gdal_bin_path, 'gdal_translate'),
            '-co', 'COMPRESS=LZW',
            '-co', 'TILED=YES',
            '-co', 'BIGTIFF=YES',
            output_vrt_path,
            file_name_new
        ]

        try:
            result = subprocess.run(translate_command, check=True, capture_output=True, text=True)
            ### 输出jpg
            file_name_jpg = file_name_new.replace('.tif', '.png')
            with Image.open(file_name_new) as img:
                img.save(file_name_jpg, 'png')
            write_thumbnail_to_file_callback(
                [{'thumbnail_url': file_name_jpg, 'item_ids': item_ids}])
            print("GeoTIFF 文件转换成功！")
        except FileNotFoundError:
            print("错误: 'gdal_translate' 命令未找到。请确保 GDAL 已经安装并且其路径已添加到系统环境变量中。")
            return
        except subprocess.CalledProcessError as e:
            print(f"转换 GeoTIFF 时出错:\n{e.stderr}")
            return
        finally:
            os.remove(output_vrt_path)  # 删除临时文件



def png_to_geotiff_with_rasterio(png_path, coordinates, output_path):
    """
    使用rasterio将PNG转换为GeoTIFF。
    该函数会自动从传入的坐标列表中计算出正确的地理边界。
    """
    # 从坐标列表中提取外接矩形边界
    # 假设坐标列表格式为 [[lon1, lat1], [lon2, lat2], ...]
    lons = [c[0] for c in coordinates]
    lats = [c[1] for c in coordinates]

    west = min(lons)
    south = min(lats)
    east = max(lons)
    north = max(lats)

    # 检查提取的坐标
    print(f"提取的地理边界: west={west}, south={south}, east={east}, north={north}")

    # 读取PNG图像
    try:
        with Image.open(png_path) as img:
            img_array = np.array(img)
    except FileNotFoundError:
        print(f"错误: 文件 '{png_path}' 未找到。请确保路径正确。")
        return

    # 如果是RGB图像，需要调整维度
    if len(img_array.shape) == 3:
        height, width, bands = img_array.shape
        # 转换为rasterio格式 (bands, height, width)
        img_array = np.transpose(img_array, (2, 0, 1))
    else:
        height, width = img_array.shape
        bands = 1
        img_array = img_array.reshape(1, height, width)

    # 创建仿射变换
    transform = from_bounds(west, south, east, north, width, height)

    # 写入GeoTIFF
    try:
        with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=bands,
                dtype=img_array.dtype,
                crs='EPSG:4326',  # 常见的WGS84坐标系
                transform=transform,
                compress='lzw'
        ) as dst:
            dst.write(img_array)
        print(f"转换完成: {output_path}")
    except Exception as e:
        print(f"写入GeoTIFF时发生错误: {e}")


if __name__ == "__main__":
    pass
