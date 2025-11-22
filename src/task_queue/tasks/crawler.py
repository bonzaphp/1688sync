# Crawler Tasks
# 爬虫相关任务

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseTask, TaskResult, register_task
from ...services.product_repository import ProductRepository
from ...services.supplier_repository import SupplierRepository

logger = logging.getLogger(__name__)


@register_task('src.queue.tasks.crawler.fetch_products')
class FetchProductsTask(BaseTask):
    """获取产品任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        required_fields = ['category_id', 'page_size']
        for field in required_fields:
            if field not in kwargs:
                raise ValueError(f"缺少必需参数: {field}")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行产品获取任务"""
        try:
            category_id = kwargs.get('category_id')
            page_size = kwargs.get('page_size', 50)
            page_num = kwargs.get('page_num', 1)
            filters = kwargs.get('filters', {})

            total_products = kwargs.get('total_products', 0)
            max_products = kwargs.get('max_products', 1000)

            # 更新进度
            self.update_progress(0, max_products, "开始获取产品")

            product_repo = ProductRepository()
            fetched_products = []
            current_count = 0

            # 模拟爬虫逻辑
            while current_count < max_products:
                # 获取当前页的产品
                products = self._fetch_products_page(
                    category_id, page_num, page_size, filters
                )

                if not products:
                    break

                # 保存产品到数据库
                saved_products = product_repo.batch_create(products)
                fetched_products.extend(saved_products)

                current_count += len(products)
                page_num += 1

                # 更新进度
                self.update_progress(
                    min(current_count, max_products),
                    max_products,
                    f"已获取 {current_count} 个产品"
                )

                # 检查是否达到最大数量
                if len(fetched_products) >= max_products:
                    break

            result_data = {
                'fetched_count': len(fetched_products),
                'products': [{'id': p.id, 'title': p.title} for p in fetched_products],
                'category_id': category_id,
                'page_num': page_num - 1
            }

            return TaskResult(
                success=True,
                data=result_data,
                metadata={'execution_time': datetime.utcnow().isoformat()}
            )

        except Exception as e:
            logger.error(f"获取产品任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _fetch_products_page(
        self, category_id: str, page_num: int, page_size: int, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """获取单页产品（模拟）"""
        # 这里应该是实际的爬虫逻辑
        # 现在返回模拟数据
        import random

        products = []
        for i in range(min(page_size, 20)):  # 模拟最多20个产品
            product = {
                'title': f'产品 {page_num}-{i+1}',
                'price': random.uniform(10, 1000),
                'category_id': category_id,
                'description': f'产品描述 {page_num}-{i+1}',
                'source_url': f'https://example.com/product/{page_num}-{i+1}',
                'images': [
                    f'https://example.com/image/{page_num}-{i+1}-1.jpg',
                    f'https://example.com/image/{page_num}-{i+1}-2.jpg'
                ]
            }
            products.append(product)

        return products


@register_task('src.queue.tasks.crawler.fetch_product_details')
class FetchProductDetailsTask(BaseTask):
    """获取产品详情任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'product_ids' not in kwargs:
            raise ValueError("缺少必需参数: product_ids")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行产品详情获取任务"""
        try:
            product_ids = kwargs.get('product_ids', [])
            batch_size = kwargs.get('batch_size', 10)

            total_count = len(product_ids)
            processed_count = 0

            self.update_progress(0, total_count, "开始获取产品详情")

            product_repo = ProductRepository()
            updated_products = []

            # 分批处理
            for i in range(0, len(product_ids), batch_size):
                batch_ids = product_ids[i:i + batch_size]

                for product_id in batch_ids:
                    # 获取产品详情
                    details = self._fetch_product_details(product_id)

                    if details:
                        # 更新产品信息
                        updated = product_repo.update(product_id, details)
                        if updated:
                            updated_products.append(updated)

                    processed_count += 1
                    self.update_progress(
                        processed_count,
                        total_count,
                        f"已处理 {processed_count} 个产品详情"
                    )

            result_data = {
                'updated_count': len(updated_products),
                'products': [{'id': p.id, 'title': p.title} for p in updated_products]
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"获取产品详情任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _fetch_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """获取单个产品详情（模拟）"""
        # 这里应该是实际的详情获取逻辑
        import random

        # 模拟成功率
        if random.random() > 0.1:  # 90%成功率
            return {
                'description': f'详细的产品描述 {product_id}',
                'specifications': {
                    'weight': f'{random.uniform(0.1, 10):.2f}kg',
                    'dimensions': f'{random.randint(10, 100)}x{random.randint(10, 100)}x{random.randint(10, 100)}cm'
                },
                'additional_images': [
                    f'https://example.com/detail/{product_id}-1.jpg',
                    f'https://example.com/detail/{product_id}-2.jpg'
                ]
            }

        return None


@register_task('src.queue.tasks.crawler.fetch_suppliers')
class FetchSuppliersTask(BaseTask):
    """获取供应商任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'product_ids' not in kwargs:
            raise ValueError("缺少必需参数: product_ids")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行供应商获取任务"""
        try:
            product_ids = kwargs.get('product_ids', [])
            max_suppliers_per_product = kwargs.get('max_suppliers', 5)

            total_count = len(product_ids)
            processed_count = 0

            self.update_progress(0, total_count, "开始获取供应商信息")

            supplier_repo = SupplierRepository()
            fetched_suppliers = []

            for product_id in product_ids:
                # 获取产品的供应商
                suppliers = self._fetch_product_suppliers(
                    product_id, max_suppliers_per_product
                )

                # 保存供应商信息
                for supplier_data in suppliers:
                    supplier = supplier_repo.create(supplier_data)
                    if supplier:
                        fetched_suppliers.append(supplier)

                processed_count += 1
                self.update_progress(
                    processed_count,
                    total_count,
                    f"已处理 {processed_count} 个产品的供应商"
                )

            result_data = {
                'fetched_count': len(fetched_suppliers),
                'suppliers': [{'id': s.id, 'name': s.name} for s in fetched_suppliers]
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"获取供应商任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _fetch_product_suppliers(self, product_id: str, max_suppliers: int) -> List[Dict[str, Any]]:
        """获取产品的供应商（模拟）"""
        import random

        suppliers = []
        supplier_count = random.randint(1, max_suppliers)

        for i in range(supplier_count):
            supplier = {
                'name': f'供应商 {product_id}-{i+1}',
                'contact_info': {
                    'phone': f'1{random.randint(3000000000, 9999999999)}',
                    'email': f'supplier{i+1}@example.com'
                },
                'location': f'地区{random.randint(1, 30)}',
                'rating': round(random.uniform(3.0, 5.0), 1),
                'product_id': product_id
            }
            suppliers.append(supplier)

        return suppliers


@register_task('src.queue.tasks.crawler.sync_category')
class SyncCategoryTask(BaseTask):
    """同步分类任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'category_id' not in kwargs:
            raise ValueError("缺少必需参数: category_id")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行分类同步任务"""
        try:
            category_id = kwargs.get('category_id')
            sync_products = kwargs.get('sync_products', True)
            sync_suppliers = kwargs.get('sync_suppliers', True)
            max_products = kwargs.get('max_products', 1000)

            self.update_progress(0, 100, "开始同步分类")

            # 第一步：获取产品
            if sync_products:
                self.update_progress(10, 100, "获取产品信息")

                product_task = FetchProductsTask()
                product_result = product_task.run(
                    category_id=category_id,
                    max_products=max_products
                )

                if not product_result.success:
                    return TaskResult(
                        success=False,
                        error=f"获取产品失败: {product_result.error}"
                    )

                product_ids = [p['id'] for p in product_result.data.get('products', [])]
                self.update_progress(40, 100, f"已获取 {len(product_ids)} 个产品")

            # 第二步：获取产品详情
            if sync_products and product_ids:
                self.update_progress(50, 100, "获取产品详情")

                details_task = FetchProductDetailsTask()
                details_result = details_task.run(product_ids=product_ids)

                if not details_result.success:
                    logger.warning(f"获取产品详情失败: {details_result.error}")

            # 第三步：获取供应商
            if sync_suppliers and product_ids:
                self.update_progress(70, 100, "获取供应商信息")

                suppliers_task = FetchSuppliersTask()
                suppliers_result = suppliers_task.run(product_ids=product_ids)

                if not suppliers_result.success:
                    logger.warning(f"获取供应商失败: {suppliers_result.error}")

            self.update_progress(100, 100, "分类同步完成")

            result_data = {
                'category_id': category_id,
                'products_count': len(product_ids) if 'product_ids' in locals() else 0,
                'sync_products': sync_products,
                'sync_suppliers': sync_suppliers
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"同步分类任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )