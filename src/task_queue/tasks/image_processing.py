# Image Processing Tasks
# 图片处理相关任务

import os
import asyncio
import logging
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import hashlib

from .base import BaseTask, TaskResult, register_task
from ..storage.image_storage import ImageStorage

logger = logging.getLogger(__name__)


@register_task('src.queue.tasks.image_processing.download_images')
class DownloadImagesTask(BaseTask):
    """下载图片任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'image_urls' not in kwargs:
            raise ValueError("缺少必需参数: image_urls")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行图片下载任务"""
        try:
            image_urls = kwargs.get('image_urls', [])
            product_id = kwargs.get('product_id')
            batch_size = kwargs.get('batch_size', 10)
            resize_options = kwargs.get('resize_options', {})

            total_count = len(image_urls)
            downloaded_count = 0
            failed_count = 0

            self.update_progress(0, total_count, "开始下载图片")

            image_storage = ImageStorage()
            downloaded_images = []

            # 分批下载
            for i in range(0, len(image_urls), batch_size):
                batch_urls = image_urls[i:i + batch_size]

                for url in batch_urls:
                    try:
                        # 下载图片
                        image_info = self._download_single_image(
                            url, product_id, resize_options, image_storage
                        )

                        if image_info:
                            downloaded_images.append(image_info)
                            downloaded_count += 1
                        else:
                            failed_count += 1

                        # 更新进度
                        self.update_progress(
                            downloaded_count + failed_count,
                            total_count,
                            f"已下载 {downloaded_count} 张图片，失败 {failed_count} 张"
                        )

                    except Exception as e:
                        logger.error(f"下载图片失败 {url}: {e}")
                        failed_count += 1

            result_data = {
                'downloaded_count': downloaded_count,
                'failed_count': failed_count,
                'images': downloaded_images,
                'product_id': product_id
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"下载图片任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _download_single_image(
        self, url: str, product_id: str, resize_options: Dict[str, Any], image_storage: ImageStorage
    ) -> Optional[Dict[str, Any]]:
        """下载单张图片"""
        try:
            # 生成文件名
            file_ext = self._get_file_extension(url)
            if not file_ext:
                return None

            filename = f"{product_id}_{hashlib.md5(url.encode()).hexdigest()[:8]}{file_ext}"

            # 检查是否已存在
            if image_storage.exists(filename):
                return image_storage.get_info(filename)

            # 下载图片
            import aiohttp
            import tempfile

            async def download():
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content = await response.read()
                            return content
                        return None

            # 运行异步下载
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            content = loop.run_until_complete(download())
            loop.close()

            if not content:
                return None

            # 保存到存储
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                # 处理并保存图片
                saved_path = image_storage.save_image(
                    tmp_path, filename, resize_options=resize_options
                )

                return image_storage.get_info(filename)

            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"下载单张图片失败 {url}: {e}")
            return None

    def _get_file_extension(self, url: str) -> Optional[str]:
        """获取文件扩展名"""
        parsed = urlparse(url)
        path = parsed.path
        if '.' in path:
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                return ext
        return '.jpg'  # 默认扩展名


@register_task('src.queue.tasks.image_processing.resize_images')
class ResizeImagesTask(BaseTask):
    """调整图片大小任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'image_paths' not in kwargs:
            raise ValueError("缺少必需参数: image_paths")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行图片调整任务"""
        try:
            image_paths = kwargs.get('image_paths', [])
            target_sizes = kwargs.get('target_sizes', [(800, 600), (400, 300), (200, 150)])
            quality = kwargs.get('quality', 85)
            batch_size = kwargs.get('batch_size', 20)

            total_count = len(image_paths)
            processed_count = 0

            self.update_progress(0, total_count, "开始调整图片大小")

            image_storage = ImageStorage()
            resized_images = []

            # 分批处理
            for i in range(0, len(image_paths), batch_size):
                batch_paths = image_paths[i:i + batch_size]

                for image_path in batch_paths:
                    try:
                        # 调整图片大小
                        resized_versions = self._resize_single_image(
                            image_path, target_sizes, quality, image_storage
                        )

                        if resized_versions:
                            resized_images.extend(resized_versions)

                        processed_count += 1
                        self.update_progress(
                            processed_count,
                            total_count,
                            f"已处理 {processed_count} 张图片"
                        )

                    except Exception as e:
                        logger.error(f"调整图片失败 {image_path}: {e}")

            result_data = {
                'processed_count': processed_count,
                'resized_images': resized_images
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"调整图片大小任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _resize_single_image(
        self, image_path: str, target_sizes: List[Tuple[int, int]], quality: int, image_storage: ImageStorage
    ) -> List[Dict[str, Any]]:
        """调整单张图片大小"""
        try:
            from PIL import Image

            resized_versions = []
            original_image = Image.open(image_path)
            original_format = original_image.format or 'JPEG'

            for width, height in target_sizes:
                # 调整大小
                resized_image = original_image.copy()
                resized_image.thumbnail((width, height), Image.Resampling.LANCZOS)

                # 生成新文件名
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                new_filename = f"{base_name}_{width}x{height}.jpg"

                # 保存调整后的图片
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    resized_image.save(tmp, format='JPEG', quality=quality, optimize=True)
                    tmp_path = tmp.name

                try:
                    # 移动到存储位置
                    final_path = image_storage.save_resized_image(tmp_path, new_filename)

                    resized_versions.append({
                        'path': final_path,
                        'size': f"{width}x{height}",
                        'filename': new_filename
                    })

                finally:
                    os.unlink(tmp_path)

            return resized_versions

        except Exception as e:
            logger.error(f"调整单张图片失败 {image_path}: {e}")
            return []


@register_task('src.queue.tasks.image_processing.optimize_images')
class OptimizeImagesTask(BaseTask):
    """优化图片任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'image_paths' not in kwargs:
            raise ValueError("缺少必需参数: image_paths")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行图片优化任务"""
        try:
            image_paths = kwargs.get('image_paths', [])
            optimization_level = kwargs.get('level', 'medium')  # low, medium, high
            batch_size = kwargs.get('batch_size', 20)

            optimization_settings = {
                'low': {'quality': 90, 'optimize': True},
                'medium': {'quality': 75, 'optimize': True},
                'high': {'quality': 60, 'optimize': True}
            }

            settings = optimization_settings.get(optimization_level, optimization_settings['medium'])
            total_count = len(image_paths)
            optimized_count = 0

            self.update_progress(0, total_count, "开始优化图片")

            image_storage = ImageStorage()
            optimization_results = []

            # 分批优化
            for i in range(0, len(image_paths), batch_size):
                batch_paths = image_paths[i:i + batch_size]

                for image_path in batch_paths:
                    try:
                        # 优化图片
                        result = self._optimize_single_image(
                            image_path, settings, image_storage
                        )

                        if result:
                            optimization_results.append(result)
                            optimized_count += 1

                        self.update_progress(
                            optimized_count,
                            total_count,
                            f"已优化 {optimized_count} 张图片"
                        )

                    except Exception as e:
                        logger.error(f"优化图片失败 {image_path}: {e}")

            result_data = {
                'optimized_count': optimized_count,
                'results': optimization_results
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"优化图片任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _optimize_single_image(
        self, image_path: str, settings: Dict[str, Any], image_storage: ImageStorage
    ) -> Optional[Dict[str, Any]]:
        """优化单张图片"""
        try:
            from PIL import Image
            import os

            # 获取原始文件大小
            original_size = os.path.getsize(image_path)

            # 打开并优化图片
            with Image.open(image_path) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background

                # 生成优化后的文件名
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                optimized_filename = f"{base_name}_optimized.jpg"

                # 保存优化后的图片
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    img.save(tmp, format='JPEG', **settings)
                    tmp_path = tmp.name

            try:
                # 获取优化后文件大小
                optimized_size = os.path.getsize(tmp_path)
                compression_ratio = (original_size - optimized_size) / original_size * 100

                # 移动到存储位置
                final_path = image_storage.save_optimized_image(tmp_path, optimized_filename)

                return {
                    'original_path': image_path,
                    'optimized_path': final_path,
                    'original_size': original_size,
                    'optimized_size': optimized_size,
                    'compression_ratio': round(compression_ratio, 2),
                    'filename': optimized_filename
                }

            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"优化单张图片失败 {image_path}: {e}")
            return None


@register_task('src.queue.tasks.image_processing.generate_thumbnails')
class GenerateThumbnailsTask(BaseTask):
    """生成缩略图任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'image_paths' not in kwargs:
            raise ValueError("缺少必需参数: image_paths")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行缩略图生成任务"""
        try:
            image_paths = kwargs.get('image_paths', [])
            thumbnail_sizes = kwargs.get('sizes', [(150, 150), (300, 300)])
            crop_to_square = kwargs.get('crop_to_square', True)
            batch_size = kwargs.get('batch_size', 30)

            total_count = len(image_paths)
            generated_count = 0

            self.update_progress(0, total_count, "开始生成缩略图")

            image_storage = ImageStorage()
            generated_thumbnails = []

            # 分批生成
            for i in range(0, len(image_paths), batch_size):
                batch_paths = image_paths[i:i + batch_size]

                for image_path in batch_paths:
                    try:
                        # 生成缩略图
                        thumbnails = self._generate_single_thumbnails(
                            image_path, thumbnail_sizes, crop_to_square, image_storage
                        )

                        if thumbnails:
                            generated_thumbnails.extend(thumbnails)
                            generated_count += 1

                        self.update_progress(
                            generated_count,
                            total_count,
                            f"已生成 {generated_count} 张缩略图"
                        )

                    except Exception as e:
                        logger.error(f"生成缩略图失败 {image_path}: {e}")

            result_data = {
                'generated_count': generated_count,
                'thumbnails': generated_thumbnails
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"生成缩略图任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _generate_single_thumbnails(
        self, image_path: str, sizes: List[Tuple[int, int]], crop_to_square: bool, image_storage: ImageStorage
    ) -> List[Dict[str, Any]]:
        """为单张图片生成缩略图"""
        try:
            from PIL import Image

            thumbnails = []
            base_name = os.path.splitext(os.path.basename(image_path))[0]

            with Image.open(image_path) as img:
                for width, height in sizes:
                    # 复制图片进行处理
                    thumb_img = img.copy()

                    if crop_to_square:
                        # 裁剪为正方形
                        min_dim = min(img.size)
                        left = (img.width - min_dim) // 2
                        top = (img.height - min_dim) // 2
                        right = left + min_dim
                        bottom = top + min_dim
                        thumb_img = thumb_img.crop((left, top, right, bottom))

                    # 调整大小
                    thumb_img.thumbnail((width, height), Image.Resampling.LANCZOS)

                    # 生成文件名
                    thumb_filename = f"{base_name}_thumb_{width}x{height}.jpg"

                    # 保存缩略图
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                        thumb_img.save(tmp, format='JPEG', quality=85, optimize=True)
                        tmp_path = tmp.name

                    try:
                        # 移动到存储位置
                        final_path = image_storage.save_thumbnail(tmp_path, thumb_filename)

                        thumbnails.append({
                            'path': final_path,
                            'size': f"{width}x{height}",
                            'filename': thumb_filename
                        })

                    finally:
                        os.unlink(tmp_path)

            return thumbnails

        except Exception as e:
            logger.error(f"生成单张缩略图失败 {image_path}: {e}")
            return []