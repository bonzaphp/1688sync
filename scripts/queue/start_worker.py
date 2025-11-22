#!/usr/bin/env python3
# Start Worker
# 启动Celery Worker脚本

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.queue.celery_app import celery_app


def start_worker():
    """启动Celery Worker"""
    # 设置环境变量
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

    # 启动worker
    celery_app.start()


if __name__ == '__main__':
    start_worker()