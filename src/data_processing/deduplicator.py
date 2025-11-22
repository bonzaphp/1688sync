"""
数据去重算法
"""
import hashlib
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """重复数据组"""
    group_id: str
    records: List[Dict[str, Any]]
    similarity_score: float
    duplicate_fields: List[str]
    master_record: Optional[Dict[str, Any]] = None


class DataDeduplicator:
    """数据去重器"""

    def __init__(self):
        """初始化去重器"""
        # 商品去重配置
        self.product_config = {
            'similarity_threshold': 0.85,  # 相似度阈值
            'key_fields': ['title', 'price_min', 'price_max'],
            'fuzzy_fields': ['title', 'description'],
            'exact_fields': ['source_id'],
            'weight_config': {
                'title': 0.4,
                'price_min': 0.3,
                'price_max': 0.2,
                'category_name': 0.1
            }
        }

        # 供应商去重配置
        self.supplier_config = {
            'similarity_threshold': 0.80,
            'key_fields': ['name', 'phone', 'company_name'],
            'fuzzy_fields': ['name', 'description'],
            'exact_fields': ['source_id'],
            'weight_config': {
                'name': 0.4,
                'phone': 0.3,
                'company_name': 0.2,
                'address': 0.1
            }
        }

    def find_duplicate_products(self, products: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """查找重复商品"""
        try:
            logger.info(f"开始查找重复商品，共 {len(products)} 条记录")

            # 按照精确字段分组
            exact_groups = self._group_by_exact_fields(
                products, self.product_config['exact_fields']
            )

            duplicate_groups = []

            for group_key, group_products in exact_groups.items():
                if len(group_products) <= 1:
                    continue

                # 在组内进行模糊匹配
                group_duplicates = self._find_fuzzy_duplicates(
                    group_products, self.product_config
                )
                duplicate_groups.extend(group_duplicates)

            logger.info(f"找到 {len(duplicate_groups)} 组重复商品")
            return duplicate_groups

        except Exception as e:
            logger.error(f"查找重复商品失败: {e}")
            raise

    def find_duplicate_suppliers(self, suppliers: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """查找重复供应商"""
        try:
            logger.info(f"开始查找重复供应商，共 {len(suppliers)} 条记录")

            # 按照精确字段分组
            exact_groups = self._group_by_exact_fields(
                suppliers, self.supplier_config['exact_fields']
            )

            duplicate_groups = []

            for group_key, group_suppliers in exact_groups.items():
                if len(group_suppliers) <= 1:
                    continue

                # 在组内进行模糊匹配
                group_duplicates = self._find_fuzzy_duplicates(
                    group_suppliers, self.supplier_config
                )
                duplicate_groups.extend(group_duplicates)

            logger.info(f"找到 {len(duplicate_groups)} 组重复供应商")
            return duplicate_groups

        except Exception as e:
            logger.error(f"查找重复供应商失败: {e}")
            raise

    def remove_duplicate_products(self, duplicate_groups: List[DuplicateGroup],
                                 strategy: str = 'keep_best') -> List[int]:
        """移除重复商品"""
        removed_ids = []

        try:
            for group in duplicate_groups:
                if strategy == 'keep_best':
                    master_id = self._select_best_product(group)
                elif strategy == 'keep_first':
                    master_id = group.records[0].get('id')
                elif strategy == 'keep_last':
                    master_id = group.records[-1].get('id')
                else:
                    master_id = self._select_best_product(group)

                # 标记其他记录为重复
                for record in group.records:
                    record_id = record.get('id')
                    if record_id and record_id != master_id:
                        removed_ids.append(record_id)
                        # 这里可以添加实际的删除逻辑
                        logger.debug(f"标记重复商品 {record_id}")

            logger.info(f"标记 {len(removed_ids)} 条重复商品")
            return removed_ids

        except Exception as e:
            logger.error(f"移除重复商品失败: {e}")
            raise

    def remove_duplicate_suppliers(self, duplicate_groups: List[DuplicateGroup],
                                  strategy: str = 'keep_best') -> List[int]:
        """移除重复供应商"""
        removed_ids = []

        try:
            for group in duplicate_groups:
                if strategy == 'keep_best':
                    master_id = self._select_best_supplier(group)
                elif strategy == 'keep_first':
                    master_id = group.records[0].get('id')
                elif strategy == 'keep_last':
                    master_id = group.records[-1].get('id')
                else:
                    master_id = self._select_best_supplier(group)

                # 标记其他记录为重复
                for record in group.records:
                    record_id = record.get('id')
                    if record_id and record_id != master_id:
                        removed_ids.append(record_id)
                        # 这里可以添加实际的删除逻辑
                        logger.debug(f"标记重复供应商 {record_id}")

            logger.info(f"标记 {len(removed_ids)} 条重复供应商")
            return removed_ids

        except Exception as e:
            logger.error(f"移除重复供应商失败: {e}")
            raise

    def _group_by_exact_fields(self, records: List[Dict[str, Any]],
                              exact_fields: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """按照精确字段分组"""
        groups = defaultdict(list)

        for record in records:
            # 创建分组键
            key_parts = []
            for field in exact_fields:
                value = record.get(field, '')
                if value is not None:
                    key_parts.append(str(value))
                else:
                    key_parts.append('')

            group_key = '|'.join(key_parts)
            groups[group_key].append(record)

        return dict(groups)

    def _find_fuzzy_duplicates(self, records: List[Dict[str, Any]],
                              config: Dict[str, Any]) -> List[DuplicateGroup]:
        """在记录组内查找模糊重复"""
        duplicate_groups = []
        processed_indices = set()

        for i, record1 in enumerate(records):
            if i in processed_indices:
                continue

            current_group = [record1]
            processed_indices.add(i)

            for j, record2 in enumerate(records[i+1:], i+1):
                if j in processed_indices:
                    continue

                similarity = self._calculate_similarity(record1, record2, config)

                if similarity >= config['similarity_threshold']:
                    current_group.append(record2)
                    processed_indices.add(j)

            if len(current_group) > 1:
                # 创建重复组
                group_id = self._generate_group_id(current_group)
                duplicate_fields = self._find_duplicate_fields(current_group, config)

                duplicate_group = DuplicateGroup(
                    group_id=group_id,
                    records=current_group,
                    similarity_score=similarity,
                    duplicate_fields=duplicate_fields
                )
                duplicate_groups.append(duplicate_group)

        return duplicate_groups

    def _calculate_similarity(self, record1: Dict[str, Any], record2: Dict[str, Any],
                            config: Dict[str, Any]) -> float:
        """计算两条记录的相似度"""
        total_score = 0.0
        total_weight = 0.0

        weight_config = config['weight_config']
        fuzzy_fields = config['fuzzy_fields']

        for field, weight in weight_config.items():
            value1 = record1.get(field, '')
            value2 = record2.get(field, '')

            if not value1 or not value2:
                continue

            if field in fuzzy_fields:
                # 模糊匹配
                similarity = self._calculate_text_similarity(str(value1), str(value2))
            else:
                # 精确匹配
                similarity = 1.0 if str(value1) == str(value2) else 0.0

            total_score += similarity * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return total_score / total_weight

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 预处理文本
        text1 = self._preprocess_text(text1)
        text2 = self._preprocess_text(text2)

        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, text1, text2).ratio()

        # 对完全相同的文本给予更高权重
        if text1 == text2:
            similarity = min(1.0, similarity * 1.1)

        return similarity

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        if not text:
            return ""

        # 转换为小写
        text = text.lower()

        # 移除特殊字符，保留中文、英文、数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', text)

        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _generate_group_id(self, records: List[Dict[str, Any]]) -> str:
        """生成重复组ID"""
        # 使用记录的ID或关键字段生成哈希
        key_parts = []
        for record in records:
            record_id = record.get('id') or record.get('source_id') or ''
            key_parts.append(str(record_id))

        key_string = '|'.join(sorted(key_parts))
        return hashlib.md5(key_string.encode()).hexdigest()[:16]

    def _find_duplicate_fields(self, records: List[Dict[str, Any]],
                              config: Dict[str, Any]) -> List[str]:
        """找出重复的字段"""
        duplicate_fields = []
        key_fields = config['key_fields']

        for field in key_fields:
            values = set()
            for record in records:
                value = record.get(field)
                if value is not None:
                    values.add(str(value))

            # 如果所有记录的该字段值都相同，则认为是重复字段
            if len(values) == 1:
                duplicate_fields.append(field)

        return duplicate_fields

    def _select_best_product(self, group: DuplicateGroup) -> Optional[int]:
        """选择最佳商品记录"""
        if not group.records:
            return None

        best_record = None
        best_score = -1

        for record in group.records:
            score = self._calculate_product_score(record)
            if score > best_score:
                best_score = score
                best_record = record

        # 设置主记录
        group.master_record = best_record
        return best_record.get('id') if best_record else None

    def _calculate_product_score(self, record: Dict[str, Any]) -> float:
        """计算商品记录质量分数"""
        score = 0.0

        # 基础信息完整性 (30%)
        basic_fields = ['title', 'description', 'main_image_url']
        basic_complete = sum(1 for field in basic_fields if record.get(field))
        score += (basic_complete / len(basic_fields)) * 30

        # 价格信息完整性 (20%)
        price_fields = ['price_min', 'price_max']
        price_complete = sum(1 for field in price_fields if record.get(field))
        score += (price_complete / len(price_fields)) * 20

        # 统计信息 (20%)
        stats_fields = ['sales_count', 'review_count', 'rating']
        stats_complete = sum(1 for field in stats_fields if record.get(field))
        score += (stats_complete / len(stats_fields)) * 20

        # 媒体信息 (15%)
        media_fields = ['main_image_url', 'detail_images']
        media_complete = sum(1 for field in media_fields if record.get(field))
        score += (media_complete / len(media_fields)) * 15

        # 规格参数 (15%)
        specs = record.get('specifications')
        if specs and isinstance(specs, dict) and len(specs) > 0:
            score += 15

        return score

    def _select_best_supplier(self, group: DuplicateGroup) -> Optional[int]:
        """选择最佳供应商记录"""
        if not group.records:
            return None

        best_record = None
        best_score = -1

        for record in group.records:
            score = self._calculate_supplier_score(record)
            if score > best_score:
                best_score = score
                best_record = record

        # 设置主记录
        group.master_record = best_record
        return best_record.get('id') if best_record else None

    def _calculate_supplier_score(self, record: Dict[str, Any]) -> float:
        """计算供应商记录质量分数"""
        score = 0.0

        # 基础信息完整性 (30%)
        basic_fields = ['name', 'description', 'company_name']
        basic_complete = sum(1 for field in basic_fields if record.get(field))
        score += (basic_complete / len(basic_fields)) * 30

        # 联系方式完整性 (25%)
        contact_fields = ['phone', 'email', 'qq', 'wechat']
        contact_complete = sum(1 for field in contact_fields if record.get(field))
        score += (contact_complete / len(contact_fields)) * 25

        # 地址信息完整性 (20%)
        address_fields = ['province', 'city', 'address']
        address_complete = sum(1 for field in address_fields if record.get(field))
        score += (address_complete / len(address_fields)) * 20

        # 工商信息完整性 (15%)
        business_fields = ['established_date', 'registered_capital']
        business_complete = sum(1 for field in business_fields if record.get(field))
        score += (business_complete / len(business_fields)) * 15

        # 认证信息 (10%)
        certifications = record.get('certifications')
        if certifications and isinstance(certifications, list) and len(certifications) > 0:
            score += 10

        return score

    def get_deduplication_statistics(self, duplicate_groups: List[DuplicateGroup]) -> Dict[str, Any]:
        """获取去重统计信息"""
        if not duplicate_groups:
            return {
                'total_groups': 0,
                'total_records': 0,
                'duplicate_records': 0,
                'unique_records': 0,
                'average_similarity': 0.0,
                'duplicate_fields': {}
            }

        total_records = sum(len(group.records) for group in duplicate_groups)
        duplicate_records = total_records - len(duplicate_groups)
        average_similarity = sum(group.similarity_score for group in duplicate_groups) / len(duplicate_groups)

        # 统计重复字段
        field_count = defaultdict(int)
        for group in duplicate_groups:
            for field in group.duplicate_fields:
                field_count[field] += 1

        return {
            'total_groups': len(duplicate_groups),
            'total_records': total_records,
            'duplicate_records': duplicate_records,
            'unique_records': len(duplicate_groups),
            'duplicate_ratio': duplicate_records / total_records if total_records > 0 else 0,
            'average_similarity': round(average_similarity, 3),
            'duplicate_fields': dict(field_count)
        }

    def export_duplicate_report(self, duplicate_groups: List[DuplicateGroup],
                               output_file: str = None) -> str:
        """导出去重报告"""
        import json
        from datetime import datetime

        report = {
            'generated_at': datetime.now().isoformat(),
            'statistics': self.get_deduplication_statistics(duplicate_groups),
            'duplicate_groups': []
        }

        for group in duplicate_groups:
            group_data = {
                'group_id': group.group_id,
                'similarity_score': round(group.similarity_score, 3),
                'duplicate_fields': group.duplicate_fields,
                'record_count': len(group.records),
                'records': []
            }

            for i, record in enumerate(group.records):
                record_summary = {
                    'index': i,
                    'id': record.get('id'),
                    'source_id': record.get('source_id'),
                    'title': record.get('title', record.get('name', '')),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at')
                }
                group_data['records'].append(record_summary)

            if group.master_record:
                group_data['master_record_id'] = group.master_record.get('id')

            report['duplicate_groups'].append(group_data)

        report_content = json.dumps(report, ensure_ascii=False, indent=2)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"去重报告已导出到: {output_file}")

        return report_content