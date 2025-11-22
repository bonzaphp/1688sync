"""
数据质量监控
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"  # 优秀 (>90%)
    GOOD = "good"           # 良好 (80-90%)
    FAIR = "fair"           # 一般 (70-80%)
    POOR = "poor"           # 较差 (60-70%)
    CRITICAL = "critical"   # 严重 (<60%)


class MetricType(Enum):
    """指标类型"""
    COMPLETENESS = "completeness"    # 完整性
    ACCURACY = "accuracy"            # 准确性
    CONSISTENCY = "consistency"      # 一致性
    VALIDITY = "validity"            # 有效性
    TIMELINESS = "timeliness"        # 及时性
    UNIQUENESS = "uniqueness"        # 唯一性


@dataclass
class QualityMetric:
    """质量指标"""
    name: str
    metric_type: MetricType
    value: float
    threshold: float
    status: QualityLevel
    description: str
    details: Dict[str, Any]
    measured_at: str


@dataclass
class QualityReport:
    """质量报告"""
    entity_type: str
    overall_score: float
    quality_level: QualityLevel
    metrics: List[QualityMetric]
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    measured_at: str
    sample_size: int


class DataQualityMonitor:
    """数据质量监控器"""

    def __init__(self):
        """初始化质量监控器"""
        # 商品质量规则
        self.product_quality_rules = {
            'completeness': {
                'required_fields': ['source_id', 'title'],
                'important_fields': ['description', 'price_min', 'main_image_url'],
                'optional_fields': ['subtitle', 'video_url', 'specifications']
            },
            'accuracy': {
                'price_range': {'min': 0.01, 'max': 1000000},
                'rating_range': {'min': 0.0, 'max': 5.0},
                'sales_max': 10000000
            },
            'validity': {
                'url_fields': ['main_image_url', 'video_url'],
                'email_fields': [],
                'phone_fields': []
            },
            'thresholds': {
                'completeness': 0.85,
                'accuracy': 0.90,
                'validity': 0.95,
                'consistency': 0.80,
                'overall': 0.80
            }
        }

        # 供应商质量规则
        self.supplier_quality_rules = {
            'completeness': {
                'required_fields': ['source_id', 'name'],
                'important_fields': ['phone', 'company_name', 'address'],
                'optional_fields': ['email', 'qq', 'wechat', 'description']
            },
            'accuracy': {
                'phone_length': {'min': 7, 'max': 15},
                'name_max_length': 200
            },
            'validity': {
                'email_fields': ['email'],
                'phone_fields': ['phone'],
                'url_fields': []
            },
            'thresholds': {
                'completeness': 0.80,
                'accuracy': 0.90,
                'validity': 0.95,
                'consistency': 0.85,
                'overall': 0.80
            }
        }

    def assess_product_quality(self, products: List[Dict[str, Any]],
                              sample_size: int = 1000) -> QualityReport:
        """评估商品数据质量"""
        try:
            logger.info(f"开始评估商品数据质量，样本量: {min(len(products), sample_size)}")

            # 采样
            sample = products[:sample_size] if len(products) > sample_size else products

            # 计算各项指标
            metrics = []

            # 完整性指标
            completeness_metric = self._assess_completeness(
                sample, self.product_quality_rules['completeness']
            )
            metrics.append(completeness_metric)

            # 准确性指标
            accuracy_metric = self._assess_accuracy(
                sample, self.product_quality_rules['accuracy']
            )
            metrics.append(accuracy_metric)

            # 有效性指标
            validity_metric = self._assess_validity(
                sample, self.product_quality_rules['validity']
            )
            metrics.append(validity_metric)

            # 一致性指标
            consistency_metric = self._assess_consistency(sample, 'product')
            metrics.append(consistency_metric)

            # 唯一性指标
            uniqueness_metric = self._assess_uniqueness(sample, 'product')
            metrics.append(uniqueness_metric)

            # 计算总分
            overall_score = self._calculate_overall_score(metrics)
            quality_level = self._determine_quality_level(
                overall_score, self.product_quality_rules['thresholds']['overall']
            )

            # 识别问题和建议
            issues = self._identify_quality_issues(metrics)
            recommendations = self._generate_recommendations(issues, metrics)

            # 创建报告
            report = QualityReport(
                entity_type='product',
                overall_score=overall_score,
                quality_level=quality_level,
                metrics=metrics,
                issues=issues,
                recommendations=recommendations,
                measured_at=datetime.now().isoformat(),
                sample_size=len(sample)
            )

            logger.info(f"商品质量评估完成: {quality_level.value} ({overall_score:.2f})")
            return report

        except Exception as e:
            logger.error(f"评估商品质量失败: {e}")
            raise

    def assess_supplier_quality(self, suppliers: List[Dict[str, Any]],
                               sample_size: int = 1000) -> QualityReport:
        """评估供应商数据质量"""
        try:
            logger.info(f"开始评估供应商数据质量，样本量: {min(len(suppliers), sample_size)}")

            # 采样
            sample = suppliers[:sample_size] if len(suppliers) > sample_size else suppliers

            # 计算各项指标
            metrics = []

            # 完整性指标
            completeness_metric = self._assess_completeness(
                sample, self.supplier_quality_rules['completeness']
            )
            metrics.append(completeness_metric)

            # 准确性指标
            accuracy_metric = self._assess_accuracy(
                sample, self.supplier_quality_rules['accuracy']
            )
            metrics.append(accuracy_metric)

            # 有效性指标
            validity_metric = self._assess_validity(
                sample, self.supplier_quality_rules['validity']
            )
            metrics.append(validity_metric)

            # 一致性指标
            consistency_metric = self._assess_consistency(sample, 'supplier')
            metrics.append(consistency_metric)

            # 唯一性指标
            uniqueness_metric = self._assess_uniqueness(sample, 'supplier')
            metrics.append(uniqueness_metric)

            # 计算总分
            overall_score = self._calculate_overall_score(metrics)
            quality_level = self._determine_quality_level(
                overall_score, self.supplier_quality_rules['thresholds']['overall']
            )

            # 识别问题和建议
            issues = self._identify_quality_issues(metrics)
            recommendations = self._generate_recommendations(issues, metrics)

            # 创建报告
            report = QualityReport(
                entity_type='supplier',
                overall_score=overall_score,
                quality_level=quality_level,
                metrics=metrics,
                issues=issues,
                recommendations=recommendations,
                measured_at=datetime.now().isoformat(),
                sample_size=len(sample)
            )

            logger.info(f"供应商质量评估完成: {quality_level.value} ({overall_score:.2f})")
            return report

        except Exception as e:
            logger.error(f"评估供应商质量失败: {e}")
            raise

    def _assess_completeness(self, data: List[Dict[str, Any]],
                           rules: Dict[str, List[str]]) -> QualityMetric:
        """评估数据完整性"""
        total_records = len(data)
        if total_records == 0:
            return QualityMetric(
                name="数据完整性",
                metric_type=MetricType.COMPLETENESS,
                value=0.0,
                threshold=0.85,
                status=QualityLevel.CRITICAL,
                description="数据完整性评估",
                details={'error': '没有数据样本'}
            )

        required_fields = rules['required_fields']
        important_fields = rules['important_fields']
        optional_fields = rules['optional_fields']

        # 统计字段完整性
        field_stats = {}
        for field in required_fields + important_fields + optional_fields:
            filled_count = sum(1 for record in data if self._is_field_filled(record.get(field)))
            field_stats[field] = {
                'filled_count': filled_count,
                'total_count': total_records,
                'completeness_rate': filled_count / total_records
            }

        # 计算加权完整性分数
        required_score = sum(
            field_stats[field]['completeness_rate']
            for field in required_fields
        ) / len(required_fields) if required_fields else 0

        important_score = sum(
            field_stats[field]['completeness_rate']
            for field in important_fields
        ) / len(important_fields) if important_fields else 0

        optional_score = sum(
            field_stats[field]['completeness_rate']
            for field in optional_fields
        ) / len(optional_fields) if optional_fields else 0

        # 加权计算
        overall_completeness = (
            required_score * 0.5 +  # 必填字段权重50%
            important_score * 0.3 +  # 重要字段权重30%
            optional_score * 0.2     # 可选字段权重20%
        )

        # 确定质量等级
        quality_level = self._determine_quality_level(overall_completeness, 0.85)

        return QualityMetric(
            name="数据完整性",
            metric_type=MetricType.COMPLETENESS,
            value=overall_completeness,
            threshold=0.85,
            status=quality_level,
            description=f"数据完整性: 必填字段 {required_score:.2f}, 重要字段 {important_score:.2f}, 可选字段 {optional_score:.2f}",
            details={
                'field_stats': field_stats,
                'required_score': required_score,
                'important_score': important_score,
                'optional_score': optional_score
            }
        )

    def _assess_accuracy(self, data: List[Dict[str, Any]],
                        rules: Dict[str, Any]) -> QualityMetric:
        """评估数据准确性"""
        total_records = len(data)
        if total_records == 0:
            return QualityMetric(
                name="数据准确性",
                metric_type=MetricType.ACCURACY,
                value=0.0,
                threshold=0.90,
                status=QualityLevel.CRITICAL,
                description="数据准确性评估",
                details={'error': '没有数据样本'}
            )

        accurate_count = 0
        accuracy_issues = []

        for record in data:
            is_accurate = True
            record_issues = []

            # 检查价格范围
            if 'price_range' in rules:
                price_min = record.get('price_min')
                price_max = record.get('price_max')

                if price_min is not None:
                    if not (rules['price_range']['min'] <= price_min <= rules['price_range']['max']):
                        is_accurate = False
                        record_issues.append(f"最小价格超出范围: {price_min}")

                if price_max is not None:
                    if not (rules['price_range']['min'] <= price_max <= rules['price_range']['max']):
                        is_accurate = False
                        record_issues.append(f"最大价格超出范围: {price_max}")

                if price_min and price_max and price_min > price_max:
                    is_accurate = False
                    record_issues.append(f"最小价格大于最大价格: {price_min} > {price_max}")

            # 检查评分范围
            if 'rating_range' in rules:
                rating = record.get('rating')
                if rating is not None:
                    if not (rules['rating_range']['min'] <= rating <= rules['rating_range']['max']):
                        is_accurate = False
                        record_issues.append(f"评分超出范围: {rating}")

            # 检查销量上限
            if 'sales_max' in rules:
                sales_count = record.get('sales_count')
                if sales_count is not None and sales_count > rules['sales_max']:
                    is_accurate = False
                    record_issues.append(f"销量异常高: {sales_count}")

            if is_accurate:
                accurate_count += 1
            else:
                accuracy_issues.extend(record_issues)

        accuracy_rate = accurate_count / total_records
        quality_level = self._determine_quality_level(accuracy_rate, 0.90)

        return QualityMetric(
            name="数据准确性",
            metric_type=MetricType.ACCURACY,
            value=accuracy_rate,
            threshold=0.90,
            status=quality_level,
            description=f"数据准确性: {accurate_count}/{total_records} 条记录准确",
            details={
                'accurate_count': accurate_count,
                'total_count': total_records,
                'accuracy_issues': accuracy_issues[:20]  # 只保留前20个问题
            }
        )

    def _assess_validity(self, data: List[Dict[str, Any]],
                        rules: Dict[str, List[str]]) -> QualityMetric:
        """评估数据有效性"""
        total_records = len(data)
        if total_records == 0:
            return QualityMetric(
                name="数据有效性",
                metric_type=MetricType.VALIDITY,
                value=0.0,
                threshold=0.95,
                status=QualityLevel.CRITICAL,
                description="数据有效性评估",
                details={'error': '没有数据样本'}
            )

        valid_count = 0
        validity_issues = []

        for record in data:
            is_valid = True
            record_issues = []

            # 检查URL有效性
            for field in rules.get('url_fields', []):
                url = record.get(field)
                if url and not self._is_valid_url(url):
                    is_valid = False
                    record_issues.append(f"无效URL {field}: {url}")

            # 检查邮箱有效性
            for field in rules.get('email_fields', []):
                email = record.get(field)
                if email and not self._is_valid_email(email):
                    is_valid = False
                    record_issues.append(f"无效邮箱 {field}: {email}")

            # 检查电话有效性
            for field in rules.get('phone_fields', []):
                phone = record.get(field)
                if phone and not self._is_valid_phone(phone):
                    is_valid = False
                    record_issues.append(f"无效电话 {field}: {phone}")

            if is_valid:
                valid_count += 1
            else:
                validity_issues.extend(record_issues)

        validity_rate = valid_count / total_records
        quality_level = self._determine_quality_level(validity_rate, 0.95)

        return QualityMetric(
            name="数据有效性",
            metric_type=MetricType.VALIDITY,
            value=validity_rate,
            threshold=0.95,
            status=quality_level,
            description=f"数据有效性: {valid_count}/{total_records} 条记录有效",
            details={
                'valid_count': valid_count,
                'total_count': total_records,
                'validity_issues': validity_issues[:20]
            }
        )

    def _assess_consistency(self, data: List[Dict[str, Any]], entity_type: str) -> QualityMetric:
        """评估数据一致性"""
        total_records = len(data)
        if total_records == 0:
            return QualityMetric(
                name="数据一致性",
                metric_type=MetricType.CONSISTENCY,
                value=0.0,
                threshold=0.80,
                status=QualityLevel.CRITICAL,
                description="数据一致性评估",
                details={'error': '没有数据样本'}
            )

        consistency_score = 0.0
        consistency_issues = []

        # 检查货币单位一致性
        if entity_type == 'product':
            currencies = [record.get('currency', 'CNY') for record in data]
            currency_consistency = len(set(currencies)) / len(currencies) if currencies else 1.0
            consistency_score += (1.0 - currency_consistency) * 0.3  # 货币种类越少越好

        # 检查字段格式一致性
        format_fields = []
        if entity_type == 'product':
            format_fields = ['title', 'description']
        elif entity_type == 'supplier':
            format_fields = ['name', 'company_name']

        for field in format_fields:
            values = [str(record.get(field, '')) for record in data]
            # 检查长度分布的一致性
            lengths = [len(value) for value in values]
            if lengths:
                std_dev = statistics.stdev(lengths) if len(lengths) > 1 else 0
                mean_length = statistics.mean(lengths)
                # 标准差越小越一致
                field_consistency = 1.0 - min(std_dev / mean_length, 1.0) if mean_length > 0 else 1.0
                consistency_score += field_consistency * 0.2

        # 检查重复数据的一致性
        duplicates = self._find_potential_duplicates(data, entity_type)
        duplicate_penalty = len(duplicates) / total_records if total_records > 0 else 0
        consistency_score -= duplicate_penalty * 0.3

        # 确保分数在0-1之间
        consistency_score = max(0.0, min(1.0, consistency_score))
        quality_level = self._determine_quality_level(consistency_score, 0.80)

        return QualityMetric(
            name="数据一致性",
            metric_type=MetricType.CONSISTENCY,
            value=consistency_score,
            threshold=0.80,
            status=quality_level,
            description=f"数据一致性评分: {consistency_score:.2f}",
            details={
                'duplicate_count': len(duplicates),
                'duplicate_rate': duplicate_penalty,
                'duplicates': duplicates[:10]  # 只保留前10个重复
            }
        )

    def _assess_uniqueness(self, data: List[Dict[str, Any]], entity_type: str) -> QualityMetric:
        """评估数据唯一性"""
        total_records = len(data)
        if total_records == 0:
            return QualityMetric(
                name="数据唯一性",
                metric_type=MetricType.UNIQUENESS,
                value=0.0,
                threshold=0.95,
                status=QualityLevel.CRITICAL,
                description="数据唯一性评估",
                details={'error': '没有数据样本'}
            )

        # 检查关键字段的唯一性
        if entity_type == 'product':
            key_fields = ['source_id', 'title']
        else:  # supplier
            key_fields = ['source_id', 'name', 'phone']

        uniqueness_scores = []
        field_duplicates = {}

        for field in key_fields:
            values = [record.get(field) for record in data]
            value_counts = defaultdict(int)
            unique_values = set()

            for value in values:
                if value is not None:
                    value_counts[value] += 1
                    unique_values.add(value)

            # 计算唯一性比例
            duplicates = sum(count - 1 for count in value_counts.values() if count > 1)
            uniqueness_rate = (len(unique_values) - duplicates) / len(values) if values else 1.0
            uniqueness_scores.append(uniqueness_rate)

            # 记录重复值
            if duplicates > 0:
                field_duplicates[field] = [
                    {'value': value, 'count': count}
                    for value, count in value_counts.items()
                    if count > 1
                ]

        overall_uniqueness = statistics.mean(uniqueness_scores) if uniqueness_scores else 0.0
        quality_level = self._determine_quality_level(overall_uniqueness, 0.95)

        return QualityMetric(
            name="数据唯一性",
            metric_type=MetricType.UNIQUENESS,
            value=overall_uniqueness,
            threshold=0.95,
            status=quality_level,
            description=f"数据唯一性: {overall_uniqueness:.2f}",
            details={
                'field_scores': dict(zip(key_fields, uniqueness_scores)),
                'field_duplicates': field_duplicates
            }
        )

    def _is_field_filled(self, value: Any) -> bool:
        """检查字段是否已填写"""
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ''
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True

    def _is_valid_url(self, url: str) -> bool:
        """验证URL有效性"""
        if not url or not isinstance(url, str):
            return False
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱有效性"""
        if not email or not isinstance(email, str):
            return False
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.lower()))

    def _is_valid_phone(self, phone: str) -> bool:
        """验证电话有效性"""
        if not phone or not isinstance(phone, str):
            return False
        import re
        return bool(re.match(r'^\+?\d{7,15}$', phone))

    def _find_potential_duplicates(self, data: List[Dict[str, Any]], entity_type: str) -> List[Dict[str, Any]]:
        """查找潜在重复数据"""
        duplicates = []

        if entity_type == 'product':
            # 基于标题相似度查找重复
            titles = [(i, record.get('title', '')) for i, record in enumerate(data)]
            for i, title1 in titles:
                for j, title2 in titles[i+1:]:
                    similarity = self._calculate_text_similarity(title1, title2)
                    if similarity > 0.9:  # 高相似度
                        duplicates.append({
                            'type': 'title_similarity',
                            'indices': [i, j],
                            'similarity': similarity,
                            'values': [title1, title2]
                        })
        elif entity_type == 'supplier':
            # 基于名称和电话查找重复
            for i, record1 in enumerate(data):
                for j, record2 in enumerate(data[i+1:], i+1):
                    name1 = record1.get('name', '')
                    name2 = record2.get('name', '')
                    phone1 = record1.get('phone', '')
                    phone2 = record2.get('phone', '')

                    if name1 == name2 or (phone1 and phone1 == phone2):
                        duplicates.append({
                            'type': 'exact_match',
                            'indices': [i, j],
                            'fields': ['name' if name1 == name2 else 'phone'],
                            'values': [record1, record2]
                        })

        return duplicates

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """计算总体质量分数"""
        if not metrics:
            return 0.0

        # 根据指标类型分配权重
        weights = {
            MetricType.COMPLETENESS: 0.3,
            MetricType.ACCURACY: 0.25,
            MetricType.VALIDITY: 0.2,
            MetricType.CONSISTENCY: 0.15,
            MetricType.UNIQUENESS: 0.1
        }

        weighted_score = 0.0
        total_weight = 0.0

        for metric in metrics:
            weight = weights.get(metric.metric_type, 0.1)
            weighted_score += metric.value * weight
            total_weight += weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _determine_quality_level(self, score: float, threshold: float) -> QualityLevel:
        """确定质量等级"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= threshold:
            return QualityLevel.GOOD
        elif score >= threshold - 0.1:
            return QualityLevel.FAIR
        elif score >= threshold - 0.2:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL

    def _identify_quality_issues(self, metrics: List[QualityMetric]) -> List[Dict[str, Any]]:
        """识别质量问题"""
        issues = []

        for metric in metrics:
            if metric.status in [QualityLevel.POOR, QualityLevel.CRITICAL]:
                issue = {
                    'metric': metric.name,
                    'level': metric.status.value,
                    'score': metric.value,
                    'threshold': metric.threshold,
                    'description': metric.description,
                    'details': metric.details
                }
                issues.append(issue)

        return issues

    def _generate_recommendations(self, issues: List[Dict[str, Any]],
                                 metrics: List[QualityMetric]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for issue in issues:
            metric_name = issue['metric']
            level = issue['level']

            if metric_name == "数据完整性":
                if level == 'critical':
                    recommendations.append("立即补充必填字段，确保数据基础完整性")
                else:
                    recommendations.append("优先补充重要字段，提升数据完整性")

            elif metric_name == "数据准确性":
                recommendations.append("建立数据验证规则，修正异常值和超出范围的数据")

            elif metric_name == "数据有效性":
                recommendations.append("格式化检查URL、邮箱、电话等字段，确保格式正确")

            elif metric_name == "数据一致性":
                recommendations.append("标准化数据格式，清理重复和不一致的数据")

            elif metric_name == "数据唯一性":
                recommendations.append("实施去重策略，确保关键字段的唯一性")

        # 通用建议
        critical_issues = [issue for issue in issues if issue['level'] == 'critical']
        if critical_issues:
            recommendations.append("存在严重质量问题，建议立即进行数据清洗和修复")

        return recommendations

    def export_quality_report(self, report: QualityReport, output_file: str = None) -> str:
        """导出质量报告"""
        try:
            report_data = {
                'entity_type': report.entity_type,
                'overall_score': report.overall_score,
                'quality_level': report.quality_level.value,
                'measured_at': report.measured_at,
                'sample_size': report.sample_size,
                'metrics': [],
                'issues': report.issues,
                'recommendations': report.recommendations
            }

            # 转换指标数据
            for metric in report.metrics:
                metric_data = asdict(metric)
                metric_data['metric_type'] = metric.metric_type.value
                metric_data['status'] = metric.status.value
                report_data['metrics'].append(metric_data)

            report_content = json.dumps(report_data, ensure_ascii=False, indent=2)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                logger.info(f"质量报告已导出到: {output_file}")

            return report_content

        except Exception as e:
            logger.error(f"导出质量报告失败: {e}")
            raise