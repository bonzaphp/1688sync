"""
Scrapy数据处理管道
"""
import re
import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import scrapy
from scrapy.exceptions import DropItem
from scrapy.http import Request, Response

from ..config import settings
from ...database.models import Product, ProductImage, SyncLog
from ...database.connection import SessionLocal


class DataValidationPipeline:
    """数据验证管道"""

    def process_item(self, item: scrapy.Item, spider: scrapy.Spider) -> scrapy.Item:
        """验证数据项"""
        try:
            # 验证必填字段
            if not item.get('title'):
                raise DropItem("缺少商品标题")

            if not item.get('price') and item.get('price') != 0:
                raise DropItem("缺少商品价格")

            # 验证价格格式
            price = item.get('price')
            if price is not None:
                try:
                    item['price'] = float(price)
                except (ValueError, TypeError):
                    raise DropItem(f"无效的价格格式: {price}")

            # 验证原价格式
            original_price = item.get('original_price')
            if original_price is not None:
                try:
                    item['original_price'] = float(original_price)
                except (ValueError, TypeError):
                    item['original_price'] = None

            # 添加爬取时间
            item['crawl_time'] = datetime.utcnow()

            return item

        except Exception as e:
            spider.logger.error(f"数据验证失败: {item}, 错误: {e}")
            raise DropItem(f"数据验证失败: {e}")


class DatabasePipeline:
    """数据库存储管道"""

    def __init__(self):
        self.db = None

    def open_spider(self, spider: scrapy.Spider):
        """爬虫启动时创建数据库连接"""
        self.db = SessionLocal()

    def close_spider(self, spider: scrapy.Spider):
        """爬虫关闭时关闭数据库连接"""
        if self.db:
            self.db.close()

    def process_item(self, item: scrapy.Item, spider: scrapy.Spider) -> scrapy.Item:
        """存储商品数据"""
        try:
            # 检查商品是否已存在
            product_id = item.get('product_id')
            if product_id:
                existing = self.db.query(Product).filter(
                    Product.product_id == product_id
                ).first()

                if existing:
                    # 更新现有商品
                    self._update_product(existing, item)
                else:
                    # 创建新商品
                    self._create_product(item)

            spider.logger.debug(f"商品已保存: {item.get('product_id', 'Unknown')}")

            return item

        except Exception as e:
            spider.logger.error(f"数据库保存失败: {item}, 错误: {e}")

            # 记录错误日志
            self._log_error(item, spider, str(e))
            raise DropItem(f"数据库保存失败: {e}")

    def _create_product(self, item: scrapy.Item):
        """创建新商品"""
        product = Product(
            product_id=item.get('product_id'),
            title=item.get('title'),
            price=item.get('price'),
            original_price=item.get('original_price'),
            description=item.get('description'),
            category=item.get('category'),
            brand=item.get('brand'),
            seller=item.get('seller'),
            location=item.get('location'),
            image_urls=item.get('image_urls', []),
            specifications=item.get('specifications', {}),
            tags=item.get('tags', []),
            source_url=item.get('source_url'),
            status='active',
            sync_status='completed',
            last_sync_at=datetime.utcnow()
        )

        self.db.add(product)
        self.db.commit()

    def _update_product(self, product: Product, item: scrapy.Item):
        """更新现有商品"""
        if item.get('title'):
            product.title = item['title']
        if item.get('price') is not None:
            product.price = item['price']
        if item.get('original_price') is not None:
            product.original_price = item['original_price']
        if item.get('description'):
            product.description = item['description']
        if item.get('category'):
            product.category = item['category']
        if item.get('brand'):
            product.brand = item['brand']
        if item.get('seller'):
            product.seller = item['seller']
        if item.get('location'):
            product.location = item['location']
        if item.get('image_urls'):
            product.image_urls = item['image_urls']
        if item.get('specifications'):
            product.specifications = item['specifications']
        if item.get('tags'):
            product.tags = item['tags']

        product.updated_at = datetime.utcnow()
        product.last_sync_at = datetime.utcnow()

        self.db.commit()

    def _log_error(self, item: scrapy.Item, spider: scrapy.Spider, error_msg: str):
        """记录错误日志"""
        try:
            log = SyncLog(
                product_id=None,  # 此时可能还没有product_id
                task_id=f"{spider.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                level="ERROR",
                message=f"数据库保存失败: {error_msg}",
                details={
                    'item': dict(item),
                    'spider': spider.name,
                },
                success=False,
                error_type="DatabaseError"
            )

            self.db.add(log)
            self.db.commit()

        except Exception as e:
            spider.logger.error(f"记录错误日志失败: {e}")


class ImageDownloadPipeline:
    """图片下载管道"""

    def __init__(self, store_uri: str, expires_days: int = 90):
        self.store_uri = store_uri
        self.expires_days = expires_days
        self.min_width = 100
        self.min_height = 100
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    @classmethod
    def from_crawler(cls, crawler):
        store_uri = crawler.settings.get('IMAGES_STORE', './data/images')
        expires_days = crawler.settings.getint('IMAGES_EXPIRES', 90)
        return cls(store_uri, expires_days)

    def get_media_requests(self, item: Any, info: Dict[str, Any]) -> List[Request]:
        """获取图片下载请求"""
        image_urls = item.get('image_urls', [])
        if not image_urls:
            return []

        requests = []
        product_id = item.get('product_id', 'unknown')

        for i, url in enumerate(image_urls):
            # 确保URL是完整的
            if not url.startswith('http'):
                continue

            # 过滤无效图片
            if self._is_valid_image_url(url):
                request = Request(
                    url=url,
                    meta={
                        'product_id': product_id,
                        'image_type': 'main' if i == 0 else 'detail',
                        'item': item
                    }
                )
                requests.append(request)

        return requests

    def media_downloaded(self, response: Response, request: Request, info: Dict[str, Any]) -> Any:
        """处理下载完成的图片"""
        try:
            # 检查响应状态
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")

            # 检查内容类型
            content_type = response.headers.get('Content-Type', b'').decode('utf-8').lower()
            if not content_type.startswith('image/'):
                raise ValueError(f"不是图片类型: {content_type}")

            # 检查文件大小
            file_size = len(response.body)
            if file_size > self.max_file_size:
                raise ValueError(f"文件过大: {file_size} bytes")

            # 生成文件路径
            checksum = self._get_checksum(response.body)
            extension = self._get_extension(content_type)
            filename = f"{checksum}.{extension}"

            product_id = request.meta.get('product_id', 'unknown')
            image_type = request.meta.get('image_type', 'detail')

            # 创建目录结构
            subdir = f"{product_id[:2]}/{product_id}"
            file_path = f"{subdir}/{filename}"

            return {
                'url': response.url,
                'path': file_path,
                'checksum': checksum,
                'status': 'completed',
                'product_id': product_id,
                'image_type': image_type,
                'file_size': file_size,
                'content_type': content_type
            }

        except Exception as e:
            info.spider.logger.error(f"图片下载失败: {request.url}, 错误: {e}")
            return {
                'url': request.url,
                'status': 'failed',
                'error': str(e),
                'product_id': request.meta.get('product_id'),
                'image_type': request.meta.get('image_type')
            }

    def media_failed(self, failure, request, info):
        """处理下载失败的图片"""
        info.spider.logger.error(f"图片下载失败: {request.url}, {failure.value}")
        return {
            'url': request.url,
            'status': 'failed',
            'error': str(failure.value),
            'product_id': request.meta.get('product_id'),
            'image_type': request.meta.get('image_type')
        }

    def item_completed(self, results: List[Any], item: Any, info: Dict[str, Any]) -> Any:
        """处理下载完成"""
        successful_results = [r for r in results if r.get('status') == 'completed']
        failed_results = [r for r in results if r.get('status') == 'failed']

        # 更新商品项
        if successful_results:
            item['image_download_status'] = 'completed'
            item['downloaded_images'] = successful_results
            item['image_count'] = len(successful_results)
        else:
            item['image_download_status'] = 'failed'

        if failed_results:
            item['failed_images'] = failed_results
            item['failed_image_count'] = len(failed_results)

        # 记录统计信息
        total = len(results)
        success = len(successful_results)
        failed = len(failed_results)

        info.spider.logger.info(
            f"图片下载完成: {item.get('product_id', 'unknown')} - "
            f"总计: {total}, 成功: {success}, 失败: {failed}"
        )

        return item

    def _is_valid_image_url(self, url: str) -> bool:
        """检查是否为有效的图片URL"""
        # 检查URL格式
        if not url.startswith(('http://', 'https://')):
            return False

        # 检查文件扩展名
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        parsed_url = url.lower()

        for ext in image_extensions:
            if ext in parsed_url:
                return True

        # 检查URL参数中是否包含图片标识
        if any(keyword in parsed_url for keyword in ['image', 'img', 'photo', 'pic']):
            return True

        return False

    def _get_checksum(self, data: bytes) -> str:
        """计算文件校验和"""
        import hashlib
        return hashlib.sha1(data).hexdigest()

    def _get_extension(self, content_type: str) -> str:
        """根据内容类型获取文件扩展名"""
        type_mapping = {
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp'
        }
        return type_mapping.get(content_type, 'jpg')


class DataCleaningPipeline:
    """数据清理管道"""

    def process_item(self, item: scrapy.Item, spider: scrapy.Spider) -> scrapy.Item:
        """清理和标准化数据"""
        # 清理标题
        title = item.get('title', '')
        if title:
            title = self._clean_text(title)
            title = self._remove_excessive_whitespace(title)
            item['title'] = title

        # 清理描述
        description = item.get('description', '')
        if description:
            description = self._clean_text(description)
            description = self._truncate_text(description, 2000)  # 限制描述长度
            item['description'] = description

        # 清理品牌
        brand = item.get('brand', '')
        if brand:
            brand = self._clean_text(brand)
            item['brand'] = brand

        # 清理卖家信息
        seller = item.get('seller', '')
        if seller:
            seller = self._clean_text(seller)
            item['seller'] = seller

        # 清理地理位置
        location = item.get('location', '')
        if location:
            location = self._clean_text(location)
            item['location'] = location

        # 清理分类
        category = item.get('category', '')
        if category:
            category = self._clean_text(category)
            item['category'] = category

        # 清理标签
        tags = item.get('tags', [])
        if tags:
            cleaned_tags = []
            for tag in tags:
                cleaned_tag = self._clean_text(tag)
                if cleaned_tag and len(cleaned_tag) <= 50:
                    cleaned_tags.append(cleaned_tag)
            item['tags'] = list(set(cleaned_tags))  # 去重

        # 清理规格
        specifications = item.get('specifications', {})
        if specifications:
            cleaned_specs = {}
            for key, value in specifications.items():
                clean_key = self._clean_text(str(key))
                clean_value = self._clean_text(str(value))
                if clean_key and clean_value:
                    cleaned_specs[clean_key] = clean_value
            item['specifications'] = cleaned_specs

        return item

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""

        # 移除特殊字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)

        # 移除首尾空白
        text = text.strip()

        return text

    def _remove_excessive_whitespace(self, text: str) -> str:
        """移除过度的空白字符"""
        return re.sub(r'\s{2,}', ' ', text)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rstrip() + '...'


class DuplicateFilterPipeline:
    """重复商品过滤管道"""

    def __init__(self):
        self.seen_products = set()
        self.seen_urls = set()

    def process_item(self, item: scrapy.Item, spider: scrapy.Spider) -> scrapy.Item:
        """过滤重复商品"""
        # 检查URL重复
        source_url = item.get('source_url')
        if source_url and source_url in self.seen_urls:
            spider.logger.debug(f"跳过重复URL: {source_url}")
            raise DropItem("重复URL")

        # 检查商品ID重复
        product_id = item.get('product_id')
        if product_id:
            unique_key = str(product_id)
        else:
            # 如果没有商品ID，使用标题和价格组合
            title = item.get('title', '')
            price = item.get('price', 0)
            unique_key = f"{title}_{price}"

        unique_hash = hashlib.md5(unique_key.encode()).hexdigest()

        if unique_hash in self.seen_products:
            spider.logger.debug(f"跳过重复商品: {product_id or title}")
            raise DropItem("重复商品")

        # 记录已处理的商品
        self.seen_products.add(unique_hash)
        if source_url:
            self.seen_urls.add(source_url)

        return item


class StatsPipeline:
    """统计信息管道"""

    def __init__(self):
        self.stats = {
            'total_items': 0,
            'successful_items': 0,
            'failed_items': 0,
            'duplicate_items': 0,
            'validation_errors': 0,
            'database_errors': 0,
            'image_downloads': 0,
            'image_failures': 0
        }

    def open_spider(self, spider: scrapy.Spider):
        """爬虫启动时初始化统计"""
        self.spider = spider
        self.start_time = time.time()

    def close_spider(self, spider: scrapy.Spider):
        """爬虫关闭时输出统计信息"""
        end_time = time.time()
        duration = end_time - self.start_time

        spider.logger.info("=" * 50)
        spider.logger.info("爬虫统计信息")
        spider.logger.info("=" * 50)
        spider.logger.info(f"运行时间: {duration:.2f} 秒")
        spider.logger.info(f"总商品数: {self.stats['total_items']}")
        spider.logger.info(f"成功商品: {self.stats['successful_items']}")
        spider.logger.info(f"失败商品: {self.stats['failed_items']}")
        spider.logger.info(f"重复商品: {self.stats['duplicate_items']}")
        spider.logger.info(f"验证错误: {self.stats['validation_errors']}")
        spider.logger.info(f"数据库错误: {self.stats['database_errors']}")
        spider.logger.info(f"图片下载: {self.stats['image_downloads']}")
        spider.logger.info(f"图片失败: {self.stats['image_failures']}")

        if self.stats['total_items'] > 0:
            success_rate = (self.stats['successful_items'] / self.stats['total_items']) * 100
            spider.logger.info(f"成功率: {success_rate:.2f}%")

    def process_item(self, item: scrapy.Item, spider: scrapy.Spider) -> scrapy.Item:
        """处理项目并更新统计"""
        self.stats['total_items'] += 1

        # 检查是否有下载的图片
        image_count = item.get('image_count', 0)
        if image_count > 0:
            self.stats['image_downloads'] += image_count

        failed_count = item.get('failed_image_count', 0)
        if failed_count > 0:
            self.stats['image_failures'] += failed_count

        return item