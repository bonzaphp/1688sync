"""
1688商品爬虫
"""
import re
import json
import time
import random
from typing import Any, Dict, List, Optional

import scrapy
from scrapy.http import Response, Request
from scrapy.selector import Selector
from scrapy.exceptions import CloseSpider

from ..items import ProductItem
from ...config import settings


class Product1688Spider(scrapy.Spider):
    """1688商品爬虫"""

    name = "1688_products"
    allowed_domains = ["1688.com"]
    start_urls = [
        "https://www.1688.com/"
    ]

    def __init__(self, category: Optional[str] = None, keyword: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        self.keyword = keyword
        self.base_url = settings.base_url
        self.request_count = 0
        self.max_requests = 1000  # 最大请求数限制

    def start_requests(self):
        """开始请求"""
        if self.keyword:
            # 如果指定了关键词，从搜索页面开始
            search_url = f"{self.base_url}/search/search.html"
            params = {
                'keywords': self.keyword,
                'beginPage': 1,
                'pageSize': 60,
                'sortType': 'saturationIndustry',  # 按综合排序
            }

            url = f"{search_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
            yield Request(
                url=url,
                callback=self.parse_search,
                meta={"keyword": self.keyword, "page": 1}
            )
        elif self.category:
            # 如果指定了分类，从分类页面开始
            category_url = f"{self.base_url}/chanpin/{self.category}.html"
            yield Request(
                url=category_url,
                callback=self.parse_category,
                meta={"category": self.category}
            )
        else:
            # 否则从首页开始，获取热门分类
            yield Request(
                url=self.start_urls[0],
                callback=self.parse_homepage
            )

    def parse_homepage(self, response: Response):
        """解析首页，获取热门分类和推荐商品"""
        selector = Selector(response)

        # 查找热门分类链接（选择器根据实际页面结构调整）
        category_selectors = [
            '.sm-widget-market .sm-offer-title a',
            '.category-list a[href*="chanpin"]',
            '.nav-category a[href*="chanpin"]',
            '.s-market-card a[href*="chanpin"]'
        ]

        for selector_text in category_selectors:
            category_links = selector.css(selector_text)
            if category_links:
                break

        for link in category_links[:10]:  # 限制数量避免过多请求
            category_url = link.css('::attr(href)').get()
            category_name = link.css('::text').get()

            if category_url and category_name:
                yield Request(
                    url=response.urljoin(category_url),
                    callback=self.parse_category,
                    meta={"category": category_name.strip()}
                )

        # 同时查找首页推荐商品
        yield from self.parse_product_list(response, "首页推荐")

    def parse_search(self, response: Response):
        """解析搜索结果页面"""
        keyword = response.meta.get('keyword', '')
        page = response.meta.get('page', 1)

        # 解析商品列表
        yield from self.parse_product_list(response, f"搜索:{keyword}")

        # 查找下一页链接
        next_selectors = [
            '.ui-page-next a::attr(href)',
            '.next-page a::attr(href)',
            'a[href*="beginPage={0}"]::attr(href)'.format(page + 1)
        ]

        for selector_text in next_selectors:
            next_url = selector.css(selector_text).get()
            if next_url:
                yield Request(
                    url=response.urljoin(next_url),
                    callback=self.parse_search,
                    meta={"keyword": keyword, "page": page + 1}
                )
                break

        # 随机延迟，避免被检测
        if random.random() < 0.3:  # 30%概率
            time.sleep(random.uniform(2, 5))

    def parse_category(self, response: Response):
        """解析分类页面，获取商品列表"""
        category = response.meta.get('category', '')

        # 解析商品列表
        yield from self.parse_product_list(response, category)

        # 查找分页链接
        next_selectors = [
            '.ui-page-next a::attr(href)',
            '.next-page a::attr(href)',
            '.pagination .next a::attr(href)'
        ]

        selector = Selector(response)
        for selector_text in next_selectors:
            next_url = selector.css(selector_text).get()
            if next_url:
                yield Request(
                    url=response.urljoin(next_url),
                    callback=self.parse_category,
                    meta={"category": category}
                )
                break

    def parse_product_list(self, response: Response, category: str):
        """解析商品列表页面"""
        selector = Selector(response)

        # 多种商品列表选择器（适应不同页面结构）
        product_selectors = [
            '.sm-widget-offer .sm-offer-content .sm-offer-title a',
            '.sm-offer .sm-offer-title a',
            '.offer-item .offer-title a',
            '.product-item .product-title a',
            '.grid-item .item-title a',
            '.list-item .title a'
        ]

        product_links = []
        for selector_text in product_selectors:
            links = selector.css(selector_text)
            if links:
                product_links = links
                break

        for link in product_links[:40]:  # 限制每页商品数量
            product_url = link.css('::attr(href)').get()

            if product_url:
                # 添加referer以便后续请求
                yield Request(
                    url=response.urljoin(product_url),
                    callback=self.parse_product,
                    meta={
                        "category": category,
                        "referer": response.url
                    }
                )

        # 检查请求限制
        self.request_count += 1
        if self.request_count >= self.max_requests:
            self.logger.info(f"达到最大请求数限制: {self.max_requests}")
            raise CloseSpider(f"达到最大请求数限制: {self.max_requests}")

    def parse_product(self, response: Response):
        """解析商品详情页面"""
        selector = Selector(response)
        category = response.meta.get('category', '')

        try:
            # 检查是否为有效的商品页面
            if not self._is_valid_product_page(selector):
                self.logger.warning(f"无效的商品页面: {response.url}")
                return

            # 提取商品基本信息
            title = self._extract_title(selector)
            price = self._extract_price(selector)
            original_price = self._extract_original_price(selector)
            description = self._extract_description(selector)
            brand = self._extract_brand(selector)
            seller = self._extract_seller(selector)
            seller_id = self._extract_seller_id(selector)
            location = self._extract_location(selector)
            image_urls = self._extract_image_urls(selector)
            specifications = self._extract_specifications(selector)
            tags = self._extract_tags(selector)

            # 验证必要字段
            if not title:
                self.logger.warning(f"无法提取商品标题: {response.url}")
                return

            # 创建商品项
            item = ProductItem()
            item['title'] = title
            item['price'] = price
            item['original_price'] = original_price
            item['description'] = description
            item['category'] = category
            item['brand'] = brand
            item['seller'] = seller
            item['seller_id'] = seller_id
            item['location'] = location
            item['image_urls'] = image_urls
            item['specifications'] = specifications
            item['tags'] = tags
            item['source_url'] = response.url
            item['spider_name'] = self.name

            # 提取商品ID
            product_id = self._extract_product_id(response.url)
            if product_id:
                item['product_id'] = product_id
            else:
                # 如果无法从URL提取，生成唯一ID
                item['product_id'] = f"auto_{int(time.time())}_{random.randint(1000, 9999)}"

            self.logger.debug(f"成功解析商品: {title[:50]} - {product_id}")
            yield item

        except Exception as e:
            self.logger.error(f"解析商品页面失败: {response.url}, 错误: {e}")
            # 记录错误项，便于后续分析
            yield {
                'error': str(e),
                'url': response.url,
                'category': category,
                'timestamp': time.time()
            }

    def _is_valid_product_page(self, selector: Selector) -> bool:
        """检查是否为有效的商品页面"""
        # 检查是否有商品相关的关键元素
        indicators = [
            '.d-title',  # 商品标题
            '.d-price',  # 价格
            '.offer-title',  # 商品标题（备用）
            '.offer-price',  # 价格（备用）
            '.title-main',  # 标题（备用）
            'h1'  # 通用标题
        ]

        for indicator in indicators:
            elements = selector.css(indicator)
            if elements:
                return True

        return False

    def _extract_title(self, selector: Selector) -> str:
        """提取商品标题"""
        title_selectors = [
            '.d-title h1::text',
            '.d-title .title-text::text',
            '.offer-title h1::text',
            '.offer-title .title::text',
            '.title-main h1::text',
            '.product-title h1::text',
            '.detail-title h1::text',
            'h1::text'
        ]

        for selector_text in title_selectors:
            title = selector.css(selector_text).get()
            if title:
                title = title.strip()
                # 过滤掉无意义的标题
                if len(title) > 5 and not title.startswith('1') and not title.startswith('1688'):
                    return title

        # 如果直接选择器失败，尝试获取所有文本再过滤
        for selector_text in title_selectors:
            texts = selector.css(selector_text).getall()
            if texts:
                combined_text = ' '.join(texts).strip()
                if len(combined_text) > 5:
                    return combined_text

        return ""

    def _extract_seller_id(self, selector: Selector) -> Optional[str]:
        """提取卖家ID"""
        seller_selectors = [
            '.d-seller .seller-name::attr(data-id)',
            '.offer-seller::attr(data-seller-id)',
            '.seller-info::attr(data-id)',
            '.company-info::attr(data-id)'
        ]

        for selector_text in seller_selectors:
            seller_id = selector.css(selector_text).get()
            if seller_id:
                return seller_id.strip()

        # 尝试从URL中提取
        seller_links = selector.css('.seller-name a::attr(href)').getall()
        for link in seller_links:
            match = re.search(r'member/(\d+)', link)
            if match:
                return match.group(1)

        return None

    def _extract_price(self, selector: Selector) -> Optional[float]:
        """提取商品价格"""
        price_selectors = [
            '.d-price .price::text',
            '.d-price .value::text',
            '.offer-price .price::text',
            '.offer-price .value::text',
            '.price-current .price::text',
            '.price-current .value::text',
            '.price-display .price::text',
            '.price-display .value::text',
            '.price::text',
            '.value::text'
        ]

        for selector_text in price_selectors:
            price_texts = selector.css(selector_text).getall()
            for price_text in price_texts:
                if price_text:
                    # 清理价格文本
                    price_text = price_text.strip()
                    # 移除常见的价格前缀和后缀
                    price_text = re.sub(r'[￥¥$€£]', '', price_text)
                    price_text = re.sub(r'[^\d.]', '', price_text)

                    try:
                        price = float(price_text)
                        # 验证价格合理性
                        if 0 < price < 100000:  # 价格在合理范围内
                            return price
                    except (ValueError, TypeError):
                        continue

        return None

    def _extract_original_price(self, selector: Selector) -> Optional[float]:
        """提取原价"""
        price_selectors = [
            '.d-price .price-del::text',
            '.offer-price .price-del::text',
            '.price-original .price::text',
            '.price-del::text'
        ]

        for selector_text in price_selectors:
            price_text = selector.css(selector_text).get()
            if price_text:
                price_text = re.sub(r'[^\d.]', '', price_text)
                try:
                    return float(price_text)
                except ValueError:
                    continue

        return None

    def _extract_description(self, selector: Selector) -> str:
        """提取商品描述"""
        desc_selectors = [
            '.d-detail .description::text',
            '.offer-description::text',
            '.desc-content::text'
        ]

        for selector_text in desc_selectors:
            desc = selector.css(selector_text).get()
            if desc:
                return desc.strip()

        return ""

    def _extract_brand(self, selector: Selector) -> str:
        """提取品牌"""
        brand_selectors = [
            '.d-brand .brand-name::text',
            '.offer-brand::text',
            '.brand::text'
        ]

        for selector_text in brand_selectors:
            brand = selector.css(selector_text).get()
            if brand:
                return brand.strip()

        return ""

    def _extract_seller(self, selector: Selector) -> str:
        """提取卖家信息"""
        seller_selectors = [
            '.d-seller .seller-name::text',
            '.offer-seller::text',
            '.seller::text'
        ]

        for selector_text in seller_selectors:
            seller = selector.css(selector_text).get()
            if seller:
                return seller.strip()

        return ""

    def _extract_location(self, selector: Selector) -> str:
        """提取地理位置"""
        location_selectors = [
            '.d-seller .location::text',
            '.offer-location::text',
            '.location::text'
        ]

        for selector_text in location_selectors:
            location = selector.css(selector_text).get()
            if location:
                return location.strip()

        return ""

    def _extract_image_urls(self, selector: Selector) -> List[str]:
        """提取图片URL"""
        image_urls = set()  # 使用集合去重

        # 多种图片选择器
        image_selectors = [
            # 主图和画廊
            '.d-gallery img::attr(src)',
            '.d-gallery img::attr(data-src)',
            '.d-gallery-thumb img::attr(src)',
            '.d-gallery-thumb img::attr(data-src)',
            '.gallery img::attr(src)',
            '.gallery img::attr(data-src)',
            '.product-gallery img::attr(src)',
            '.product-gallery img::attr(data-src)',

            # 商品图片
            '.product-image img::attr(src)',
            '.product-image img::attr(data-src)',
            '.offer-image img::attr(src)',
            '.offer-image img::attr(data-src)',

            # 详情图片
            '.detail-image img::attr(src)',
            '.detail-image img::attr(data-src)',
            '.desc-content img::attr(src)',
            '.desc-content img::attr(data-src)',

            # 通用图片
            'img[src*="jpg"]::attr(src)',
            'img[src*="jpeg"]::attr(src)',
            'img[src*="png"]::attr(src)',
            'img[src*="webp"]::attr(src)'
        ]

        for selector_text in image_selectors:
            images = selector.css(selector_text).getall()
            for img in images:
                if img and isinstance(img, str):
                    # 处理相对URL
                    if img.startswith('//'):
                        img = 'https:' + img
                    elif img.startswith('/'):
                        img = 'https://www.1688.com' + img
                    elif not img.startswith('http'):
                        continue

                    # 过滤掉小图标和无用图片
                    if any(keyword in img.lower() for keyword in ['icon', 'logo', 'avatar', 'small', 'thumb']):
                        if any(size in img for size in ['50x50', '60x60', '80x80']):
                            continue

                    image_urls.add(img)

        # 转换为列表并限制数量
        return list(image_urls)[:20]  # 最多20张图片

    def _extract_specifications(self, selector: Selector) -> Dict[str, Any]:
        """提取商品规格"""
        specs = {}

        # 多种规格选择器
        spec_selectors = [
            '.d-attributes table tr',
            '.offer-attributes table tr',
            '.product-attributes table tr',
            '.specifications table tr',
            '.detail-attributes table tr',
            '.attribute-list tr',
            '.spec-item'
        ]

        for selector_text in spec_selectors:
            rows = selector.css(selector_text)
            if rows:
                for row in rows:
                    # 尝试不同的单元格结构
                    cells = row.css('td')
                    if len(cells) >= 2:
                        key = cells[0].css('::text').get()
                        value = cells[1].css('::text').get()
                    else:
                        # 尝试其他结构
                        key_elem = row.css('.attr-name, .spec-name, .label, dt')
                        value_elem = row.css('.attr-value, .spec-value, .value, dd')

                        key = key_elem.css('::text').get()
                        value = value_elem.css('::text').get()

                    if key and value:
                        key = key.strip().replace('：', '').replace(':', '')
                        value = value.strip()
                        if key and value:
                            specs[key] = value

                if specs:  # 如果找到了规格，就不再尝试其他选择器
                    break

        return specs

    def _extract_tags(self, selector: Selector) -> List[str]:
        """提取商品标签"""
        tags = []

        # 查找标签
        tag_selectors = [
            '.d-tags .tag::text',
            '.offer-tags .tag::text',
            '.tags .tag::text'
        ]

        for selector_text in tag_selectors:
            tag_elements = selector.css(selector_text)
            for tag in tag_elements:
                tag_text = tag.get().strip()
                if tag_text:
                    tags.append(tag_text)

        return tags

    def _extract_product_id(self, url: str) -> Optional[str]:
        """从URL提取商品ID"""
        # 从URL中提取数字ID
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)

        # 尝试从其他模式提取
        match = re.search(r'id=(\d+)', url)
        if match:
            return match.group(1)

        return None