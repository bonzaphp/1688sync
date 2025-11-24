#!/usr/bin/env python3
"""
简化数据库初始化脚本
避免复杂的异步依赖问题
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def init_database():
    """初始化数据库的简化版本"""
    try:
        # 使用SQLAlchemy的同步引擎
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        # 读取数据库URL，转换为同步版本
        database_url = os.getenv('DATABASE_URL', 'sqlite:///data/1688sync.db')

        # 转换异步URL为同步URL
        if 'sqlite+aiosqlite:' in database_url:
            database_url = database_url.replace('sqlite+aiosqlite:', 'sqlite:')
        elif 'postgresql+asyncpg:' in database_url:
            database_url = database_url.replace('postgresql+asyncpg:', 'postgresql+psycopg2:')

        print(f"使用数据库URL: {database_url}")

        # 创建同步引擎
        engine = create_engine(database_url)

        # 测试连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("数据库连接测试成功")

        # 导入模型并创建表
        from src.models.base import Base

        # 导入所有模型以确保它们被注册
        from src.models import product, supplier, image, sync_record

        # 创建所有表
        Base.metadata.create_all(engine)
        print("数据库表创建成功！")

        return True

    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return False

if __name__ == "__main__":
    print("开始初始化1688sync数据库...")

    # 创建数据目录
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("images", exist_ok=True)

    # 初始化数据库
    if init_database():
        print("✅ 数据库初始化完成！")
        sys.exit(0)
    else:
        print("❌ 数据库初始化失败！")
        sys.exit(1)