"""
数据处理管道使用示例
"""
import json
import logging
from datetime import datetime

from src.data_processing.pipeline import DataPipeline
from src.data_processing.cleaner import DataCleaner
from src.data_processing.validator import DataValidator
from src.data_processing.deduplicator import DataDeduplicator
from src.data_processing.version_manager import VersionManager, ChangeType
from src.data_processing.quality_monitor import DataQualityMonitor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_data_cleaning():
    """数据清洗示例"""
    print("=== 数据清洗示例 ===")

    cleaner = DataCleaner()

    # 原始商品数据（包含需要清洗的内容）
    raw_product = {
        'source_id': ' 12345 ',
        'title': '  iPhone 13 Pro Max 256GB  \n\n',
        'description': '<p>最新款iPhone</p><script>alert("test")</script>',
        'price_text': '¥8999.5 - ¥9999.8元',
        'currency': 'RMB',
        'moq_text': '1起订',
        'price_unit': '个',
        'main_image_url': 'https://example.com/iphone.jpg',
        'detail_images': 'https://example.com/1.jpg, https://example.com/2.jpg, invalid_url',
        'sales_count': '1500',
        'rating': '4.8',
        'category_name': '  手机数码  '
    }

    # 清洗商品数据
    cleaned_product = cleaner.clean_product_data(raw_product)

    print("原始数据:")
    print(json.dumps(raw_product, ensure_ascii=False, indent=2))
    print("\n清洗后数据:")
    print(json.dumps(cleaned_product, ensure_ascii=False, indent=2))

    return cleaned_product


def example_data_validation():
    """数据验证示例"""
    print("\n=== 数据验证示例 ===")

    validator = DataValidator()

    # 测试数据（包含有效和无效的字段）
    test_product = {
        'source_id': 'product001',
        'title': '测试商品',
        'price_min': -100,  # 无效：负价格
        'price_max': 50,    # 无效：最大价格小于最小价格
        'currency': 'CNY',
        'sales_count': -1,  # 无效：负销量
        'rating': 6.0,      # 无效：超出评分范围
        'main_image_url': 'invalid_url',  # 无效URL
        'category_name': '电子产品'
    }

    # 验证商品数据
    validation_results = validator.validate_product_data(test_product)

    print("验证结果:")
    for result in validation_results:
        level_icon = "❌" if result.level.value == "error" else "⚠️" if result.level.value == "warning" else "ℹ️"
        print(f"{level_icon} {result.field}: {result.message}")
        if result.suggestion:
            print(f"   建议: {result.suggestion}")

    # 获取验证摘要
    summary = validator.get_validation_summary(validation_results)
    print(f"\n验证摘要: {summary['error_count']} 个错误, {summary['warning_count']} 个警告")

    return validation_results


def example_data_deduplication():
    """数据去重示例"""
    print("\n=== 数据去重示例 ===")

    deduplicator = DataDeduplicator()

    # 模拟重复商品数据
    products = [
        {
            'id': 1,
            'source_id': 'p001',
            'title': 'iPhone 13 Pro Max 256GB',
            'price_min': 8999,
            'price_max': 9999,
            'category_name': '手机',
            'description': 'Apple iPhone 13 Pro Max'
        },
        {
            'id': 2,
            'source_id': 'p002',
            'title': 'iPhone 13 Pro Max 256GB',  # 相同标题
            'price_min': 8999,
            'price_max': 9999,
            'category_name': '手机',
            'description': '苹果 iPhone 13 Pro Max'  # 相似描述
        },
        {
            'id': 3,
            'source_id': 'p003',
            'title': 'Samsung Galaxy S22 Ultra',
            'price_min': 7999,
            'price_max': 8999,
            'category_name': '手机',
            'description': 'Samsung flagship phone'
        },
        {
            'id': 4,
            'source_id': 'p004',
            'title': 'iPhone 13 Pro',  # 相似但不完全相同
            'price_min': 7999,
            'price_max': 8999,
            'category_name': '手机',
            'description': 'Apple iPhone 13 Pro'
        }
    ]

    # 查找重复商品
    duplicate_groups = deduplicator.find_duplicate_products(products)

    print(f"找到 {len(duplicate_groups)} 组重复数据:")

    for i, group in enumerate(duplicate_groups, 1):
        print(f"\n重复组 {i}:")
        print(f"  相似度: {group.similarity_score:.3f}")
        print(f"  重复字段: {group.duplicate_fields}")
        print(f"  包含记录: {[record['id'] for record in group.records]}")

        # 选择最佳记录
        best_id = deduplicator._select_best_product(group)
        best_record = next(record for record in group.records if record['id'] == best_id)
        print(f"  最佳记录: ID {best_id} - {best_record['title']}")

    # 获取去重统计
    stats = deduplicator.get_deduplication_statistics(duplicate_groups)
    print(f"\n去重统计:")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  重复记录数: {stats['duplicate_records']}")
    print(f"  重复率: {stats['duplicate_ratio']:.2%}")

    return duplicate_groups


def example_version_management():
    """版本管理示例"""
    print("\n=== 版本管理示例 ===")

    version_manager = VersionManager()

    entity_type = 'product'
    entity_id = 'demo_product_001'

    # 版本1: 创建
    version1_data = {
        'title': 'Demo Product',
        'price': 100,
        'description': 'Initial version',
        'category': 'Electronics'
    }

    version1 = version_manager.create_version(
        entity_type=entity_type,
        entity_id=entity_id,
        data=version1_data,
        change_type=ChangeType.CREATE,
        created_by='demo_user'
    )

    print(f"版本1: {version1.version_id} - {version1.change_type.value}")
    print(f"  数据: {version1.data}")

    # 版本2: 更新
    version2_data = {
        'title': 'Demo Product v2',
        'price': 120,
        'description': 'Updated version with new features',
        'category': 'Electronics',
        'features': ['Feature A', 'Feature B']
    }

    version2 = version_manager.create_version(
        entity_type=entity_type,
        entity_id=entity_id,
        data=version2_data,
        change_type=ChangeType.UPDATE,
        previous_data=version1.data,
        created_by='demo_user'
    )

    print(f"\n版本2: {version2.version_id} - {version2.change_type.value}")
    print(f"  数据: {version2.data}")
    print(f"  变更字段: {version2.changed_fields}")

    # 版本3: 再次更新
    version3_data = version2_data.copy()
    version3_data['price'] = 110
    version3_data['description'] = 'Price adjustment'

    version3 = version_manager.create_version(
        entity_type=entity_type,
        entity_id=entity_id,
        data=version3_data,
        change_type=ChangeType.UPDATE,
        previous_data=version2.data,
        created_by='demo_user'
    )

    print(f"\n版本3: {version3.version_id} - {version3.change_type.value}")
    print(f"  数据: {version3.data}")

    # 获取版本历史
    history = version_manager.get_version_history(entity_type, entity_id)
    print(f"\n版本历史 (共 {len(history)} 个版本):")
    for version in history:
        print(f"  {version.version_id}: {version.change_type.value} at {version.created_at}")

    # 比较版本
    diffs = version_manager.compare_versions(entity_type, entity_id, version1.version_id, version3.version_id)
    print(f"\n版本1 vs 版本3 的差异:")
    for diff in diffs:
        print(f"  {diff.field}: {diff.old_value} → {diff.new_value} ({diff.change_type})")

    # 回滚到版本2
    revert_version = version_manager.revert_to_version(entity_type, entity_id, version2.version_id)
    print(f"\n回滚到版本2: {revert_version.version_id}")
    print(f"  回滚后数据: {revert_version.data}")

    return version_manager


def example_quality_monitoring():
    """质量监控示例"""
    print("\n=== 质量监控示例 ===")

    monitor = DataQualityMonitor()

    # 模拟商品数据（包含不同质量的数据）
    products = [
        {
            'source_id': 'p001',
            'title': 'High Quality Product',
            'description': 'Complete product description with all details',
            'price_min': 100,
            'price_max': 150,
            'currency': 'CNY',
            'main_image_url': 'https://example.com/image1.jpg',
            'detail_images': ['https://example.com/detail1.jpg', 'https://example.com/detail2.jpg'],
            'sales_count': 500,
            'review_count': 100,
            'rating': 4.5,
            'category_name': 'Electronics',
            'specifications': {'color': 'black', 'size': 'large', 'material': 'metal'}
        },
        {
            'source_id': 'p002',
            'title': 'Medium Quality Product',
            'description': 'Brief description',
            'price_min': 80,
            'price_max': 120,
            'currency': 'CNY',
            'main_image_url': 'https://example.com/image2.jpg',
            'sales_count': 200,
            'rating': 4.0,
            'category_name': 'Electronics'
        },
        {
            'source_id': 'p003',
            'title': '',  # 缺少标题
            'description': '',
            'price_min': -10,  # 无效价格
            'price_max': 0,
            'currency': 'CNY',
            'main_image_url': 'invalid_url',  # 无效URL
            'sales_count': -1,  # 无效销量
            'rating': 6.0,  # 超出范围
            'category_name': ''
        }
    ]

    # 评估数据质量
    quality_report = monitor.assess_product_quality(products)

    print(f"质量评估结果:")
    print(f"  总体评分: {quality_report.overall_score:.2f}")
    print(f"  质量等级: {quality_report.quality_level.value}")
    print(f"  样本数量: {quality_report.sample_size}")

    print(f"\n各项指标:")
    for metric in quality_report.metrics:
        status_icon = "✅" if metric.status.value in ['excellent', 'good'] else "⚠️" if metric.status.value in ['fair', 'poor'] else "❌"
        print(f"  {status_icon} {metric.name}: {metric.value:.2f} (阈值: {metric.threshold})")
        print(f"    {metric.description}")

    print(f"\n发现的问题:")
    for issue in quality_report.issues:
        print(f"  ❌ {issue['metric']}: {issue['description']}")

    print(f"\n改进建议:")
    for i, recommendation in enumerate(quality_report.recommendations, 1):
        print(f"  {i}. {recommendation}")

    return quality_report


def example_data_pipeline():
    """数据处理管道完整示例"""
    print("\n=== 数据处理管道完整示例 ===")

    pipeline = DataPipeline()

    # 模拟原始商品数据
    raw_products = [
        {
            'source_id': ' raw001 ',
            'title': '  Smartphone Pro  \n\n',
            'description': '<p>Latest smartphone</p>',
            'price_text': '¥2999 - ¥3999元',
            'currency': 'RMB',
            'main_image_url': 'https://example.com/phone.jpg',
            'sales_count': '1500',
            'rating': '4.6',
            'category_name': '  手机  '
        },
        {
            'source_id': '  raw002  ',
            'title': 'Smartphone Pro',  # 潜在重复
            'description': 'Newest smartphone model',
            'price_text': '¥2999 - ¥3999',
            'currency': 'RMB',
            'main_image_url': 'https://example.com/phone2.jpg',
            'sales_count': '1200',
            'rating': '4.5',
            'category_name': '手机'
        },
        {
            'source_id': '',  # 无效记录
            'title': '',
            'price_text': 'invalid',
            'currency': 'RMB'
        }
    ]

    print(f"输入数据: {len(raw_products)} 条原始商品记录")

    # 配置处理选项
    options = {
        'skip_cleaning': False,
        'skip_validation': False,
        'skip_deduplication': False,
        'skip_versioning': False,
        'skip_quality_monitoring': False
    }

    # 执行数据处理管道
    result = pipeline.process_products(raw_products, options)

    print(f"\n处理结果:")
    print(f"  状态: {result.status.value}")
    print(f"  总记录数: {result.total_records}")
    print(f"  成功处理: {result.processed_records}")
    print(f"  处理失败: {result.failed_records}")
    print(f"  处理时间: {result.processing_time:.2f}秒")
    print(f"  创建版本: {result.versions_created}")

    # 清洗结果
    print(f"\n清洗结果:")
    success_count = sum(1 for r in result.cleaning_results if r['status'] == 'success')
    fail_count = sum(1 for r in result.cleaning_results if r['status'] == 'failed')
    print(f"  成功清洗: {success_count}")
    print(f"  清洗失败: {fail_count}")

    # 验证结果
    total_errors = sum(
        sum(1 for r in results if r.level.value == 'error')
        for results in result.validation_results
    )
    total_warnings = sum(
        sum(1 for r in results if r.level.value == 'warning')
        for results in result.validation_results
    )
    print(f"\n验证结果:")
    print(f"  错误数量: {total_errors}")
    print(f"  警告数量: {total_warnings}")

    # 去重结果
    print(f"\n去重结果:")
    print(f"  重复组数: {len(result.duplicate_groups)}")
    for group in result.duplicate_groups:
        print(f"    组 {group.group_id}: {len(group.records)} 条记录，相似度 {group.similarity_score:.2f}")

    # 质量评估结果
    if result.quality_report:
        print(f"\n质量评估:")
        print(f"  总体评分: {result.quality_report.overall_score:.2f}")
        print(f"  质量等级: {result.quality_report.quality_level.value}")
        print(f"  问题数量: {len(result.quality_report.issues)}")

    # 获取处理摘要
    summary = pipeline.get_pipeline_summary(result)
    print(f"\n处理摘要:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 导出处理报告
    report_file = f"/tmp/pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    pipeline.export_pipeline_report(result, report_file)
    print(f"\n处理报告已导出到: {report_file}")

    return result


def main():
    """主函数 - 运行所有示例"""
    print("🚀 1688sync 数据处理管道示例")
    print("=" * 50)

    try:
        # 1. 数据清洗示例
        example_data_cleaning()

        # 2. 数据验证示例
        example_data_validation()

        # 3. 数据去重示例
        example_data_deduplication()

        # 4. 版本管理示例
        example_version_management()

        # 5. 质量监控示例
        example_quality_monitoring()

        # 6. 完整管道示例
        example_data_pipeline()

        print("\n" + "=" * 50)
        print("✅ 所有示例运行完成！")

    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        print(f"❌ 示例运行失败: {e}")


if __name__ == '__main__':
    main()