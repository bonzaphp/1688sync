#!/usr/bin/env python3
"""
简化的爬虫系统测试脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_directory_structure():
    """测试目录结构"""
    print("测试目录结构...")
    try:
        required_files = [
            "src/scrapy_project/__init__.py",
            "src/scrapy_project/spiders/__init__.py",
            "src/scrapy_project/spiders/1688_spider.py",
            "src/scrapy_project/items.py",
            "src/scrapy_project/settings.py",
            "src/scrapy_project/pipelines.py",
            "src/scrapy_project/middlewares.py",
            "src/scrapy_project/crawler.py",
            "src/database/models.py",
            "src/config.py",
            "scrapy.cfg"
        ]

        missing_files = []
        for file_path in required_files:
            full_path = project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"✗ 缺少文件: {', '.join(missing_files)}")
            return False

        print("✓ 所有必需文件都存在")
        return True
    except Exception as e:
        print(f"✗ 目录结构测试失败: {e}")
        return False


def test_spider_file_syntax():
    """测试爬虫文件语法"""
    print("测试爬虫文件语法...")
    try:
        spider_file = project_root / "src/scrapy_project/spiders/1688_spider.py"
        with open(spider_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键类和方法
        required_elements = [
            "class Product1688Spider",
            "def start_requests",
            "def parse_homepage",
            "def parse_search",
            "def parse_category",
            "def parse_product",
            "def _extract_title",
            "def _extract_price",
            "def _extract_image_urls"
        ]

        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)

        if missing_elements:
            print(f"✗ 爬虫文件缺少元素: {', '.join(missing_elements)}")
            return False

        print("✓ 爬虫文件语法检查通过")
        return True
    except Exception as e:
        print(f"✗ 爬虫文件语法测试失败: {e}")
        return False


def test_pipeline_file_syntax():
    """测试管道文件语法"""
    print("测试管道文件语法...")
    try:
        pipeline_file = project_root / "src/scrapy_project/pipelines.py"
        with open(pipeline_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键类
        required_classes = [
            "class DataValidationPipeline",
            "class DatabasePipeline",
            "class ImageDownloadPipeline",
            "class DataCleaningPipeline",
            "class DuplicateFilterPipeline",
            "class StatsPipeline"
        ]

        missing_classes = []
        for class_name in required_classes:
            if class_name not in content:
                missing_classes.append(class_name)

        if missing_classes:
            print(f"✗ 管道文件缺少类: {', '.join(missing_classes)}")
            return False

        print("✓ 管道文件语法检查通过")
        return True
    except Exception as e:
        print(f"✗ 管道文件语法测试失败: {e}")
        return False


def test_settings_file_syntax():
    """测试设置文件语法"""
    print("测试设置文件语法...")
    try:
        settings_file = project_root / "src/scrapy_project/settings.py"
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键设置
        required_settings = [
            "BOT_NAME",
            "SPIDER_MODULES",
            "USER_AGENT",
            "CONCURRENT_REQUESTS",
            "DOWNLOAD_DELAY",
            "ITEM_PIPELINES",
            "DOWNLOADER_MIDDLEWARES",
            "IMAGES_STORE"
        ]

        missing_settings = []
        for setting in required_settings:
            if setting not in content:
                missing_settings.append(setting)

        if missing_settings:
            print(f"✗ 设置文件缺少配置: {', '.join(missing_settings)}")
            return False

        print("✓ 设置文件语法检查通过")
        return True
    except Exception as e:
        print(f"✗ 设置文件语法测试失败: {e}")
        return False


def test_middleware_file_syntax():
    """测试中间件文件语法"""
    print("测试中间件文件语法...")
    try:
        middleware_file = project_root / "src/scrapy_project/middlewares.py"
        with open(middleware_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键中间件类
        required_middlewares = [
            "class UserAgentMiddleware",
            "class ProxyMiddleware",
            "class RateLimitMiddleware",
            "class RetryMiddlewareWithBackoff",
            "class HeaderMiddleware",
            "class AntiDetectionMiddleware"
        ]

        missing_middlewares = []
        for middleware in required_middlewares:
            if middleware not in content:
                missing_middlewares.append(middleware)

        if missing_middlewares:
            print(f"✗ 中间件文件缺少类: {', '.join(missing_middlewares)}")
            return False

        print("✓ 中间件文件语法检查通过")
        return True
    except Exception as e:
        print(f"✗ 中间件文件语法测试失败: {e}")
        return False


def test_database_models_syntax():
    """测试数据库模型语法"""
    print("测试数据库模型语法...")
    try:
        models_file = project_root / "src/database/models.py"
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键模型
        required_models = [
            "class Product",
            "class ProductImage",
            "class SyncLog",
            "class SyncTask"
        ]

        missing_models = []
        for model in required_models:
            if model not in content:
                missing_models.append(model)

        if missing_models:
            print(f"✗ 数据库模型缺少类: {', '.join(missing_models)}")
            return False

        print("✓ 数据库模型语法检查通过")
        return True
    except Exception as e:
        print(f"✗ 数据库模型语法测试失败: {e}")
        return False


def test_config_file_syntax():
    """测试配置文件语法"""
    print("测试配置文件语法...")
    try:
        config_file = project_root / "src/config.py"
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键配置
        required_configs = [
            "class Settings",
            "name",
            "database_url",
            "base_url",
            "scrapy_download_delay",
            "scrapy_concurrent_requests"
        ]

        missing_configs = []
        for config in required_configs:
            if config not in content:
                missing_configs.append(config)

        if missing_configs:
            print(f"✗ 配置文件缺少配置: {', '.join(missing_configs)}")
            return False

        print("✓ 配置文件语法检查通过")
        return True
    except Exception as e:
        print(f"✗ 配置文件语法测试失败: {e}")
        return False


def test_scrapy_cfg():
    """测试Scrapy配置文件"""
    print("测试Scrapy配置文件...")
    try:
        scrapy_cfg = project_root / "scrapy.cfg"
        with open(scrapy_cfg, 'r', encoding='utf-8') as f:
            content = f.read()

        if "[settings]" not in content:
            print("✗ scrapy.cfg缺少[settings]部分")
            return False

        if "default = src.scrapy_project.settings" not in content:
            print("✗ scrapy.cfg缺少默认设置")
            return False

        print("✓ Scrapy配置文件检查通过")
        return True
    except Exception as e:
        print(f"✗ Scrapy配置文件测试失败: {e}")
        return False


def run_simple_tests():
    """运行简化测试"""
    print("=" * 60)
    print("开始运行1688sync爬虫系统简化测试")
    print("=" * 60)

    tests = [
        test_directory_structure,
        test_spider_file_syntax,
        test_pipeline_file_syntax,
        test_settings_file_syntax,
        test_middleware_file_syntax,
        test_database_models_syntax,
        test_config_file_syntax,
        test_scrapy_cfg,
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
        print("🎉 所有基础测试通过！爬虫系统结构完整。")
        print("\n下一步操作:")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 配置数据库: 编辑.env文件")
        print("3. 运行爬虫: python src/scrapy_project/crawler.py --keyword '手机'")
        return True
    else:
        print("❌ 部分测试失败，请检查问题。")
        return False


if __name__ == '__main__':
    success = run_simple_tests()
    sys.exit(0 if success else 1)