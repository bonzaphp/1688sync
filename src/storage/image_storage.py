"""
图片存储系统
"""
import hashlib
import io
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.parse import urlparse

import aiofiles
import aiohttp
from PIL import Image, ImageOps

from config.settings import app_settings

logger = logging.getLogger(__name__)


class ImageStorage:
    """图片存储管理器"""

    def __init__(self):
        self.base_path = Path(app_settings.storage_path)
        self.max_file_size = app_settings.max_file_size
        self.allowed_types = app_settings.allowed_image_types
        self.cdn_enabled = app_settings.cdn_enabled
        self.cdn_base_url = app_settings.cdn_base_url

        # 创建存储目录
        self._ensure_directories()

    def _ensure_directories(self):
        """确保存储目录存在"""
        directories = [
            self.base_path / "original",
            self.base_path / "thumbnail",
            self.base_path / "compressed",
            self.base_path / "temp",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, url: str) -> str:
        """根据URL生成文件哈希"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_image_path(self, product_id: Union[str, int], image_hash: str,
                       image_type: str = "original", extension: str = "jpg") -> Path:
        """获取图片存储路径"""
        # 按产品ID分目录存储
        product_dir = self.base_path / image_type / str(product_id)
        product_dir.mkdir(exist_ok=True)

        return product_dir / f"{image_hash}.{extension}"

    async def download_image(self, url: str, product_id: Union[str, int]) -> Tuple[bool, Optional[str], Optional[dict]]:
        """下载图片到本地存储"""
        try:
            # 生成文件哈希
            image_hash = self._get_file_hash(url)

            # 检查文件是否已存在
            local_path = self._get_image_path(product_id, image_hash)
            if local_path.exists():
                logger.debug(f"图片已存在: {local_path}")
                return True, str(local_path), await self._get_image_info(local_path)

            # 下载图片
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"下载图片失败: HTTP {response.status}, URL: {url}")
                        return False, None, {"error": f"HTTP {response.status}"}

                    # 检查文件大小
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        logger.error(f"图片文件过大: {content_length} bytes")
                        return False, None, {"error": "File too large"}

                    # 检查MIME类型
                    content_type = response.headers.get('content-type', '').lower()
                    if content_type not in self.allowed_types:
                        logger.error(f"不支持的图片类型: {content_type}")
                        return False, None, {"error": f"Unsupported type: {content_type}"}

                    # 读取图片数据
                    image_data = await response.read()

                    # 验证图片
                    try:
                        image = Image.open(io.BytesIO(image_data))
                        image.verify()  # 验证图片完整性
                    except Exception as e:
                        logger.error(f"图片验证失败: {e}")
                        return False, None, {"error": "Invalid image data"}

                    # 保存原图
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(image_data)

                    # 生成缩略图和压缩图
                    await self._process_image(local_path, product_id, image_hash)

                    image_info = await self._get_image_info(local_path)
                    logger.info(f"图片下载成功: {local_path}")
                    return True, str(local_path), image_info

        except aiohttp.ClientError as e:
            logger.error(f"网络错误下载图片: {url}, 错误: {e}")
            return False, None, {"error": f"Network error: {e}"}
        except Exception as e:
            logger.error(f"下载图片异常: {url}, 错误: {e}")
            return False, None, {"error": f"Exception: {e}"}

    async def _process_image(self, original_path: Path, product_id: Union[str, int], image_hash: str):
        """处理图片：生成缩略图和压缩图"""
        try:
            with Image.open(original_path) as img:
                # 自动旋转（基于EXIF）
                img = ImageOps.exif_transpose(img)

                # 转换为RGB模式（处理RGBA等）
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # 生成缩略图 (200x200)
                thumbnail_path = self._get_image_path(product_id, image_hash, "thumbnail", "jpg")
                await self._create_thumbnail(img, thumbnail_path)

                # 生成压缩图 (最大宽度1200，质量85%)
                compressed_path = self._get_image_path(product_id, image_hash, "compressed", "jpg")
                await self._create_compressed(img, compressed_path)

        except Exception as e:
            logger.error(f"图片处理失败: {original_path}, 错误: {e}")

    async def _create_thumbnail(self, img: Image.Image, output_path: Path):
        """创建缩略图"""
        try:
            # 创建缩略图，保持宽高比
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)

            # 创建200x200的正方形缩略图（居中裁剪）
            thumbnail = Image.new('RGB', (200, 200), (255, 255, 255))
            offset = ((200 - img.width) // 2, (200 - img.height) // 2)
            thumbnail.paste(img, offset)

            thumbnail.save(output_path, 'JPEG', quality=90, optimize=True)
            logger.debug(f"缩略图创建成功: {output_path}")

        except Exception as e:
            logger.error(f"创建缩略图失败: {e}")

    async def _create_compressed(self, img: Image.Image, output_path: Path):
        """创建压缩图"""
        try:
            # 如果图片太大，先缩放到合适尺寸
            max_width = 1200
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # 保存压缩图
            img.save(output_path, 'JPEG', quality=85, optimize=True, progressive=True)
            logger.debug(f"压缩图创建成功: {output_path}")

        except Exception as e:
            logger.error(f"创建压缩图失败: {e}")

    async def _get_image_info(self, image_path: Path) -> dict:
        """获取图片信息"""
        try:
            with Image.open(image_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "size": image_path.stat().st_size,
                    "size_mb": round(image_path.stat().st_size / (1024 * 1024), 2),
                    "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0,
                }
        except Exception as e:
            logger.error(f"获取图片信息失败: {image_path}, 错误: {e}")
            return {"error": str(e)}

    def get_image_url(self, local_path: str, image_type: str = "original") -> str:
        """获取图片访问URL"""
        if self.cdn_enabled and self.cdn_base_url:
            # CDN URL
            relative_path = str(Path(local_path).relative_to(self.base_path))
            return f"{self.cdn_base_url.rstrip('/')}/{relative_path}"
        else:
            # 本地URL
            return f"file://{local_path}"

    def get_thumbnail_url(self, local_path: str) -> str:
        """获取缩略图URL"""
        path = Path(local_path)
        thumbnail_path = (
            self.base_path / "thumbnail" /
            path.parent.name / f"{path.stem}.jpg"
        )
        return self.get_image_url(str(thumbnail_path), "thumbnail")

    def get_compressed_url(self, local_path: str) -> str:
        """获取压缩图URL"""
        path = Path(local_path)
        compressed_path = (
            self.base_path / "compressed" /
            path.parent.name / f"{path.stem}.jpg"
        )
        return self.get_image_url(str(compressed_path), "compressed")

    async def delete_image(self, local_path: str) -> bool:
        """删除图片及其衍生文件"""
        try:
            path = Path(local_path)
            if not path.exists():
                logger.warning(f"图片文件不存在: {local_path}")
                return True

            # 删除原图
            path.unlink()

            # 删除缩略图和压缩图
            product_id = path.parent.name
            image_hash = path.stem

            thumbnail_path = self._get_image_path(product_id, image_hash, "thumbnail", "jpg")
            compressed_path = self._get_image_path(product_id, image_hash, "compressed", "jpg")

            for file_path in [thumbnail_path, compressed_path]:
                if file_path.exists():
                    file_path.unlink()

            # 如果目录为空，删除目录
            for parent_dir in [path.parent, thumbnail_path.parent, compressed_path.parent]:
                if parent_dir.exists() and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()

            logger.info(f"图片删除成功: {local_path}")
            return True

        except Exception as e:
            logger.error(f"删除图片失败: {local_path}, 错误: {e}")
            return False

    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """清理临时文件"""
        try:
            temp_dir = self.base_path / "temp"
            current_time = os.path.getmtime(temp_dir)

            for file_path in temp_dir.iterdir():
                if file_path.is_file():
                    file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
                    if file_age_hours > max_age_hours:
                        file_path.unlink()
                        logger.debug(f"删除临时文件: {file_path}")

        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

    async def get_storage_stats(self) -> dict:
        """获取存储统计信息"""
        try:
            stats = {}
            total_size = 0

            for subdir in ["original", "thumbnail", "compressed"]:
                subdir_path = self.base_path / subdir
                size = 0
                count = 0

                if subdir_path.exists():
                    for file_path in subdir_path.rglob("*"):
                        if file_path.is_file():
                            size += file_path.stat().st_size
                            count += 1

                stats[subdir] = {
                    "count": count,
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                }
                total_size += size

            stats["total"] = {
                "size_bytes": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2)
            }

            return stats

        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {"error": str(e)}


# 全局图片存储实例
image_storage = ImageStorage()