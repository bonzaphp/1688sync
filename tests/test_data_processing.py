"""
数据处理模块测试用例
"""
import unittest
from decimal import Decimal
from datetime import datetime

from src.data_processing.cleaner import DataCleaner
from src.data_processing.validator import DataValidator, ValidationLevel
from src.data_processing.deduplicator import DataDeduplicator
from src.data_processing.version_manager import VersionManager, ChangeType
from src.data_processing.quality_monitor import DataQualityMonitor, QualityLevel
from src.data_processing.pipeline import DataPipeline, PipelineStatus


class TestDataCleaner(unittest.TestCase):
    """数据清洗器测试"""

    def setUp(self):
        """测试前准备"""
        self.cleaner = DataCleaner()

    def test_clean_product_data(self):
        """测试商品数据清洗"""
        # 原始数据（包含需要清洗的内容）
        raw_data = {
            'source_id': ' 12345 ',
            'title': '  测试商品  \n\n',
            'description': '<p>商品描述</p><script>alert("test")</script>',
            'price_text': '¥100.5 - ¥200.8元',
            'currency': 'RMB',
            'moq_text': '100起订',
            'price_unit': '个',
            'main_image_url': 'https://example.com/image.jpg',
            'detail_images': 'https://example.com/1.jpg, https://example.com/2.jpg',
            'sales_count': '150',
            'rating': '4.5',
            'category_name': '  电子产品  '
        }

        cleaned = self.cleaner.clean_product_data(raw_data)

        # 验证清洗结果
        self.assertEqual(cleaned['source_id'], '12345')
        self.assertEqual(cleaned['title'], '测试商品')
        self.assertEqual(cleaned['description'], '商品描述')
        self.assertEqual(cleaned['price_min'], Decimal('100.5'))
        self.assertEqual(cleaned['price_max'], Decimal('200.8'))
        self.assertEqual(cleaned['currency'], 'CNY')
        self.assertEqual(cleaned['moq'], 100)
        self.assertEqual(cleaned['price_unit'], 'piece')
        self.assertEqual(cleaned['sales_count'], 150)
        self.assertEqual(cleaned['rating'], Decimal('4.5'))
        self.assertEqual(cleaned['category_name'], '电子产品')

        # 验证图片列表
        self.assertIsInstance(cleaned['detail_images'], list)
        self.assertEqual(len(cleaned['detail_images']), 2)

    def test_clean_supplier_data(self):
        """测试供应商数据清洗"""
        raw_data = {
            'source_id': ' supplier001 ',
            'name': '  测试供应商  ',
            'phone': ' +86-13800138000 ',
            'email': 'TEST@EXAMPLE.COM',
            'company_name': '  测试公司  ',
            'established_date': '2020年01月01日',
            'registered_capital': '100万 元',
            'certifications': ' ISO9001, CE认证 '
        }

        cleaned = self.cleaner.clean_supplier_data(raw_data)

        # 验证清洗结果
        self.assertEqual(cleaned['source_id'], 'supplier001')
        self.assertEqual(cleaned['name'], '测试供应商')
        self.assertEqual(cleaned['phone'], '+8613800138000')
        self.assertEqual(cleaned['email'], 'test@example.com')
        self.assertEqual(cleaned['company_name'], '测试公司')
        self.assertEqual(cleaned['established_date'], '2020-01-01')
        self.assertEqual(cleaned['registered_capital'], '1000000')
        self.assertIsInstance(cleaned['certifications'], list)
        self.assertIn('ISO9001', cleaned['certifications'])

    def test_extract_prices(self):
        """测试价格提取"""
        test_cases = [
            ('¥100.5', [100.5]),
            ('100元', [100.0]),
            ('RMB 200.8', [200.8]),
            ('50元 - 100元', [50.0, 100.0]),
            ('无效价格', []),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                prices = self.cleaner._extract_prices(text)
                self.assertEqual(prices, expected)

    def test_standardize_unit(self):
        """测试单位标准化"""
        test_cases = [
            ('个', 'piece'),
            ('公斤', 'kg'),
            ('米', 'meter'),
            ('unknown', 'unknown'),
        ]

        for unit, expected in test_cases:
            with self.subTest(unit=unit):
                result = self.cleaner._standardize_unit(unit)
                self.assertEqual(result, expected)


class TestDataValidator(unittest.TestCase):
    """数据验证器测试"""

    def setUp(self):
        """测试前准备"""
        self.validator = DataValidator()

    def test_validate_product_data_valid(self):
        """测试有效商品数据验证"""
        valid_data = {
            'source_id': 'product001',
            'title': '测试商品',
            'price_min': Decimal('100.0'),
            'price_max': Decimal('200.0'),
            'currency': 'CNY',
            'sales_count': 50,
            'review_count': 10,
            'rating': 4.5,
            'main_image_url': 'https://example.com/image.jpg',
            'category_name': '电子产品'
        }

        results = self.validator.validate_product_data(valid_data)

        # 应该没有错误
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        self.assertEqual(len(errors), 0)

        # 整体验证应该通过
        overall_result = next(r for r in results if r.field == 'overall')
        self.assertTrue(overall_result.is_valid)

    def test_validate_product_data_invalid(self):
        """测试无效商品数据验证"""
        invalid_data = {
            'source_id': '',  # 必填字段为空
            'title': '',
            'price_min': -10,  # 负价格
            'price_max': 5,    # 最大价格小于最小价格
            'rating': 6.0,     # 超出评分范围
            'sales_count': -1, # 负销量
            'main_image_url': 'invalid_url'
        }

        results = self.validator.validate_product_data(invalid_data)

        # 应该有多个错误
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        self.assertGreater(len(errors), 0)

        # 验证具体错误
        error_fields = [r.field for r in errors]
        self.assertIn('source_id', error_fields)
        self.assertIn('price_min', error_fields)
        self.assertIn('rating', error_fields)

    def test_validate_supplier_data_valid(self):
        """测试有效供应商数据验证"""
        valid_data = {
            'source_id': 'supplier001',
            'name': '测试供应商',
            'phone': '+8613800138000',
            'email': 'test@example.com',
            'company_name': '测试公司'
        }

        results = self.validator.validate_supplier_data(valid_data)

        # 应该没有错误
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        self.assertEqual(len(errors), 0)

    def test_validate_phone(self):
        """测试电话验证"""
        valid_phones = ['13800138000', '+8613800138000', '+1234567890']
        invalid_phones = ['123', 'abc', '138001380000']

        for phone in valid_phones:
            with self.subTest(phone=phone):
                self.assertTrue(self.validator._is_valid_phone(phone))

        for phone in invalid_phones:
            with self.subTest(phone=phone):
                self.assertFalse(self.validator._is_valid_phone(phone))

    def test_validate_email(self):
        """测试邮箱验证"""
        valid_emails = ['test@example.com', 'user.name@domain.co.uk']
        invalid_emails = ['invalid', 'test@', '@domain.com', 'test..test@domain.com']

        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(self.validator._is_valid_email(email))

        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(self.validator._is_valid_email(email))


class TestDataDeduplicator(unittest.TestCase):
    """数据去重器测试"""

    def setUp(self):
        """测试前准备"""
        self.deduplicator = DataDeduplicator()

    def test_find_duplicate_products(self):
        """测试商品去重"""
        products = [
            {
                'id': 1,
                'source_id': 'p001',
                'title': 'iPhone 13',
                'price_min': 5000,
                'price_max': 6000,
                'category_name': '手机'
            },
            {
                'id': 2,
                'source_id': 'p002',
                'title': 'iPhone 13',  # 相同标题
                'price_min': 5100,
                'price_max': 5900,
                'category_name': '手机'
            },
            {
                'id': 3,
                'source_id': 'p003',
                'title': 'Samsung Galaxy',
                'price_min': 4000,
                'price_max': 5000,
                'category_name': '手机'
            }
        ]

        duplicate_groups = self.deduplicator.find_duplicate_products(products)

        # 应该找到一组重复（ID 1和2）
        self.assertEqual(len(duplicate_groups), 1)
        self.assertEqual(len(duplicate_groups[0].records), 2)

        # 验证相似度
        self.assertGreater(duplicate_groups[0].similarity_score, 0.85)

    def test_find_duplicate_suppliers(self):
        """测试供应商去重"""
        suppliers = [
            {
                'id': 1,
                'source_id': 's001',
                'name': '华为技术有限公司',
                'phone': '13800138000',
                'company_name': '华为技术有限公司'
            },
            {
                'id': 2,
                'source_id': 's002',
                'name': '华为技术有限公司',  # 相同名称
                'phone': '13800138000',     # 相同电话
                'company_name': '华为技术有限公司'
            },
            {
                'id': 3,
                'source_id': 's003',
                'name': '小米科技',
                'phone': '13800138001',
                'company_name': '小米科技有限责任公司'
            }
        ]

        duplicate_groups = self.deduplicator.find_duplicate_suppliers(suppliers)

        # 应该找到一组重复（ID 1和2）
        self.assertEqual(len(duplicate_groups), 1)
        self.assertEqual(len(duplicate_groups[0].records), 2)

    def test_calculate_text_similarity(self):
        """测试文本相似度计算"""
        text1 = "iPhone 13 128GB"
        text2 = "iPhone 13 256GB"
        text3 = "Samsung Galaxy S21"

        similarity_12 = self.deduplicator._calculate_text_similarity(text1, text2)
        similarity_13 = self.deduplicator._calculate_text_similarity(text1, text3)

        # 相似文本应该有更高相似度
        self.assertGreater(similarity_12, similarity_13)
        self.assertGreater(similarity_12, 0.5)

    def test_select_best_product(self):
        """测试最佳商品选择"""
        from src.data_processing.deduplicator import DuplicateGroup

        # 创建测试重复组
        group = DuplicateGroup(
            group_id='test_group',
            records=[
                {
                    'id': 1,
                    'title': 'iPhone 13',
                    'description': '完整描述',
                    'price_min': 5000,
                    'main_image_url': 'https://example.com/1.jpg',
                    'sales_count': 100,
                    'rating': 4.5
                },
                {
                    'id': 2,
                    'title': 'iPhone 13',
                    'description': '简短描述',
                    'price_min': 5000,
                    'main_image_url': '',
                    'sales_count': 50,
                    'rating': 4.0
                }
            ],
            similarity_score=0.9,
            duplicate_fields=['title']
        )

        best_id = self.deduplicator._select_best_product(group)

        # 应该选择第一个更完整的记录
        self.assertEqual(best_id, 1)


class TestVersionManager(unittest.TestCase):
    """版本管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.version_manager = VersionManager()

    def test_create_version(self):
        """测试版本创建"""
        data = {'title': '测试商品', 'price': 100}

        version = self.version_manager.create_version(
            entity_type='product',
            entity_id='p001',
            data=data,
            change_type=ChangeType.CREATE
        )

        # 验证版本信息
        self.assertEqual(version.entity_type, 'product')
        self.assertEqual(version.entity_id, 'p001')
        self.assertEqual(version.change_type, ChangeType.CREATE)
        self.assertEqual(version.data, data)
        self.assertIsNotNone(version.version_id)
        self.assertIsNotNone(version.checksum)

    def test_version_history(self):
        """测试版本历史"""
        entity_type = 'product'
        entity_id = 'p001'

        # 创建多个版本
        for i in range(3):
            data = {'title': f'版本{i+1}', 'price': 100 + i * 10}
            change_type = ChangeType.CREATE if i == 0 else ChangeType.UPDATE
            previous_data = {'title': f'版本{i}', 'price': 100 + (i-1) * 10} if i > 0 else None

            self.version_manager.create_version(
                entity_type=entity_type,
                entity_id=entity_id,
                data=data,
                change_type=change_type,
                previous_data=previous_data
            )

        # 获取版本历史
        history = self.version_manager.get_version_history(entity_type, entity_id)

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].change_type, ChangeType.CREATE)
        self.assertEqual(history[1].change_type, ChangeType.UPDATE)
        self.assertEqual(history[2].change_type, ChangeType.UPDATE)

    def test_compare_versions(self):
        """测试版本比较"""
        entity_type = 'product'
        entity_id = 'p001'

        # 创建两个版本
        version1 = self.version_manager.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data={'title': '版本1', 'price': 100, 'category': '手机'},
            change_type=ChangeType.CREATE
        )

        version2 = self.version_manager.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data={'title': '版本2', 'price': 120, 'category': '手机'},
            change_type=ChangeType.UPDATE,
            previous_data=version1.data
        )

        # 比较版本
        diffs = self.version_manager.compare_versions(
            entity_type, entity_id, version1.version_id, version2.version_id
        )

        # 应该检测到标题和价格的变化
        diff_fields = [diff.field for diff in diffs]
        self.assertIn('title', diff_fields)
        self.assertIn('price', diff_fields)

        title_diff = next(diff for diff in diffs if diff.field == 'title')
        self.assertEqual(title_diff.old_value, '版本1')
        self.assertEqual(title_diff.new_value, '版本2')

    def test_revert_to_version(self):
        """测试版本回滚"""
        entity_type = 'product'
        entity_id = 'p001'

        # 创建初始版本
        original_version = self.version_manager.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data={'title': '原始标题', 'price': 100},
            change_type=ChangeType.CREATE
        )

        # 创建更新版本
        updated_version = self.version_manager.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data={'title': '更新标题', 'price': 120},
            change_type=ChangeType.UPDATE,
            previous_data=original_version.data
        )

        # 回滚到原始版本
        revert_version = self.version_manager.revert_to_version(
            entity_type, entity_id, original_version.version_id
        )

        # 验证回滚结果
        self.assertEqual(revert_version.data['title'], '原始标题')
        self.assertEqual(revert_version.data['price'], 100)
        self.assertEqual(revert_version.change_type, ChangeType.UPDATE)


class TestDataQualityMonitor(unittest.TestCase):
    """数据质量监控器测试"""

    def setUp(self):
        """测试前准备"""
        self.monitor = DataQualityMonitor()

    def test_assess_product_quality_good(self):
        """测试良好质量的商品数据"""
        products = [
            {
                'source_id': f'p{i:03d}',
                'title': f'高质量商品{i}',
                'description': f'这是商品{i}的详细描述',
                'price_min': 100 + i * 10,
                'price_max': 150 + i * 10,
                'main_image_url': f'https://example.com/image{i}.jpg',
                'sales_count': 100 + i * 5,
                'rating': 4.0 + (i % 2) * 0.5,
                'category_name': '电子产品'
            }
            for i in range(10)
        ]

        report = self.monitor.assess_product_quality(products)

        # 验证报告
        self.assertEqual(report.entity_type, 'product')
        self.assertEqual(report.sample_size, 10)
        self.assertGreater(report.overall_score, 0.8)
        self.assertIn(report.quality_level, [QualityLevel.EXCELLENT, QualityLevel.GOOD])

        # 验证指标
        metric_names = [metric.name for metric in report.metrics]
        self.assertIn('数据完整性', metric_names)
        self.assertIn('数据准确性', metric_names)
        self.assertIn('数据有效性', metric_names)

    def test_assess_product_quality_poor(self):
        """测试质量较差的商品数据"""
        products = [
            {
                'source_id': '',  # 必填字段缺失
                'title': '',
                'description': '',
                'price_min': -10,  # 无效价格
                'price_max': 5,    # 逻辑错误
                'main_image_url': 'invalid_url',
                'sales_count': -1, # 无效销量
                'rating': 6.0,     # 超出范围
                'category_name': ''
            }
        ]

        report = self.monitor.assess_product_quality(products)

        # 质量应该较差
        self.assertLess(report.overall_score, 0.7)
        self.assertIn(report.quality_level, [QualityLevel.POOR, QualityLevel.CRITICAL])

        # 应该有问题和建议
        self.assertGreater(len(report.issues), 0)
        self.assertGreater(len(report.recommendations), 0)

    def test_assess_supplier_quality(self):
        """测试供应商数据质量评估"""
        suppliers = [
            {
                'source_id': f's{i:03d}',
                'name': f'供应商{i}',
                'phone': f'1380013800{i}',
                'email': f'supplier{i}@example.com',
                'company_name': f'测试公司{i}',
                'address': f'测试地址{i}'
            }
            for i in range(5)
        ]

        report = self.monitor.assess_supplier_quality(suppliers)

        # 验证报告
        self.assertEqual(report.entity_type, 'supplier')
        self.assertEqual(report.sample_size, 5)
        self.assertGreaterEqual(report.overall_score, 0.0)
        self.assertLessEqual(report.overall_score, 1.0)

    def test_calculate_completeness(self):
        """测试完整性计算"""
        data = [
            {'title': '商品1', 'price': 100, 'description': '描述1'},  # 完整
            {'title': '商品2', 'price': 200},                         # 缺少描述
            {'price': 300},                                            # 缺少标题
        ]

        rules = {
            'required_fields': ['title'],
            'important_fields': ['price'],
            'optional_fields': ['description']
        }

        metric = self.monitor._assess_completeness(data, rules)

        # 验证完整性计算
        self.assertGreater(metric.value, 0)
        self.assertLessEqual(metric.value, 1)
        self.assertEqual(metric.metric_type.value, 'completeness')


class TestDataPipeline(unittest.TestCase):
    """数据处理管道测试"""

    def setUp(self):
        """测试前准备"""
        self.pipeline = DataPipeline()

    def test_process_products_success(self):
        """测试成功的商品数据处理"""
        raw_products = [
            {
                'source_id': 'p001',
                'title': 'iPhone 13',
                'description': '苹果手机',
                'price_text': '¥5000 - ¥6000',
                'main_image_url': 'https://example.com/iphone.jpg',
                'sales_count': '1000',
                'rating': '4.5'
            },
            {
                'source_id': 'p002',
                'title': 'Samsung Galaxy',
                'description': '三星手机',
                'price_text': '¥4000 - ¥5000',
                'main_image_url': 'https://example.com/galaxy.jpg',
                'sales_count': '800',
                'rating': '4.3'
            }
        ]

        result = self.pipeline.process_products(raw_products)

        # 验证处理结果
        self.assertEqual(result.status, PipelineStatus.COMPLETED)
        self.assertEqual(result.total_records, 2)
        self.assertEqual(result.processed_records, 2)
        self.assertEqual(result.failed_records, 0)
        self.assertGreater(result.processing_time, 0)

        # 验证各步骤结果
        self.assertEqual(len(result.cleaning_results), 2)
        self.assertEqual(len(result.validation_results), 2)
        self.assertIsNotNone(result.quality_report)

    def test_process_products_with_errors(self):
        """测试包含错误的商品数据处理"""
        raw_products = [
            {
                'source_id': 'p001',
                'title': 'iPhone 13',
                'price_text': '¥5000'
            },
            {
                'source_id': '',  # 必填字段缺失
                'title': '',
                'price_text': 'invalid_price'
            }
        ]

        result = self.pipeline.process_products(raw_products)

        # 验证处理结果
        self.assertEqual(result.status, PipelineStatus.PARTIAL)
        self.assertEqual(result.total_records, 2)
        self.assertGreater(result.failed_records, 0)

        # 应该有验证错误
        total_errors = sum(
            sum(1 for r in results if r.level.value == 'error')
            for results in result.validation_results
        )
        self.assertGreater(total_errors, 0)

    def test_process_suppliers(self):
        """测试供应商数据处理"""
        raw_suppliers = [
            {
                'source_id': 's001',
                'name': '华为技术',
                'phone': '13800138000',
                'email': 'huawei@example.com'
            }
        ]

        result = self.pipeline.process_suppliers(raw_suppliers)

        # 验证处理结果
        self.assertEqual(result.status, PipelineStatus.COMPLETED)
        self.assertEqual(result.entity_type, 'supplier')
        self.assertEqual(result.total_records, 1)
        self.assertEqual(result.processed_records, 1)

    def test_pipeline_with_options(self):
        """测试带选项的管道处理"""
        raw_products = [
            {
                'source_id': 'p001',
                'title': 'iPhone 13',
                'price_text': '¥5000'
            }
        ]

        # 跳过某些步骤
        options = {
            'skip_validation': True,
            'skip_deduplication': True,
            'skip_quality_monitoring': True
        }

        result = self.pipeline.process_products(raw_products, options)

        # 验证选项生效
        self.assertEqual(len(result.validation_results), 0)  # 跳过验证
        self.assertEqual(len(result.duplicate_groups), 0)    # 跳过去重
        self.assertIsNone(result.quality_report)            # 跳过质量监控

    def test_get_pipeline_summary(self):
        """测试管道摘要"""
        raw_products = [
            {
                'source_id': 'p001',
                'title': 'iPhone 13',
                'price_text': '¥5000'
            }
        ]

        result = self.pipeline.process_products(raw_products)
        summary = self.pipeline.get_pipeline_summary(result)

        # 验证摘要内容
        self.assertIn('entity_type', summary)
        self.assertIn('status', summary)
        self.assertIn('record_summary', summary)
        self.assertIn('processing_time', summary)

        record_summary = summary['record_summary']
        self.assertEqual(record_summary['total'], 1)
        self.assertEqual(record_summary['processed'], 1)
        self.assertEqual(record_summary['success_rate'], 1.0)

    def test_export_pipeline_report(self):
        """测试管道报告导出"""
        raw_products = [
            {
                'source_id': 'p001',
                'title': 'iPhone 13',
                'price_text': '¥5000'
            }
        ]

        result = self.pipeline.process_products(raw_products)
        report_content = self.pipeline.export_pipeline_report(result)

        # 验证报告内容
        self.assertIn('pipeline_info', report_content)
        self.assertIn('processing_summary', report_content)
        self.assertIn('detailed_results', report_content)

        # 验证JSON格式
        import json
        report_data = json.loads(report_content)
        self.assertIn('pipeline_info', report_data)


if __name__ == '__main__':
    unittest.main()