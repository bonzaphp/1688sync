#!/usr/bin/env python3
"""
1688sync爬虫使用示例
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.scrapy_project.crawler import CrawlerRunner


def example_search_products():
    """示例：搜索商品"""
    print("=" * 50)
    print("示例1: 搜索手机商品")
    print("=" * 50)

    runner = CrawlerRunner()

    try:
        # 运行搜索爬虫，限制请求数量以便演示
        runner.run_search_spider(keyword="手机", max_requests=10)
        print("搜索爬虫运行完成")
    except Exception as e:
        print(f"搜索爬虫运行失败: {e}")


def example_category_products():
    """示例：按分类爬取商品"""
    print("\n" + "=" * 50)
    print("示例2: 分类爬取商品")
    print("=" * 50)

    runner = CrawlerRunner()

    try:
        # 运行分类爬虫
        runner.run_category_spider(category="电子产品", max_requests=10)
        print("分类爬虫运行完成")
    except Exception as e:
        print(f"分类爬虫运行失败: {e}")


def example_homepage_products():
    """示例：首页商品爬取"""
    print("\n" + "=" * 50)
    print("示例3: 首页商品爬取")
    print("=" * 50)

    runner = CrawlerRunner()

    try:
        # 运行首页爬虫
        runner.run_homepage_spider(max_requests=5)
        print("首页爬虫运行完成")
    except Exception as e:
        print(f"首页爬虫运行失败: {e}")


def example_custom_spider():
    """示例：自定义爬虫配置"""
    print("\n" + "=" * 50)
    print("示例4: 自定义爬虫配置")
    print("=" * 50)

    try:
        from scrapy.crawler import CrawlerProcess
        from src.scrapy_project.spiders._1688_spider import Product1688Spider

        # 创建爬虫进程
        process = CrawlerProcess({
            'LOG_LEVEL': 'INFO',
            'CONCURRENT_REQUESTS': 8,
            'DOWNLOAD_DELAY': 2.0,
            'ITEM_PIPELINES': {
                'src.scrapy_project.pipelines.DataCleaningPipeline': 200,
                'src.scrapy_project.pipelines.DataValidationPipeline': 300,
                'src.scrapy_project.pipelines.StatsPipeline': 900,
            }
        })

        # 运行爬虫
        process.crawl(
            Product1688Spider,
            keyword="笔记本电脑",
            max_requests=5
        )

        print("自定义爬虫开始运行...")
        process.start()
        print("自定义爬虫运行完成")

    except Exception as e:
        print(f"自定义爬虫运行失败: {e}")


def example_data_analysis():
    """示例：数据分析"""
    print("\n" + "=" * 50)
    print("示例5: 数据分析")
    print("=" * 50)

    try:
        from src.database.connection import SessionLocal
        from src.database.models import Product

        db = SessionLocal()

        # 查询商品总数
        total_products = db.query(Product).count()
        print(f"商品总数: {total_products}")

        if total_products > 0:
            # 查询最近10个商品
            recent_products = db.query(Product).order_by(
                Product.created_at.desc()
            ).limit(10).all()

            print("\n最近10个商品:")
            for product in recent_products:
                print(f"- {product.title[:50]}... - ¥{product.price}")

            # 按分类统计
            categories = db.query(Product.category).filter(
                Product.category.isnot(None)
            ).distinct().all()

            print(f"\n商品分类数量: {len(categories)}")

        db.close()

    except Exception as e:
        print(f"数据分析失败: {e}")


def run_examples():
    """运行所有示例"""
    print("1688sync爬虫系统使用示例")
    print("注意：这些示例用于演示功能，实际运行需要配置数据库等环境")

    examples = [
        ("搜索商品示例", example_search_products),
        ("分类爬取示例", example_category_products),
        ("首页爬取示例", example_homepage_products),
        ("自定义配置示例", example_custom_spider),
        ("数据分析示例", example_data_analysis),
    ]

    for name, func in examples:
        print(f"\n准备运行: {name}")
        try:
            func()
        except KeyboardInterrupt:
            print(f"\n用户中断了 {name}")
            break
        except Exception as e:
            print(f"{name} 运行出错: {e}")

        print(f"\n{name} 演示完成")
        time.sleep(2)  # 间隔2秒


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='1688sync爬虫使用示例')
    parser.add_argument('--example', '-e',
                       choices=['search', 'category', 'homepage', 'custom', 'analysis', 'all'],
                       default='all',
                       help='运行指定示例')

    args = parser.parse_args()

    if args.example == 'all':
        run_examples()
    elif args.example == 'search':
        example_search_products()
    elif args.example == 'category':
        example_category_products()
    elif args.example == 'homepage':
        example_homepage_products()
    elif args.example == 'custom':
        example_custom_spider()
    elif args.example == 'analysis':
        example_data_analysis()


if __name__ == '__main__':
    main()