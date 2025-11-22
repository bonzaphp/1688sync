#!/usr/bin/env python3
"""
1688sync API服务启动脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

import uvicorn
from src.config import settings


def main():
    """主函数"""
    print(f"🚀 启动 {settings.name} API 服务...")
    print(f"📍 版本: {settings.version}")
    print(f"🌐 主机: {settings.api_host}")
    print(f"🔌 端口: {settings.api_port}")
    print(f"🔧 调试模式: {settings.api_debug}")
    print(f"📊 日志级别: {settings.log_level}")

    # 启动服务
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True
    )


if __name__ == "__main__":
    main()