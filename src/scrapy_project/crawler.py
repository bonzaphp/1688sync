"""
爬虫运行器
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings


class CrawlerRunner:
    """爬虫运行器"""

    def __init__(self):
        self.process = None
        self.setup_environment()

    def setup_environment(self):
        """设置环境"""
        # 确保数据目录存在
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.image_dir.mkdir(parents=True, exist_ok=True)

        # 确保日志目录存在
        if settings.log_file:
            Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)

    def get_crawler_process(self) -> CrawlerProcess:
        """获取爬虫进程"""
        if self.process is None:
            # 获取Scrapy项目设置
            scrapy_settings = get_project_settings()

            # 添加自定义设置
            custom_settings = {
                'LOG_LEVEL': settings.log_level.lower(),
                'LOG_FILE': settings.log_file,
                'IMAGES_STORE': str(settings.image_dir),
                'DOWNLOAD_DELAY': settings.scrapy_download_delay,
                'RANDOMIZE_DOWNLOAD_DELAY': settings.scrapy_randomize_download_delay,
                'CONCURRENT_REQUESTS': settings.scrapy_concurrent_requests,
            }

            # 合并设置
            scrapy_settings.setdict(custom_settings)

            self.process = CrawlerProcess(settings=scrapy_settings)

        return self.process

    def run_spider(
        self,
        spider_name: str = "1688_products",
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        max_requests: int = 100,
        **kwargs
    ):
        """运行爬虫"""
        process = self.get_crawler_process()

        # 爬虫参数
        spider_args = {
            'max_requests': max_requests,
            **kwargs
        }

        if category:
            spider_args['category'] = category

        if keyword:
            spider_args['keyword'] = keyword

        print(f"启动爬虫: {spider_name}")
        print(f"参数: {spider_args}")
        print("-" * 50)

        # 运行爬虫
        process.crawl(spider_name, **spider_args)
        process.start()

    def run_category_spider(self, category: str, max_requests: int = 100):
        """运行分类爬虫"""
        self.run_spider(category=category, max_requests=max_requests)

    def run_search_spider(self, keyword: str, max_requests: int = 100):
        """运行搜索爬虫"""
        self.run_spider(keyword=keyword, max_requests=max_requests)

    def run_homepage_spider(self, max_requests: int = 100):
        """运行首页爬虫"""
        self.run_spider(max_requests=max_requests)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='1688商品爬虫')
    parser.add_argument('--category', '-c', help='商品分类')
    parser.add_argument('--keyword', '-k', help='搜索关键词')
    parser.add_argument('--max-requests', '-m', type=int, default=100, help='最大请求数')
    parser.add_argument('--log-level', '-l', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')

    args = parser.parse_args()

    # 创建运行器
    runner = CrawlerRunner()

    # 根据参数运行不同的爬虫
    if args.keyword:
        print(f"运行搜索爬虫，关键词: {args.keyword}")
        runner.run_search_spider(args.keyword, args.max_requests)
    elif args.category:
        print(f"运行分类爬虫，分类: {args.category}")
        runner.run_category_spider(args.category, args.max_requests)
    else:
        print("运行首页爬虫")
        runner.run_homepage_spider(args.max_requests)


if __name__ == '__main__':
    main()