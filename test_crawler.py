#!/usr/bin/env python3
"""
爬虫系统测试脚本
"""
import os
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.config import settings
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"配置模块导入失败: {e}")
    CONFIG_AVAILABLE = False

try:
    from src.scrapy_project.spiders._1688_spider import Product1688Spider
    from src.scrapy_project.items import ProductItem
    from src.scrapy_project.pipelines import (
        DataValidationPipeline,
        DataCleaningPipeline,
        DuplicateFilterPipeline,
        ImageDownloadPipeline
    )
    SCRAPY_AVAILABLE = True
except ImportError as e:
    print(f"Scrapy模块导入失败: {e}")
    SCRAPY_AVAILABLE = False


def test_spider_initialization():
    """测试爬虫初始化"""
    print("测试爬虫初始化...")
    if not SCRAPY_AVAILABLE:
        print("⚠ Scrapy模块不可用，跳过测试")
        return True

    try:
        spider = Product1688Spider()
        assert spider.name == "1688_products"
        assert "1688.com" in spider.allowed_domains
        print("✓ 爬虫初始化成功")
        return True
    except Exception as e:
        print(f"✗ 爬虫初始化失败: {e}")
        return False


def test_spider_with_keyword():
    """测试关键词搜索爬虫"""
    print("测试关键词搜索爬虫...")
    try:
        spider = Product1688Spider(keyword="手机")
        assert spider.keyword == "手机"
        print("✓ 关键词爬虫初始化成功")
        return True
    except Exception as e:
        print(f"✗ 关键词爬虫初始化失败: {e}")
        return False


def test_spider_with_category():
    """测试分类爬虫"""
    print("测试分类爬虫...")
    try:
        spider = Product1688Spider(category="电子产品")
        assert spider.category == "电子产品"
        print("✓ 分类爬虫初始化成功")
        return True
    except Exception as e:
        print(f"✗ 分类爬虫初始化失败: {e}")
        return False


def test_item_creation():
    """测试商品项创建"""
    print("测试商品项创建...")
    try:
        item = ProductItem()
        item['title'] = "测试商品"
        item['price'] = 99.99
        item['product_id'] = "test_001"
        item['source_url'] = "https://example.com/product/001"

        assert item['title'] == "测试商品"
        assert item['price'] == 99.99
        assert item['product_id'] == "test_001"
        print("✓ 商品项创建成功")
        return True
    except Exception as e:
        print(f"✗ 商品项创建失败: {e}")
        return False


def test_data_validation_pipeline():
    """测试数据验证管道"""
    print("测试数据验证管道...")
    try:
        pipeline = DataValidationPipeline()

        # 创建模拟爬虫
        spider = Mock()
        spider.logger = Mock()

        # 测试有效数据
        item = ProductItem()
        item['title'] = "测试商品"
        item['price'] = 99.99

        result = pipeline.process_item(item, spider)
        assert 'crawl_time' in result
        print("✓ 有效数据验证成功")

        # 测试无效数据（缺少标题）
        invalid_item = ProductItem()
        invalid_item['price'] = 99.99

        try:
            pipeline.process_item(invalid_item, spider)
            print("✗ 无效数据验证失败（应该抛出异常）")
            return False
        except:
            print("✓ 无效数据验证成功（正确抛出异常）")

        return True
    except Exception as e:
        print(f"✗ 数据验证管道测试失败: {e}")
        return False


def test_data_cleaning_pipeline():
    """测试数据清理管道"""
    print("测试数据清理管道...")
    try:
        pipeline = DataCleaningPipeline()
        spider = Mock()

        # 测试文本清理
        item = ProductItem()
        item['title'] = "  测试商品  \n\t  "
        item['description'] = "这是一个测试描述" * 100  # 很长的描述
        item['tags'] = ["标签1", "标签2", "标签1", ""]  # 重复和空标签

        result = pipeline.process_item(item, spider)

        assert result['title'] == "测试商品"
        assert len(result['description']) <= 2003  # 2000 + "..."
        assert len(set(result['tags'])) == len(result['tags'])  # 无重复
        assert "" not in result['tags']  # 无空标签

        print("✓ 数据清理成功")
        return True
    except Exception as e:
        print(f"✗ 数据清理管道测试失败: {e}")
        return False


def test_duplicate_filter_pipeline():
    """测试重复过滤管道"""
    print("测试重复过滤管道...")
    try:
        pipeline = DuplicateFilterPipeline()
        spider = Mock()
        spider.logger = Mock()

        # 第一个商品应该通过
        item1 = ProductItem()
        item1['product_id'] = "test_001"
        item1['title'] = "测试商品1"
        item1['price'] = 99.99

        result1 = pipeline.process_item(item1, spider)
        assert result1 == item1

        # 相同商品应该被过滤
        item2 = ProductItem()
        item2['product_id'] = "test_001"
        item2['title'] = "测试商品1"
        item2['price'] = 99.99

        try:
            pipeline.process_item(item2, spider)
            print("✗ 重复过滤失败（应该抛出异常）")
            return False
        except:
            print("✓ 重复过滤成功（正确抛出异常）")

        return True
    except Exception as e:
        print(f"✗ 重复过滤管道测试失败: {e}")
        return False


def test_image_download_pipeline():
    """测试图片下载管道"""
    print("测试图片下载管道...")
    try:
        pipeline = ImageDownloadPipeline(store_uri="./test_images")
        spider = Mock()
        spider.logger = Mock()

        # 测试有效图片URL
        item = ProductItem()
        item['product_id'] = "test_001"
        item['image_urls'] = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.png",
            "invalid_url",  # 无效URL应该被过滤
            "/relative/path.jpg",  # 相对路径应该被过滤
        ]

        requests = pipeline.get_media_requests(item, {})
        assert len(requests) == 2  # 只有两个有效URL
        print("✓ 图片URL过滤成功")
        return True
    except Exception as e:
        print(f"✗ 图片下载管道测试失败: {e}")
        return False


def test_configuration():
    """测试配置"""
    print("测试配置...")
    try:
        assert settings.name == "1688sync"
        assert settings.base_url == "https://www.1688.com"
        assert settings.scrapy_download_delay >= 0
        assert settings.scrapy_concurrent_requests > 0
        print("✓ 配置验证成功")
        return True
    except Exception as e:
        print(f"✗ 配置验证失败: {e}")
        return False


def test_directory_structure():
    """测试目录结构"""
    print("测试目录结构...")
    try:
        required_dirs = [
            "src/scrapy_project",
            "src/scrapy_project/spiders",
            "src/database",
            "src/config.py"
        ]

        for path in required_dirs:
            full_path = project_root / path
            if path.endswith('.py'):
                assert full_path.is_file(), f"缺少文件: {path}"
            else:
                assert full_path.is_dir(), f"缺少目录: {path}"

        print("✓ 目录结构验证成功")
        return True
    except Exception as e:
        print(f"✗ 目录结构验证失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行1688sync爬虫系统测试")
    print("=" * 60)

    tests = [
        test_configuration,
        test_directory_structure,
        test_spider_initialization,
        test_spider_with_keyword,
        test_spider_with_category,
        test_item_creation,
        test_data_validation_pipeline,
        test_data_cleaning_pipeline,
        test_duplicate_filter_pipeline,
        test_image_download_pipeline,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ 测试异常: {test.__name__} - {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"测试完成 - 通过: {passed}, 失败: {failed}")
    print("=" * 60)

    if failed == 0:
        print("🎉 所有测试通过！爬虫系统准备就绪。")
        return True
    else:
        print("❌ 部分测试失败，请检查问题。")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)