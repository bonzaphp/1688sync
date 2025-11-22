"""
数据清洗和标准化模块
"""
import re
import logging
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗和标准化处理器"""

    def __init__(self):
        """初始化数据清洗器"""
        self.price_patterns = [
            r'¥(\d+\.?\d*)',
            r'(\d+\.?\d*)元',
            r'RMB\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*元'
        ]

        self.maq_patterns = [
            r'(\d+)\s*起',
            r'最小起订量[:：]\s*(\d+)',
            r'MOQ[:：]\s*(\d+)',
            r'起订量[:：]\s*(\d+)'
        ]

        # 常见单位标准化映射
        self.unit_mapping = {
            '个': 'piece',
            '件': 'piece',
            '只': 'piece',
            '支': 'piece',
            '张': 'piece',
            '片': 'piece',
            '条': 'piece',
            '根': 'piece',
            '套': 'set',
            '对': 'pair',
            '双': 'pair',
            '公斤': 'kg',
            '千克': 'kg',
            '斤': 'jin',  # 0.5kg
            '克': 'g',
            '米': 'meter',
            '公尺': 'meter',
            '厘米': 'cm',
            '毫米': 'mm',
            '升': 'liter',
            '毫升': 'ml',
            '吨': 'ton'
        }

    def clean_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗商品数据"""
        try:
            cleaned_data = {}

            # 清洗基本信息
            cleaned_data['title'] = self._clean_text(raw_data.get('title', ''))
            cleaned_data['subtitle'] = self._clean_text(raw_data.get('subtitle', ''))
            cleaned_data['description'] = self._clean_html(raw_data.get('description', ''))

            # 清洗价格信息
            price_info = self._clean_price_info(raw_data)
            cleaned_data.update(price_info)

            # 清洗订货信息
            order_info = self._clean_order_info(raw_data)
            cleaned_data.update(order_info)

            # 清洗媒体信息
            media_info = self._clean_media_info(raw_data)
            cleaned_data.update(media_info)

            # 清洗规格参数
            specs = self._clean_specifications(raw_data.get('specifications', {}))
            cleaned_data['specifications'] = specs

            # 清洗属性
            attributes = self._clean_attributes(raw_data.get('attributes', {}))
            cleaned_data['attributes'] = attributes

            # 清洗分类信息
            category_info = self._clean_category_info(raw_data)
            cleaned_data.update(category_info)

            # 清洗统计信息
            stats_info = self._clean_statistics(raw_data)
            cleaned_data.update(stats_info)

            # 保留原始ID
            cleaned_data['source_id'] = str(raw_data.get('source_id', ''))

            logger.debug(f"商品数据清洗完成: {cleaned_data.get('title', 'Unknown')}")
            return cleaned_data

        except Exception as e:
            logger.error(f"清洗商品数据失败: {e}")
            raise

    def clean_supplier_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗供应商数据"""
        try:
            cleaned_data = {}

            # 清洗基本信息
            cleaned_data['name'] = self._clean_text(raw_data.get('name', ''))
            cleaned_data['description'] = self._clean_text(raw_data.get('description', ''))

            # 清洗联系方式
            contact_info = self._clean_contact_info(raw_data)
            cleaned_data.update(contact_info)

            # 清洗地址信息
            address_info = self._clean_address_info(raw_data)
            cleaned_data.update(address_info)

            # 清洗工商信息
            business_info = self._clean_business_info(raw_data)
            cleaned_data.update(business_info)

            # 清洗认证信息
            certification_info = self._clean_certification_info(raw_data)
            cleaned_data.update(certification_info)

            # 保留原始ID
            cleaned_data['source_id'] = str(raw_data.get('source_id', ''))

            logger.debug(f"供应商数据清洗完成: {cleaned_data.get('name', 'Unknown')}")
            return cleaned_data

        except Exception as e:
            logger.error(f"清洗供应商数据失败: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """清洗文本内容"""
        if not text:
            return ""

        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text.strip())

        # 移除特殊字符（保留中文、英文、数字、常用标点）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?()（）。，！？：:]', '', text)

        # 限制长度
        if len(text) > 500:
            text = text[:500] + "..."

        return text

    def _clean_html(self, html_content: str) -> str:
        """清洗HTML内容"""
        if not html_content:
            return ""

        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html_content)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text.strip())

        # 限制长度
        if len(text) > 2000:
            text = text[:2000] + "..."

        return text

    def _clean_price_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗价格信息"""
        price_info = {}

        # 尝试从不同字段提取价格
        price_text = (
            raw_data.get('price_text', '') or
            raw_data.get('price_range', '') or
            str(raw_data.get('price_min', '')) + '-' + str(raw_data.get('price_max', ''))
        )

        # 提取价格数值
        prices = self._extract_prices(price_text)
        if prices:
            price_info['price_min'] = Decimal(str(min(prices)))
            price_info['price_max'] = Decimal(str(max(prices)))
        else:
            # 直接从字段获取
            try:
                if raw_data.get('price_min'):
                    price_info['price_min'] = Decimal(str(raw_data['price_min']))
                if raw_data.get('price_max'):
                    price_info['price_max'] = Decimal(str(raw_data['price_max']))
            except (InvalidOperation, ValueError):
                pass

        # 标准化货币单位
        currency = raw_data.get('currency', 'CNY')
        price_info['currency'] = self._standardize_currency(currency)

        return price_info

    def _extract_prices(self, price_text: str) -> List[float]:
        """从文本中提取价格"""
        prices = []

        for pattern in self.price_patterns:
            matches = re.findall(pattern, price_text)
            for match in matches:
                try:
                    price = float(match)
                    if 0 < price < 1000000:  # 合理价格范围
                        prices.append(price)
                except ValueError:
                    continue

        return prices

    def _standardize_currency(self, currency: str) -> str:
        """标准化货币单位"""
        currency = currency.upper().strip()
        currency_mapping = {
            'RMB': 'CNY',
            'YUAN': 'CNY',
            '元': 'CNY',
            '￥': 'CNY',
            'USD': 'USD',
            '$': 'USD',
            'EUR': 'EUR',
            '€': 'EUR'
        }
        return currency_mapping.get(currency, 'CNY')

    def _clean_order_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗订货信息"""
        order_info = {}

        # 提取最小起订量
        moq_text = (
            raw_data.get('moq_text', '') or
            raw_data.get('order_info', '') or
            str(raw_data.get('moq', ''))
        )

        moq = self._extract_moq(moq_text)
        if moq:
            order_info['moq'] = moq

        # 标准化价格单位
        unit = raw_data.get('price_unit', '')
        if unit:
            order_info['price_unit'] = self._standardize_unit(unit)

        return order_info

    def _extract_moq(self, moq_text: str) -> Optional[int]:
        """从文本中提取最小起订量"""
        for pattern in self.maq_patterns:
            match = re.search(pattern, moq_text)
            if match:
                try:
                    moq = int(match.group(1))
                    if 0 < moq < 1000000:  # 合理范围
                        return moq
                except ValueError:
                    continue
        return None

    def _standardize_unit(self, unit: str) -> str:
        """标准化单位"""
        unit = unit.lower().strip()
        return self.unit_mapping.get(unit, unit)

    def _clean_media_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗媒体信息"""
        media_info = {}

        # 清洗主图URL
        main_image = raw_data.get('main_image_url', '')
        if main_image and self._is_valid_url(main_image):
            media_info['main_image_url'] = main_image

        # 清洗详情图
        detail_images = raw_data.get('detail_images', [])
        if isinstance(detail_images, str):
            # 如果是字符串，尝试解析为列表
            detail_images = [img.strip() for img in detail_images.split(',') if img.strip()]

        valid_images = []
        for img in detail_images:
            if self._is_valid_url(img):
                valid_images.append(img)

        media_info['detail_images'] = valid_images[:10]  # 限制数量

        # 清洗视频URL
        video_url = raw_data.get('video_url', '')
        if video_url and self._is_valid_url(video_url):
            media_info['video_url'] = video_url

        return media_info

    def _is_valid_url(self, url: str) -> bool:
        """验证URL有效性"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _clean_specifications(self, specs: Union[Dict, List, str]) -> Dict[str, str]:
        """清洗规格参数"""
        if isinstance(specs, str):
            # 尝试解析字符串为字典
            try:
                import json
                specs = json.loads(specs)
            except:
                return {}

        if isinstance(specs, list):
            # 将列表转换为字典
            cleaned_specs = {}
            for spec in specs:
                if isinstance(spec, dict):
                    cleaned_specs.update(spec)
                elif isinstance(spec, str) and ':' in spec:
                    key, value = spec.split(':', 1)
                    cleaned_specs[key.strip()] = value.strip()
            return cleaned_specs

        if isinstance(specs, dict):
            cleaned_specs = {}
            for key, value in specs.items():
                clean_key = self._clean_text(str(key))
                clean_value = self._clean_text(str(value))
                if clean_key and clean_value:
                    cleaned_specs[clean_key] = clean_value
            return cleaned_specs

        return {}

    def _clean_attributes(self, attributes: Union[Dict, List, str]) -> Dict[str, str]:
        """清洗商品属性"""
        return self._clean_specifications(attributes)

    def _clean_category_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗分类信息"""
        category_info = {}

        category_id = raw_data.get('category_id', '')
        if category_id:
            category_info['category_id'] = str(category_id).strip()

        category_name = raw_data.get('category_name', '')
        if category_name:
            category_info['category_name'] = self._clean_text(category_name)

        return category_info

    def _clean_statistics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗统计信息"""
        stats_info = {}

        # 清洗销量
        try:
            sales_count = int(raw_data.get('sales_count', 0))
            stats_info['sales_count'] = max(0, sales_count)
        except (ValueError, TypeError):
            stats_info['sales_count'] = 0

        # 清洗评论数
        try:
            review_count = int(raw_data.get('review_count', 0))
            stats_info['review_count'] = max(0, review_count)
        except (ValueError, TypeError):
            stats_info['review_count'] = 0

        # 清洗评分
        try:
            rating = float(raw_data.get('rating', 0))
            stats_info['rating'] = Decimal(str(min(5.0, max(0.0, rating))))
        except (ValueError, TypeError):
            stats_info['rating'] = None

        return stats_info

    def _clean_contact_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗联系方式"""
        contact_info = {}

        # 清洗电话
        phone = raw_data.get('phone', '')
        if phone:
            contact_info['phone'] = self._clean_phone(phone)

        # 清洗邮箱
        email = raw_data.get('email', '')
        if email:
            contact_info['email'] = self._clean_email(email)

        # 清洗QQ
        qq = raw_data.get('qq', '')
        if qq:
            contact_info['qq'] = self._clean_qq(qq)

        # 清洗微信
        wechat = raw_data.get('wechat', '')
        if wechat:
            contact_info['wechat'] = self._clean_text(wechat)

        return contact_info

    def _clean_phone(self, phone: str) -> str:
        """清洗电话号码"""
        # 移除非数字字符，保留+号
        phone = re.sub(r'[^\d+]', '', phone)

        # 验证电话号码格式
        if re.match(r'^\+?\d{7,15}$', phone):
            return phone
        return ""

    def _clean_email(self, email: str) -> str:
        """清洗邮箱地址"""
        email = email.strip().lower()
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email
        return ""

    def _clean_qq(self, qq: str) -> str:
        """清洗QQ号码"""
        qq = re.sub(r'[^\d]', '', qq)
        if re.match(r'^[1-9]\d{4,11}$', qq):
            return qq
        return ""

    def _clean_address_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗地址信息"""
        address_info = {}

        # 清洗省份
        province = raw_data.get('province', '')
        if province:
            address_info['province'] = self._clean_text(province)

        # 清洗城市
        city = raw_data.get('city', '')
        if city:
            address_info['city'] = self._clean_text(city)

        # 清洗详细地址
        address = raw_data.get('address', '')
        if address:
            address_info['address'] = self._clean_text(address)

        return address_info

    def _clean_business_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗工商信息"""
        business_info = {}

        # 清洗公司名称
        company_name = raw_data.get('company_name', '')
        if company_name:
            business_info['company_name'] = self._clean_text(company_name)

        # 清洗成立时间
        established_date = raw_data.get('established_date', '')
        if established_date:
            business_info['established_date'] = self._clean_date(established_date)

        # 清洗注册资本
        registered_capital = raw_data.get('registered_capital', '')
        if registered_capital:
            business_info['registered_capital'] = self._clean_capital(registered_capital)

        return business_info

    def _clean_date(self, date_str: str) -> Optional[str]:
        """清洗日期"""
        try:
            # 尝试解析各种日期格式
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y年%m月%d日',
                '%Y.%m.%d'
            ]

            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        except Exception:
            pass

        return None

    def _clean_capital(self, capital_str: str) -> Optional[str]:
        """清洗注册资本"""
        # 提取数字和单位
        match = re.search(r'([\d.]+)\s*([万千亿]?)元', capital_str)
        if match:
            number = float(match.group(1))
            unit = match.group(2)

            # 转换单位
            multiplier = {'万': 10000, '千': 1000, '亿': 100000000, '': 1}
            capital = number * multiplier.get(unit, 1)

            return str(int(capital))

        return None

    def _clean_certification_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗认证信息"""
        cert_info = {}

        # 清洗认证列表
        certifications = raw_data.get('certifications', [])
        if isinstance(certifications, str):
            certifications = [cert.strip() for cert in certifications.split(',') if cert.strip()]

        clean_certs = []
        for cert in certifications:
            clean_cert = self._clean_text(str(cert))
            if clean_cert:
                clean_certs.append(clean_cert)

        cert_info['certifications'] = clean_certs

        return cert_info