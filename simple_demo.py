#!/usr/bin/env python3
"""
1688sync简单演示脚本
不依赖Redis的基础功能演示
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def simple_demo():
    """简单演示核心功能"""
    try:
        print("🚀 1688sync简单演示")
        print("=" * 50)

        # 检查数据库是否已初始化
        if not os.path.exists("data/1688sync.db"):
            print("❌ 数据库未初始化，请先运行: python init_db.py")
            return False

        print("✅ 数据库已初始化")

        # 演示数据库操作
        print("\n📊 演示数据库操作...")

        from sqlalchemy import create_engine, text
        from src.models.base import Base
        from src.models import product, supplier, image, sync_record

        # 使用同步引擎
        database_url = os.getenv('DATABASE_URL', 'sqlite:///data/1688sync.db')
        if 'sqlite+aiosqlite:' in database_url:
            database_url = database_url.replace('sqlite+aiosqlite:', 'sqlite:')

        engine = create_engine(database_url)

        # 检查表是否存在
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            print(f"✅ 数据库表: {', '.join(tables)}")

        # 演示数据模型验证
        print("\n💾 演示数据模型验证...")
        from src.models.product import Product
        from src.models.supplier import Supplier
        from src.models.image import ProductImage

        print("✅ Product模型加载成功")
        print("✅ Supplier模型加载成功")
        print("✅ ProductImage模型加载成功")

        # 查询数据
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
            print(f"📈 数据库中现有产品数量: {count}")

        # 演示配置加载
        print("\n⚙️ 演示配置系统...")
        from config.settings import get_settings
        settings = get_settings()
        print(f"✅ 应用名称: {settings.app_name}")
        print(f"✅ 调试模式: {settings.debug}")
        print(f"✅ 存储路径: {settings.storage_path}")

        # 演示日志系统
        print("\n📝 演示日志系统...")
        import logging
        logger = logging.getLogger("1688sync")
        logger.info("这是一条测试日志")
        print("✅ 日志系统正常工作")

        print("\n" + "=" * 50)
        print("🎉 简单演示完成！")
        print("\n💡 下一步:")
        print("1. 启动Redis服务: docker run -d -p 6379:6379 redis:alpine")
        print("2. 启动Worker: python scripts/queue/start_worker.py")
        print("3. 运行爬虫: python cli.py crawl products 123 --max-products 10")
        print("4. 查看帮助: python demo_crawl.py --help")

        return True

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simple_demo()
    if not success:
        sys.exit(1)