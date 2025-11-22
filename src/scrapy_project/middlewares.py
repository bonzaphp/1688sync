"""
Scrapy中间件定义
"""
import random
import time
from typing import Any, Callable, Dict, Iterable, Optional

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Request, Response
from scrapy.exceptions import NotConfigured
from scrapy.utils.response import response_status_message

from ..config import settings


class UserAgentMiddleware:
    """随机User-Agent中间件"""

    def __init__(self, user_agents: list):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        user_agents = crawler.settings.getlist('USER_AGENT_LIST')
        if not user_agents:
            raise NotConfigured("USER_AGENT_LIST setting is required")
        return cls(user_agents)

    def process_request(self, request: Request, spider):
        """为请求添加随机User-Agent"""
        user_agent = random.choice(self.user_agents)
        request.headers.setdefault('User-Agent', user_agent)


class ProxyMiddleware:
    """代理中间件"""

    def __init__(self, proxy_list: list):
        self.proxy_list = proxy_list
        self.current_proxy = None
        self.proxy_failures = {}

    @classmethod
    def from_crawler(cls, crawler):
        proxy_list = crawler.settings.getlist('PROXY_LIST')
        return cls(proxy_list)

    def process_request(self, request: Request, spider):
        """为请求添加代理"""
        if self.proxy_list:
            # 选择失败次数最少的代理
            self.current_proxy = min(self.proxy_list, key=lambda x: self.proxy_failures.get(x, 0))
            request.meta['proxy'] = self.current_proxy

    def process_response(self, request: Request, response: Response, spider):
        """处理响应，如果代理失败则切换"""
        if response.status in [403, 407, 429]:
            proxy = request.meta.get('proxy')
            if proxy:
                self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
                spider.logger.warning(f"代理失败: {proxy}, 状态码: {response.status}")

        return response


class ErrorHandlingMiddleware:
    """错误处理中间件"""

    def process_response(self, request: Request, response: Response, spider):
        """处理异常响应"""
        if response.status == 403:
            spider.logger.warning(f"访问被禁止: {request.url}")
            # 可以在这里实现反爬虫策略
        elif response.status == 404:
            spider.logger.debug(f"页面不存在: {request.url}")
        elif response.status >= 500:
            spider.logger.error(f"服务器错误: {request.url}, 状态码: {response.status}")

        return response

    def process_exception(self, request: Request, exception, spider):
        """处理请求异常"""
        spider.logger.error(f"请求异常: {request.url}, 异常: {exception}")
        return None


class RateLimitMiddleware:
    """限速中间件"""

    def __init__(self, delay: float = 1.0, randomize: bool = True):
        self.delay = delay
        self.randomize = randomize
        self.last_request_time = 0

    @classmethod
    def from_crawler(cls, crawler):
        delay = crawler.settings.getfloat('DOWNLOAD_DELAY', 1.0)
        randomize = crawler.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY', True)
        return cls(delay, randomize)

    def process_request(self, request: Request, spider):
        """限制请求频率"""
        if self.delay > 0:
            current_time = time.time()
            if self.randomize:
                # 随机延迟，避免被检测
                delay = self.delay * random.uniform(0.5, 1.5)
            else:
                delay = self.delay

            elapsed = current_time - self.last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)

            self.last_request_time = time.time()


class RetryMiddlewareWithBackoff(RetryMiddleware):
    """带退避策略的重试中间件"""

    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.retry_backoff_policy = settings.get('RETRY_BACKOFF_POLICY', 'exponential')

    def get_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟"""
        if self.retry_backoff_policy == 'exponential':
            # 指数退避
            return min(2 ** retry_count, 60)  # 最大60秒
        elif self.retry_backoff_policy == 'linear':
            # 线性退避
            return retry_count * 5
        else:
            # 固定延迟
            return 5

    def process_response(self, request: Request, response: Response, spider):
        """处理响应，决定是否重试"""
        if request.meta.get('dont_retry', False):
            return response

        if response.status in self.retry_http_codes:
            retries = request.meta.get('retry_times', 0) + 1

            if retries <= self.max_retry_times:
                spider.logger.warning(
                    f"重试请求 {retries}/{self.max_retry_times}: "
                    f"{request.url} (状态码: {response.status})"
                )

                # 计算延迟
                delay = self.get_retry_delay(retries)
                time.sleep(delay)

                retryreq = request.copy()
                retryreq.meta['retry_times'] = retries
                retryreq.dont_filter = True
                return retryreq
            else:
                spider.logger.error(f"超过最大重试次数: {request.url}")

        return response


class HeaderMiddleware:
    """请求头中间件"""

    def __init__(self):
        # 常用请求头
        self.common_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def process_request(self, request: Request, spider):
        """添加请求头"""
        # 合并请求头
        for key, value in self.common_headers.items():
            request.headers.setdefault(key, value)

        # 添加Referer（如果不是第一个请求）
        referer = request.meta.get('referer')
        if referer:
            request.headers.setdefault('Referer', referer)


class CookieMiddleware:
    """Cookie管理中间件"""

    def __init__(self):
        self.cookies = {}

    def process_request(self, request: Request, spider):
        """管理Cookie"""
        # 如果需要特定Cookie，在这里添加
        if spider.name == '1688_products':
            # 为1688爬虫添加必要Cookie
            request.headers.setdefault('Cookie', self._get_1688_cookies())

    def _get_1688_cookies(self) -> str:
        """获取1688网站的Cookie"""
        # 这里可以实现Cookie生成逻辑
        # 或者从配置文件读取
        cookies = [
            'aliyuncs_tracking=2; domain=.1688.com; path=/',
            '_tb_token_=123456; domain=.1688.com; path=/',
            # 添加更多Cookie...
        ]
        return '; '.join(cookies)


class AntiDetectionMiddleware:
    """反检测中间件"""

    def __init__(self):
        self.request_count = 0
        self.session_start = time.time()

    def process_request(self, request: Request, spider):
        """反检测处理"""
        self.request_count += 1

        # 每隔一定数量请求，模拟人类行为
        if self.request_count % 50 == 0:
            # 长时间暂停
            time.sleep(random.uniform(30, 60))
        elif self.request_count % 10 == 0:
            # 短时间暂停
            time.sleep(random.uniform(5, 15))

        # 随机添加一些查询参数，使请求看起来更像真实用户
        if random.random() < 0.1:  # 10%的概率
            self._add_random_params(request)

    def _add_random_params(self, request: Request):
        """添加随机参数"""
        if request.method == 'GET':
            # 添加随机时间戳或其他参数
            separator = '&' if '?' in request.url else '?'
            request.url = f"{request.url}{separator}_t={int(time.time())}"


class SpiderMiddleware:
    """爬虫中间件"""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def process_spider_input(self, response: Response, spider):
        """爬虫输入处理"""
        # 可以在这里预处理响应
        pass

    def process_spider_output(self, response: Response, result: Any, spider):
        """爬虫输出处理"""
        # 可以在这里后处理结果
        for item in result:
            yield item

    def process_spider_exception(self, response, exception, spider):
        """处理爬虫异常"""
        spider.logger.error(f"爬虫异常: {exception}")
        return []

    def process_start_requests(self, start_requests, spider):
        """处理起始请求"""
        for request in start_requests:
            yield request

    def spider_opened(self, spider):
        """爬虫启动时调用"""
        spider.logger.info(f"爬虫已启动: {spider.name}")

    def spider_closed(self, spider):
        """爬虫关闭时调用"""
        spider.logger.info(f"爬虫已关闭: {spider.name}")