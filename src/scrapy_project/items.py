"""
Scrapy项目数据项定义
"""
import scrapy


class ProductItem(scrapy.Item):
    """商品数据项"""
    # 基本信息
    title = scrapy.Field()
    product_id = scrapy.Field()
    price = scrapy.Field()
    original_price = scrapy.Field()
    description = scrapy.Field()
    category = scrapy.Field()
    brand = scrapy.Field()
    seller = scrapy.Field()
    seller_id = scrapy.Field()
    location = scrapy.Field()

    # 媒体内容
    image_urls = scrapy.Field()
    specifications = scrapy.Field()
    tags = scrapy.Field()

    # 元数据
    source_url = scrapy.Field()
    crawl_time = scrapy.Field()
    spider_name = scrapy.Field()


class ImageItem(scrapy.Item):
    """图片数据项"""
    url = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()

    # 商品关联
    product_id = scrapy.Field()

    # 图片信息
    image_type = scrapy.Field()  # main, detail, thumbnail
    file_size = scrapy.Field()
    width = scrapy.Field()
    height = scrapy.Field()