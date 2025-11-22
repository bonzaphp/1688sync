#!/usr/bin/env python3
"""
简化的API测试 - 验证基本结构
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

print("🔍 检查1688sync API项目结构...")

# 检查主要文件
files_to_check = [
    "api/__init__.py",
    "api/main.py",
    "api/routes/__init__.py",
    "api/routes/products.py",
    "api/routes/tasks.py",
    "api/routes/logs.py",
    "api/schemas/__init__.py",
    "api/schemas/common.py",
    "api/schemas/product.py",
    "api/schemas/task.py",
    "api/schemas/log.py",
    "api/deps/__init__.py",
    "api/deps/database.py",
    "api/deps/auth.py",
    "api/services/__init__.py",
    "api/services/product_service.py",
    "api/services/task_service.py",
    "api/services/log_service.py",
    "api/exceptions/__init__.py",
    "api/exceptions/custom.py",
    "api/exceptions/handlers.py",
    "api/middleware/__init__.py",
    "api/middleware/logging.py",
    "api/middleware/security.py",
    "api/middleware/rate_limit.py",
    "api/middleware/timing.py"
]

all_exist = True
for file_path in files_to_check:
    full_path = project_root / "src" / file_path
    if full_path.exists():
        print(f"✅ {file_path}")
    else:
        print(f"❌ {file_path} - 文件不存在")
        all_exist = False

if all_exist:
    print("\n🎉 所有API文件都已创建成功！")
    print("\n📋 项目特性:")
    print("   • FastAPI异步Web框架")
    print("   • RESTful API设计")
    print("   • Pydantic数据验证")
    print("   • JWT认证和授权")
    print("   • SQLAlchemy ORM集成")
    print("   • 错误处理和日志记录")
    print("   • CORS和安全中间件")
    print("   • 频率限制保护")
    print("   • 自动API文档生成")

    print("\n🚀 使用方法:")
    print("   1. 安装依赖: pip install fastapi uvicorn sqlalchemy pymysql")
    print("   2. 配置环境: cp .env.example .env")
    print("   3. 启动服务: python run_api.py")
    print("   4. 访问文档: http://localhost:8000/docs")

    print("\n📡 API端点:")
    print("   • 商品管理: /api/v1/products/")
    print("   • 任务管理: /api/v1/tasks/")
    print("   • 日志管理: /api/v1/logs/")
    print("   • 健康检查: /health")
else:
    print("\n⚠️  部分文件缺失，请检查项目结构")