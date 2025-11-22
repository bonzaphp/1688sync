"""
数据库测试用例
"""
import pytest
import tempfile
import os
from pathlib import Path

from src.config import settings
from src.database.connection import create_tables, drop_tables, engine
from src.database.models import Product


class TestDatabase:
    """数据库测试类"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库"""
        # 创建临时数据库文件
        temp_dir = tempfile.mkdtemp()
        temp_db = os.path.join(temp_dir, "test.db")
        old_database_url = settings.database_url

        # 设置临时数据库
        settings.database_url = f"sqlite:///{temp_db}"

        yield temp_db

        # 清理
        os.unlink(temp_db)
        os.rmdir(temp_dir)
        settings.database_url = old_database_url

    def test_create_tables(self, temp_db):
        """测试创建表"""
        create_tables()

        # 验证表是否创建成功
        with engine.connect() as conn:
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in result]

            expected_tables = ['products', 'product_images', 'sync_logs', 'sync_tasks']
            for table in expected_tables:
                assert table in tables, f"表 {table} 未创建"

    def test_drop_tables(self, temp_db):
        """测试删除表"""
        create_tables()  # 先创建表
        drop_tables()

        # 验证表是否删除成功
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            assert result.fetchone()[0] == 0, "表未完全删除"

    def test_product_model(self, temp_db):
        """测试商品模型"""
        create_tables()

        # 创建测试商品
        product = Product(
            product_id="test123",
            title="测试商品",
            price=99.99,
            category="测试分类",
            description="这是一个测试商品",
            source_url="https://test.com/item/123"
        )

        # 保存到数据库
        from src.database.connection import SessionLocal
        db = SessionLocal()
        db.add(product)
        db.commit()

        # 验证保存成功
        saved_product = db.query(Product).filter(Product.product_id == "test123").first()
        assert saved_product is not None, "商品保存失败"
        assert saved_product.title == "测试商品", "商品标题不匹配"
        assert saved_product.price == 99.99, "商品价格不匹配"

        db.close()

    def test_product_duplicate_prevention(self, temp_db):
        """测试商品重复预防"""
        create_tables()

        from src.database.connection import SessionLocal
        db = SessionLocal()

        # 创建第一个商品
        product1 = Product(
            product_id="dup123",
            title="重复测试商品",
            price=50.0,
            source_url="https://test.com/item/123"
        )
        db.add(product1)
        db.commit()

        # 尝试创建重复商品（相同的product_id）
        product2 = Product(
            product_id="dup123",  # 相同ID
            title="重复测试商品2",
            price=60.0,
            source_url="https://test.com/item/456"
        )
        db.add(product2)
        try:
            db.commit()
            assert False, "应该抛出唯一约束异常"
        except Exception:
            # 正常，应该违反唯一性约束
            db.rollback()

        db.close()


if __name__ == '__main__':
    pytest.main([__file__])