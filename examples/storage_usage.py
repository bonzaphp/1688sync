"""
存储系统使用示例
"""
import asyncio
import logging
from datetime import datetime

from src import (
    init_database,
    close_database,
    SupplierRepository,
    ProductRepository,
    ImageRepository,
    SyncRepository,
    DataConsistencyManager,
    backup_restore_manager,
    db_manager
)
from src.database import db_transaction
from src.models import Supplier, Product, ProductImage

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def storage_system_demo():
    """存储系统演示"""
    try:
        # 1. 初始化数据库
        logger.info("初始化数据库连接...")
        await init_database()
        logger.info("数据库连接初始化完成")

        # 2. 健康检查
        logger.info("执行数据库健康检查...")
        health = await db_manager.health_check()
        logger.info(f"数据库健康状态: {health}")

        # 3. 创建供应商示例
        logger.info("创建供应商示例...")
        async with db_manager.get_session() as session:
            supplier_repo = SupplierRepository(session)

            # 创建供应商
            supplier = await supplier_repo.create_or_update_supplier(
                source_id="supplier_001",
                name="示例供应商有限公司",
                company_name="示例供应商有限公司",
                location="浙江省杭州市",
                province="浙江省",
                city="杭州市",
                rating=4.5,
                response_rate=98.5,
                business_type="manufacturer",
                is_verified="Y",
                verification_level="gold"
            )

            logger.info(f"创建供应商成功: {supplier.name} (ID: {supplier.id})")

        # 4. 创建商品示例
        logger.info("创建商品示例...")
        async with db_manager.get_session() as session:
            product_repo = ProductRepository(session)

            # 创建商品
            product = await product_repo.create_or_update_product(
                source_id="product_001",
                title="高质量手机壳批发",
                subtitle="多种颜色可选，支持定制",
                price_min=5.50,
                price_max=15.80,
                currency="CNY",
                moq=100,
                price_unit="piece",
                main_image_url="https://example.com/image1.jpg",
                supplier_id=supplier.id,
                category_id="electronics",
                category_name="手机配件",
                status="active",
                sync_status="pending"
            )

            logger.info(f"创建商品成功: {product.title} (ID: {product.id})")

        # 5. 创建图片记录示例
        logger.info("创建图片记录示例...")
        async with db_manager.get_session() as session:
            image_repo = ImageRepository(session)

            # 创建主图
            main_image = await image_repo.create_product_image(
                product_id=product.id,
                url="https://example.com/image1.jpg",
                image_type="main",
                sort_order=0
            )

            # 创建详情图
            detail_image = await image_repo.create_product_image(
                product_id=product.id,
                url="https://example.com/image2.jpg",
                image_type="detail",
                sort_order=1
            )

            logger.info(f"创建图片记录成功: 主图 {main_image.id}, 详情图 {detail_image.id}")

        # 6. 创建同步记录示例
        logger.info("创建同步记录示例...")
        async with db_manager.get_session() as session:
            sync_repo = SyncRepository(session)

            sync_record = await sync_repo.create_sync_record(
                task_id=f"sync_task_{int(datetime.now().timestamp())}",
                operation_type="incremental",
                sync_type="product",
                task_name="示例商品同步任务",
                total_count=1,
                config={"batch_size": 100, "max_retries": 3}
            )

            logger.info(f"创建同步记录成功: {sync_record.task_id}")

        # 7. 数据一致性检查
        logger.info("执行数据一致性检查...")
        async with db_manager.get_session() as session:
            consistency_manager = DataConsistencyManager(session)

            consistency_report = await consistency_manager.validate_data_integrity()
            logger.info(f"数据一致性检查结果: {consistency_report['total_issues']} 个问题")

        # 8. 获取统计信息
        logger.info("获取统计信息...")
        async with db_manager.get_session() as session:
            supplier_repo = SupplierRepository(session)
            product_repo = ProductRepository(session)

            supplier_stats = await supplier_repo.get_supplier_statistics()
            product_stats = await product_repo.get_product_statistics()

            logger.info(f"供应商统计: {supplier_stats['total_count']} 个供应商")
            logger.info(f"商品统计: {product_stats['total_count']} 个商品")

        # 9. 备份示例（仅演示，不实际执行）
        logger.info("演示备份功能...")
        logger.info("创建完整备份（演示模式）...")
        # backup_result = backup_restore_manager.create_full_backup("demo_backup")
        # logger.info(f"备份结果: {backup_result}")

        logger.info("存储系统演示完成！")

    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise

    finally:
        # 关闭数据库连接
        await close_database()
        logger.info("数据库连接已关闭")


async def demonstrate_advanced_features():
    """演示高级功能"""
    try:
        await init_database()

        logger.info("=== 高级功能演示 ===")

        # 1. 批量操作
        logger.info("演示批量操作...")
        async with db_manager.get_session() as session:
            product_repo = ProductRepository(session)

            # 批量导入商品数据
            products_data = [
                {
                    "source_id": f"batch_product_{i}",
                    "title": f"批量商品 {i}",
                    "price_min": 10.0 + i,
                    "supplier_id": 1,  # 假设存在
                    "status": "active"
                }
                for i in range(1, 6)
            ]

            # imported_products = await product_repo.bulk_import_products(products_data)
            logger.info(f"批量导入商品完成")

        # 2. 复杂查询
        logger.info("演示复杂查询...")
        async with db_manager.get_session() as session:
            product_repo = ProductRepository(session)

            # 搜索商品
            search_results = await product_repo.search_products(
                keyword="批量",
                min_price=10.0,
                max_price=15.0,
                min_rating=4.0,
                limit=10
            )
            logger.info(f"搜索到 {len(search_results)} 个商品")

        # 3. 事务处理
        logger.info("演示事务处理...")
        async with db_transaction() as session:
            supplier_repo = SupplierRepository(session)
            product_repo = ProductRepository(session)

            # 创建供应商和商品（在同一个事务中）
            new_supplier = await supplier_repo.create(
                source_id="tx_supplier_001",
                name="事务供应商",
                rating=4.0
            )

            new_product = await product_repo.create(
                source_id="tx_product_001",
                title="事务商品",
                price_min=20.0,
                supplier_id=new_supplier.id
            )

            logger.info(f"事务中创建: 供应商 {new_supplier.id}, 商品 {new_product.id}")

        logger.info("高级功能演示完成！")

    except Exception as e:
        logger.error(f"高级功能演示失败: {e}")
    finally:
        await close_database()


if __name__ == "__main__":
    print("1688sync 存储系统演示")
    print("=" * 50)

    # 基础演示
    print("\n1. 基础功能演示")
    asyncio.run(storage_system_demo())

    # 高级功能演示
    print("\n2. 高级功能演示")
    asyncio.run(demonstrate_advanced_features())

    print("\n演示完成！")