"""
数据验证机制
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    ERROR = "error"      # 严重错误，必须修复
    WARNING = "warning"  # 警告，建议修复
    INFO = "info"        # 信息，仅供参考


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    level: ValidationLevel
    field: str
    message: str
    value: Any = None
    suggestion: Optional[str] = None


class DataValidator:
    """数据验证器"""

    def __init__(self):
        """初始化验证器"""
        # 商品验证规则
        self.product_rules = {
            'required_fields': ['source_id', 'title'],
            'max_lengths': {
                'title': 500,
                'subtitle': 500,
                'description': 2000
            },
            'price_ranges': {
                'min': 0.01,
                'max': 1000000
            },
            'rating_range': {
                'min': 0.0,
                'max': 5.0
            }
        }

        # 供应商验证规则
        self.supplier_rules = {
            'required_fields': ['source_id', 'name'],
            'max_lengths': {
                'name': 200,
                'description': 1000,
                'company_name': 200
            }
        }

    def validate_product_data(self, product_data: Dict[str, Any]) -> List[ValidationResult]:
        """验证商品数据"""
        results = []

        try:
            # 验证必填字段
            results.extend(self._validate_required_fields(
                product_data, self.product_rules['required_fields']
            ))

            # 验证字段长度
            results.extend(self._validate_field_lengths(
                product_data, self.product_rules['max_lengths']
            ))

            # 验证价格信息
            results.extend(self._validate_price_info(product_data))

            # 验证统计信息
            results.extend(self._validate_statistics(product_data))

            # 验证媒体URL
            results.extend(self._validate_media_urls(product_data))

            # 验证分类信息
            results.extend(self._validate_category_info(product_data))

            # 验证规格参数
            results.extend(self._validate_specifications(product_data))

            # 计算整体有效性
            errors = [r for r in results if r.level == ValidationLevel.ERROR]
            is_valid = len(errors) == 0

            # 添加整体验证结果
            if not is_valid:
                results.insert(0, ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field="overall",
                    message=f"商品数据验证失败，存在 {len(errors)} 个错误",
                    suggestion="请修复所有错误项"
                ))
            else:
                warnings = [r for r in results if r.level == ValidationLevel.WARNING]
                if warnings:
                    results.insert(0, ValidationResult(
                        is_valid=True,
                        level=ValidationLevel.WARNING,
                        field="overall",
                        message=f"商品数据验证通过，存在 {len(warnings)} 个警告",
                        suggestion="建议修复警告项以提高数据质量"
                    ))

            return results

        except Exception as e:
            logger.error(f"商品数据验证异常: {e}")
            return [ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                field="validation",
                message=f"验证过程异常: {str(e)}",
                suggestion="请检查数据格式或联系技术支持"
            )]

    def validate_supplier_data(self, supplier_data: Dict[str, Any]) -> List[ValidationResult]:
        """验证供应商数据"""
        results = []

        try:
            # 验证必填字段
            results.extend(self._validate_required_fields(
                supplier_data, self.supplier_rules['required_fields']
            ))

            # 验证字段长度
            results.extend(self._validate_field_lengths(
                supplier_data, self.supplier_rules['max_lengths']
            ))

            # 验证联系方式
            results.extend(self._validate_contact_info(supplier_data))

            # 验证地址信息
            results.extend(self._validate_address_info(supplier_data))

            # 验证工商信息
            results.extend(self._validate_business_info(supplier_data))

            # 计算整体有效性
            errors = [r for r in results if r.level == ValidationLevel.ERROR]
            is_valid = len(errors) == 0

            # 添加整体验证结果
            if not is_valid:
                results.insert(0, ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field="overall",
                    message=f"供应商数据验证失败，存在 {len(errors)} 个错误",
                    suggestion="请修复所有错误项"
                ))
            else:
                warnings = [r for r in results if r.level == ValidationLevel.WARNING]
                if warnings:
                    results.insert(0, ValidationResult(
                        is_valid=True,
                        level=ValidationLevel.WARNING,
                        field="overall",
                        message=f"供应商数据验证通过，存在 {len(warnings)} 个警告",
                        suggestion="建议修复警告项以提高数据质量"
                    ))

            return results

        except Exception as e:
            logger.error(f"供应商数据验证异常: {e}")
            return [ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                field="validation",
                message=f"验证过程异常: {str(e)}",
                suggestion="请检查数据格式或联系技术支持"
            )]

    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> List[ValidationResult]:
        """验证必填字段"""
        results = []

        for field in required_fields:
            value = data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field=field,
                    message=f"必填字段 '{field}' 不能为空",
                    value=value,
                    suggestion=f"请提供有效的 {field} 值"
                ))

        return results

    def _validate_field_lengths(self, data: Dict[str, Any], max_lengths: Dict[str, int]) -> List[ValidationResult]:
        """验证字段长度"""
        results = []

        for field, max_length in max_lengths.items():
            value = data.get(field)
            if value and isinstance(value, str):
                length = len(value)
                if length > max_length:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field=field,
                        message=f"字段 '{field}' 长度 {length} 超过限制 {max_length}",
                        value=value,
                        suggestion=f"建议将字段长度控制在 {max_length} 字符以内"
                    ))

        return results

    def _validate_price_info(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证价格信息"""
        results = []

        # 验证最小价格
        price_min = data.get('price_min')
        if price_min is not None:
            try:
                price_min_decimal = Decimal(str(price_min))
                if price_min_decimal <= 0:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.ERROR,
                        field='price_min',
                        message=f"最小价格必须大于0: {price_min}",
                        value=price_min,
                        suggestion="请设置有效的最小价格"
                    ))
                elif price_min_decimal < Decimal(str(self.product_rules['price_ranges']['min'])):
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field='price_min',
                        message=f"最小价格过低: {price_min}",
                        value=price_min,
                        suggestion="请确认价格是否正确"
                    ))
                elif price_min_decimal > Decimal(str(self.product_rules['price_ranges']['max'])):
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field='price_min',
                        message=f"最小价格过高: {price_min}",
                        value=price_min,
                        suggestion="请确认价格是否正确"
                    ))
            except (InvalidOperation, ValueError):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='price_min',
                    message=f"最小价格格式无效: {price_min}",
                    value=price_min,
                    suggestion="请提供有效的数字格式价格"
                ))

        # 验证最大价格
        price_max = data.get('price_max')
        if price_max is not None:
            try:
                price_max_decimal = Decimal(str(price_max))
                if price_max_decimal <= 0:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.ERROR,
                        field='price_max',
                        message=f"最大价格必须大于0: {price_max}",
                        value=price_max,
                        suggestion="请设置有效的最大价格"
                    ))
            except (InvalidOperation, ValueError):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='price_max',
                    message=f"最大价格格式无效: {price_max}",
                    value=price_max,
                    suggestion="请提供有效的数字格式价格"
                ))

        # 验证价格范围逻辑
        if (price_min is not None and price_max is not None and
            isinstance(price_min, (int, float, Decimal)) and
            isinstance(price_max, (int, float, Decimal))):
            if price_min > price_max:
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='price_range',
                    message=f"最小价格不能大于最大价格: {price_min} > {price_max}",
                    value={'price_min': price_min, 'price_max': price_max},
                    suggestion="请调整价格范围"
                ))

        # 验证货币单位
        currency = data.get('currency')
        if currency and currency not in ['CNY', 'USD', 'EUR']:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='currency',
                message=f"不常见的货币单位: {currency}",
                value=currency,
                suggestion="建议使用标准货币单位 (CNY, USD, EUR)"
            ))

        return results

    def _validate_statistics(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证统计信息"""
        results = []

        # 验证销量
        sales_count = data.get('sales_count')
        if sales_count is not None:
            try:
                sales_int = int(sales_count)
                if sales_int < 0:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.ERROR,
                        field='sales_count',
                        message=f"销量不能为负数: {sales_count}",
                        value=sales_count,
                        suggestion="请设置有效的销量"
                    ))
                elif sales_int > 10000000:  # 1000万
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field='sales_count',
                        message=f"销量异常高: {sales_count}",
                        value=sales_count,
                        suggestion="请确认销量数据是否准确"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='sales_count',
                    message=f"销量格式无效: {sales_count}",
                    value=sales_count,
                    suggestion="请提供有效的整数格式销量"
                ))

        # 验证评论数
        review_count = data.get('review_count')
        if review_count is not None:
            try:
                review_int = int(review_count)
                if review_int < 0:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.ERROR,
                        field='review_count',
                        message=f"评论数不能为负数: {review_count}",
                        value=review_count,
                        suggestion="请设置有效的评论数"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='review_count',
                    message=f"评论数格式无效: {review_count}",
                    value=review_count,
                    suggestion="请提供有效的整数格式评论数"
                ))

        # 验证评分
        rating = data.get('rating')
        if rating is not None:
            try:
                rating_float = float(rating)
                min_rating = self.product_rules['rating_range']['min']
                max_rating = self.product_rules['rating_range']['max']
                if not (min_rating <= rating_float <= max_rating):
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.ERROR,
                        field='rating',
                        message=f"评分必须在 {min_rating} 到 {max_rating} 之间: {rating}",
                        value=rating,
                        suggestion=f"请设置 {min_rating} 到 {max_rating} 之间的评分"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='rating',
                    message=f"评分格式无效: {rating}",
                    value=rating,
                    suggestion="请提供有效的数字格式评分"
                ))

        return results

    def _validate_media_urls(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证媒体URL"""
        results = []

        # 验证主图URL
        main_image_url = data.get('main_image_url')
        if main_image_url and not self._is_valid_url(main_image_url):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='main_image_url',
                message=f"主图URL格式无效: {main_image_url}",
                value=main_image_url,
                suggestion="请提供有效的图片URL"
            ))

        # 验证详情图URL列表
        detail_images = data.get('detail_images', [])
        if detail_images:
            if not isinstance(detail_images, list):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='detail_images',
                    message="详情图必须是列表格式",
                    value=detail_images,
                    suggestion="请将详情图转换为列表格式"
                ))
            else:
                invalid_urls = []
                for i, url in enumerate(detail_images):
                    if not self._is_valid_url(url):
                        invalid_urls.append(i)

                if invalid_urls:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field='detail_images',
                        message=f"详情图中存在无效URL: 位置 {invalid_urls}",
                        value=detail_images,
                        suggestion="请检查并修复无效的图片URL"
                    ))

        # 验证视频URL
        video_url = data.get('video_url')
        if video_url and not self._is_valid_url(video_url):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='video_url',
                message=f"视频URL格式无效: {video_url}",
                value=video_url,
                suggestion="请提供有效的视频URL"
            ))

        return results

    def _validate_category_info(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证分类信息"""
        results = []

        # 验证分类ID
        category_id = data.get('category_id')
        if category_id and not isinstance(category_id, str):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='category_id',
                message=f"分类ID应为字符串格式: {category_id}",
                value=category_id,
                suggestion="请将分类ID转换为字符串格式"
            ))

        # 验证分类名称
        category_name = data.get('category_name')
        if category_name and len(category_name) > 200:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='category_name',
                message=f"分类名称过长: {len(category_name)} 字符",
                value=category_name,
                suggestion="建议将分类名称控制在200字符以内"
            ))

        return results

    def _validate_specifications(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证规格参数"""
        results = []

        specifications = data.get('specifications')
        if specifications is not None:
            if not isinstance(specifications, dict):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    field='specifications',
                    message="规格参数必须是字典格式",
                    value=specifications,
                    suggestion="请将规格参数转换为字典格式"
                ))
            else:
                # 验证规格参数数量
                if len(specifications) > 50:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field='specifications',
                        message=f"规格参数过多: {len(specifications)} 个",
                        value=specifications,
                        suggestion="建议精简规格参数，保留最重要的信息"
                    ))

                # 验证规格参数键值
                for key, value in specifications.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        results.append(ValidationResult(
                            is_valid=False,
                            level=ValidationLevel.WARNING,
                            field='specifications',
                            message=f"规格参数键值应为字符串: {key}: {value}",
                            value={'key': key, 'value': value},
                            suggestion="请确保规格参数的键和值都是字符串格式"
                        ))

        return results

    def _validate_contact_info(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证联系方式"""
        results = []

        # 验证电话
        phone = data.get('phone')
        if phone and not self._is_valid_phone(phone):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='phone',
                message=f"电话号码格式无效: {phone}",
                value=phone,
                suggestion="请提供有效的电话号码格式"
            ))

        # 验证邮箱
        email = data.get('email')
        if email and not self._is_valid_email(email):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='email',
                message=f"邮箱格式无效: {email}",
                value=email,
                suggestion="请提供有效的邮箱地址格式"
            ))

        # 验证QQ
        qq = data.get('qq')
        if qq and not self._is_valid_qq(qq):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='qq',
                message=f"QQ号码格式无效: {qq}",
                value=qq,
                suggestion="请提供有效的QQ号码格式"
            ))

        return results

    def _validate_address_info(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证地址信息"""
        results = []

        # 验证地址完整性
        province = data.get('province')
        city = data.get('city')
        address = data.get('address')

        if province and not city:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.INFO,
                field='address',
                message="有省份信息但缺少城市信息",
                value={'province': province, 'city': city, 'address': address},
                suggestion="建议补充城市信息"
            ))

        if city and not province:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.INFO,
                field='address',
                message="有城市信息但缺少省份信息",
                value={'province': province, 'city': city, 'address': address},
                suggestion="建议补充省份信息"
            ))

        return results

    def _validate_business_info(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """验证工商信息"""
        results = []

        # 验证成立日期
        established_date = data.get('established_date')
        if established_date and not self._is_valid_date(established_date):
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                field='established_date',
                message=f"成立日期格式无效: {established_date}",
                value=established_date,
                suggestion="请提供 YYYY-MM-DD 格式的日期"
            ))

        # 验证注册资本
        registered_capital = data.get('registered_capital')
        if registered_capital:
            try:
                capital_int = int(registered_capital)
                if capital_int <= 0:
                    results.append(ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        field='registered_capital',
                        message=f"注册资本必须大于0: {registered_capital}",
                        value=registered_capital,
                        suggestion="请设置有效的注册资本"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    field='registered_capital',
                    message=f"注册资本格式无效: {registered_capital}",
                    value=registered_capital,
                    suggestion="请提供有效的数字格式注册资本"
                ))

        return results

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

    def _is_valid_phone(self, phone: str) -> bool:
        """验证电话号码"""
        if not phone or not isinstance(phone, str):
            return False
        import re
        return bool(re.match(r'^\+?\d{7,15}$', phone))

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱地址"""
        if not email or not isinstance(email, str):
            return False
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.lower()))

    def _is_valid_qq(self, qq: str) -> bool:
        """验证QQ号码"""
        if not qq or not isinstance(qq, str):
            return False
        import re
        return bool(re.match(r'^[1-9]\d{4,11}$', qq))

    def _is_valid_date(self, date_str: str) -> bool:
        """验证日期格式"""
        if not date_str or not isinstance(date_str, str):
            return False
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """获取验证结果摘要"""
        summary = {
            'is_valid': True,
            'total_count': len(results),
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'field_issues': {},
            'suggestions': []
        }

        for result in results:
            # 统计各级别数量
            if result.level == ValidationLevel.ERROR:
                summary['error_count'] += 1
                summary['is_valid'] = False
            elif result.level == ValidationLevel.WARNING:
                summary['warning_count'] += 1
            elif result.level == ValidationLevel.INFO:
                summary['info_count'] += 1

            # 统计字段问题
            field = result.field
            if field not in summary['field_issues']:
                summary['field_issues'][field] = []
            summary['field_issues'][field].append({
                'level': result.level.value,
                'message': result.message
            })

            # 收集建议
            if result.suggestion:
                summary['suggestions'].append(result.suggestion)

        # 去重建议
        summary['suggestions'] = list(set(summary['suggestions']))

        return summary