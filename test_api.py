#!/usr/bin/env python3
"""
简单的API测试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from fastapi import FastAPI
    from api.main import app
    print("✅ API应用创建成功")
    print(f"📱 应用标题: {app.title}")
    print(f"🔧 版本: {app.version}")
    print(f"📖 文档地址: http://localhost:8000/docs")
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("💡 请确保安装了FastAPI: pip install fastapi uvicorn")
except Exception as e:
    print(f"❌ 其他错误: {e}")