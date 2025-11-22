"""
Scrapy设置文件
"""
import os

from ..config import settings

# Scrapy项目设置
BOT_NAME = '1688sync'

SPIDER_MODULES = ['src.scrapy_project.spiders']
NEWSPIDER_MODULE = 'src.scrapy_project.spiders'

# 用户代理设置
USER_AGENT = settings.scrapy_user_agent

# 并发控制
CONCURRENT_REQUESTS = settings.scrapy_concurrent_requests
DOWNLOAD_DELAY = settings.scrapy_download_delay
RANDOMIZE_DOWNLOAD_DELAY = settings.scrapy_randomize_download_delay

# 禁用cookies
COOKIES_ENABLED = False

# 启用并遵守robots.txt
ROBOTSTXT_OBEY = True

# 配置中间件
DOWNLOADER_MIDDLEWARES = {
    # 禁用默认User-Agent中间件
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    # 自定义中间件
    'src.scrapy_project.middlewares.UserAgentMiddleware': 540,
    'src.scrapy_project.middlewares.ProxyMiddleware': 541,
    'src.scrapy_project.middlewares.HeaderMiddleware': 542,
    'src.scrapy_project.middlewares.CookieMiddleware': 543,
    'src.scrapy_project.middlewares.AntiDetectionMiddleware': 544,
    'src.scrapy_project.middlewares.RetryMiddlewareWithBackoff': 550,
    # Scrapy默认中间件
    'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 560,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 580,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 600,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 610,
    'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
}

# 启用的爬虫中间件
SPIDER_MIDDLEWARES = {
    'src.scrapy_project.middlewares.SpiderMiddleware': 543,
    'scrapy.downloadermiddlewares.depth.DepthMiddleware': 900,
    'scrapy.downloadermiddlewares.httperror.HttpErrorMiddleware': 950,
    'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': 500,
    'scrapy.spidermiddlewares.referer.RefererMiddleware': 700,
    'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': 800,
    'scrapy.spidermiddlewares.depth.DepthMiddleware': 900,
}

# 扩展
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
    'scrapy.extensions.logstats.LogStats': None,
}

# 自动限速扩展
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# 日志设置
LOG_LEVEL = settings.log_level.lower()
LOG_FILE = settings.log_file

# 项目管道设置
ITEM_PIPELINES = {
    # 数据处理管道
    'src.scrapy_project.pipelines.DataCleaningPipeline': 200,
    'src.scrapy_project.pipelines.DataValidationPipeline': 300,
    'src.scrapy_project.pipelines.DuplicateFilterPipeline': 350,

    # 存储管道
    'src.scrapy_project.pipelines.DatabasePipeline': 400,
    'src.scrapy_project.pipelines.ImageDownloadPipeline': 500,

    # 统计管道
    'src.scrapy_project.pipelines.StatsPipeline': 900,
}

# 图片下载设置
IMAGES_STORE = str(settings.image_dir)
IMAGES_EXPIRES = 90
IMAGES_THUMBS = {
    'small': (50, 50),
    'big': (270, 270),
}

# 重试设置
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_BACKOFF_POLICY = 'exponential'

# 请求指纹设置
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'
DUPEFILTER_DEBUG = False

# 调试设置
CLOSESPIDER_TIMEOUT = 300
DOWNLOAD_TIMEOUT = settings.request_timeout

# 并发请求延迟
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 8

# User-Agent列表
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
]

# 代理列表（可选）
# PROXY_LIST = [
#     'http://proxy1.example.com:8080',
#     'http://proxy2.example.com:8080',
# ]

# DNS设置
DNS_TIMEOUT = 60
DNS_RESOLVER = 'scrapy.resolver.CachingThreadedResolver'

# 下载处理器
DOWNLOAD_HANDLERS = {
    'http': 'scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler',
    'https': 'scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler',
}

# 压缩设置
COMPRESSION_ENABLED = True

# 缓存设置
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# 统计收集器
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'
STATS_DUMP = True