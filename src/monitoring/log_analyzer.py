"""
日志分析器 - 分析日志数据，提取洞察和趋势
"""

import json
import re
import threading
import time
from collections import defaultdict, Counter, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from statistics import mean, median, stdev

from .logger import get_logger

logger = get_logger(__name__)


class AnalysisType(Enum):
    """分析类型"""
    FREQUENCY = "frequency"
    PERFORMANCE = "performance"
    ERROR = "error"
    BUSINESS = "business"
    SECURITY = "security"


class TrendDirection(Enum):
    """趋势方向"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    FLUCTUATING = "fluctuating"


@dataclass
class LogPattern:
    """日志模式"""
    pattern: str
    count: int
    first_seen: datetime
    last_seen: datetime
    samples: List[str]
    severity_distribution: Dict[str, int]
    context: Dict[str, Any]


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_name: str
    avg_value: float
    min_value: float
    max_value: float
    p50: float
    p95: float
    p99: float
    trend: TrendDirection
    time_series: List[Tuple[datetime, float]]


@dataclass
class Anomaly:
    """异常"""
    id: str
    type: str
    severity: str
    description: str
    detected_at: datetime
    affected_logs: List[str]
    confidence: float
    details: Dict[str, Any]


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: AnalysisType
    time_range: Dict[str, datetime]
    total_logs: int
    patterns: List[LogPattern]
    metrics: Dict[str, PerformanceMetric]
    anomalies: List[Anomaly]
    insights: List[str]
    recommendations: List[str]
    generated_at: datetime


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, analysis_interval: int = 300, max_patterns: int = 1000):
        self.analysis_interval = analysis_interval
        self.max_patterns = max_patterns
        self.analysis_active = False
        self.analysis_thread: Optional[threading.Thread] = None

        # 缓存数据
        self.log_cache: deque = deque(maxlen=10000)
        self.pattern_cache: Dict[str, LogPattern] = {}
        self.metric_history: Dict[str, List[float]] = defaultdict(list)
        self.anomalies: List[Anomaly] = []

        # 分析配置
        self.pattern_min_occurrences = 5
        self.anomaly_threshold = 2.0  # 标准差倍数
        self.trend_window = 100  # 趋势分析窗口

        self._lock = threading.Lock()

    def start_analysis(self):
        """启动分析"""
        if self.analysis_active:
            return

        self.analysis_active = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        logger.info("日志分析器已启动")

    def stop_analysis(self):
        """停止分析"""
        self.analysis_active = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=10)
        logger.info("日志分析器已停止")

    def _analysis_loop(self):
        """分析循环"""
        while self.analysis_active:
            try:
                self._perform_analysis()
                time.sleep(self.analysis_interval)
            except Exception as e:
                logger.error("日志分析循环异常", exc_info=True)
                time.sleep(self.analysis_interval)

    def _perform_analysis(self):
        """执行分析"""
        try:
            # 加载新日志
            self._load_recent_logs()

            if not self.log_cache:
                return

            # 分析模式
            self._analyze_patterns()

            # 分析性能
            self._analyze_performance()

            # 检测异常
            self._detect_anomalies()

            # 清理旧数据
            self._cleanup_old_data()

        except Exception as e:
            logger.error("执行日志分析失败", exc_info=True)

    def _load_recent_logs(self):
        """加载最近的日志"""
        try:
            from .logger import structured_logger

            log_files = structured_logger.get_log_files()
            if not log_files:
                return

            cutoff_time = datetime.now() - timedelta(hours=1)  # 最近1小时

            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                log_entry = json.loads(line.strip())
                                log_time = datetime.fromisoformat(log_entry.get('timestamp', ''))

                                if log_time >= cutoff_time:
                                    self.log_cache.append(log_entry)

                            except (json.JSONDecodeError, ValueError):
                                continue

                except Exception as e:
                    logger.error(f"读取日志文件失败 {log_file}: {e}")

        except Exception as e:
            logger.error("加载日志失败", exc_info=True)

    def _analyze_patterns(self):
        """分析日志模式"""
        try:
            # 提取消息模式
            message_patterns = defaultdict(list)

            for log_entry in self.log_cache:
                message = log_entry.get('message', '')
                if message:
                    # 标准化消息
                    normalized = self._normalize_message(message)
                    message_patterns[normalized].append({
                        'message': message,
                        'level': log_entry.get('level', 'INFO'),
                        'timestamp': log_entry.get('timestamp'),
                        'details': log_entry.get('details', {})
                    })

            # 更新模式缓存
            current_time = datetime.now()
            for pattern, occurrences in message_patterns.items():
                if len(occurrences) >= self.pattern_min_occurrences:
                    if pattern in self.pattern_cache:
                        # 更新现有模式
                        cached_pattern = self.pattern_cache[pattern]
                        cached_pattern.count = len(occurrences)
                        cached_pattern.last_seen = current_time
                        cached_pattern.samples = [occ['message'] for occ in occurrences[-5:]]

                        # 更新严重程度分布
                        severity_dist = Counter(occ['level'] for occ in occurrences)
                        cached_pattern.severity_distribution = dict(severity_dist)
                    else:
                        # 创建新模式
                        severity_dist = Counter(occ['level'] for occ in occurrences)
                        self.pattern_cache[pattern] = LogPattern(
                            pattern=pattern,
                            count=len(occurrences),
                            first_seen=min(
                                datetime.fromisoformat(occ['timestamp'])
                                for occ in occurrences
                            ),
                            last_seen=current_time,
                            samples=[occ['message'] for occ in occurrences[-5:]],
                            severity_distribution=dict(severity_dist),
                            context=self._extract_pattern_context(occurrences)
                        )

            # 限制模式数量
            if len(self.pattern_cache) > self.max_patterns:
                # 保留最频繁的模式
                sorted_patterns = sorted(
                    self.pattern_cache.items(),
                    key=lambda x: x[1].count,
                    reverse=True
                )
                self.pattern_cache = dict(sorted_patterns[:self.max_patterns])

        except Exception as e:
            logger.error("分析日志模式失败", exc_info=True)

    def _normalize_message(self, message: str) -> str:
        """标准化消息"""
        # 移除数字
        normalized = re.sub(r'\d+', '{N}', message)
        # 移除UUID和ID
        normalized = re.sub(r'[a-f0-9]{8,}', '{ID}', normalized)
        # 移除IP地址
        normalized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '{IP}', normalized)
        # 移除时间戳
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '{TIME}', normalized)
        # 移除文件路径中的具体部分
        normalized = re.sub(r'/[^/]+/\./', '/{PATH}/./', normalized)
        # 转换为小写并去除多余空格
        normalized = ' '.join(normalized.lower().split())

        return normalized

    def _extract_pattern_context(self, occurrences: List[Dict]) -> Dict[str, Any]:
        """提取模式上下文"""
        try:
            # 提取常见的模块和函数
            modules = Counter()
            functions = Counter()
            task_ids = Counter()

            for occ in occurrences:
                details = occ.get('details', {})

                # 从details中提取上下文信息
                if 'module' in details:
                    modules[details['module']] += 1
                if 'function' in details:
                    functions[details['function']] += 1
                if 'task_id' in details:
                    task_ids[details['task_id']] += 1

            return {
                'common_modules': dict(modules.most_common(5)),
                'common_functions': dict(functions.most_common(5)),
                'common_tasks': dict(task_ids.most_common(5)),
                'time_span_hours': self._calculate_time_span(occurrences)
            }

        except Exception:
            return {}

    def _calculate_time_span(self, occurrences: List[Dict]) -> float:
        """计算时间跨度（小时）"""
        try:
            timestamps = [
                datetime.fromisoformat(occ['timestamp'])
                for occ in occurrences
                if 'timestamp' in occ
            ]
            if len(timestamps) < 2:
                return 0

            time_span = max(timestamps) - min(timestamps)
            return time_span.total_seconds() / 3600

        except Exception:
            return 0

    def _analyze_performance(self):
        """分析性能指标"""
        try:
            # 提取性能相关的日志
            performance_logs = [
                entry for entry in self.log_cache
                if self._is_performance_log(entry)
            ]

            for log_entry in performance_logs:
                self._extract_performance_metrics(log_entry)

            # 计算性能趋势
            for metric_name, values in self.metric_history.items():
                if len(values) >= self.trend_window:
                    recent_values = values[-self.trend_window:]
                    trend = self._calculate_trend(recent_values)
                    # 这里可以更新性能指标或触发告警

        except Exception as e:
            logger.error("分析性能指标失败", exc_info=True)

    def _is_performance_log(self, log_entry: Dict) -> bool:
        """判断是否为性能日志"""
        message = log_entry.get('message', '').lower()
        details = log_entry.get('details', {})

        perf_keywords = [
            'duration', 'response time', 'execution time', 'latency',
            'throughput', 'performance', 'timing', 'speed'
        ]

        return (any(keyword in message for keyword in perf_keywords) or
                any(key in details for key in ['duration_ms', 'response_time', 'execution_time']))

    def _extract_performance_metrics(self, log_entry: Dict):
        """提取性能指标"""
        try:
            details = log_entry.get('details', {})
            timestamp = datetime.fromisoformat(log_entry.get('timestamp', ''))

            # 提取各种性能指标
            metrics = {
                'duration_ms': details.get('duration_ms'),
                'response_time': details.get('response_time'),
                'execution_time': details.get('execution_time'),
                'throughput': details.get('throughput'),
                'cpu_usage': details.get('cpu_usage'),
                'memory_usage': details.get('memory_usage')
            }

            for metric_name, value in metrics.items():
                if value is not None and isinstance(value, (int, float)):
                    self.metric_history[metric_name].append(value)
                    # 限制历史数据大小
                    if len(self.metric_history[metric_name]) > 1000:
                        self.metric_history[metric_name] = self.metric_history[metric_name][-1000:]

        except Exception as e:
            logger.error("提取性能指标失败", exc_info=True)

    def _calculate_trend(self, values: List[float]) -> TrendDirection:
        """计算趋势"""
        try:
            if len(values) < 10:
                return TrendDirection.STABLE

            # 简单线性回归
            x = list(range(len(values)))
            n = len(values)

            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

            # 计算相对变化率
            avg_value = sum_y / n
            relative_slope = slope / avg_value if avg_value != 0 else 0

            # 确定趋势
            if abs(relative_slope) < 0.01:
                return TrendDirection.STABLE
            elif relative_slope > 0.05:
                return TrendDirection.INCREASING
            elif relative_slope < -0.05:
                return TrendDirection.DECREASING
            else:
                return TrendDirection.FLUCTUATING

        except Exception:
            return TrendDirection.STABLE

    def _detect_anomalies(self):
        """检测异常"""
        try:
            # 检测错误率异常
            self._detect_error_rate_anomaly()

            # 检测性能异常
            self._detect_performance_anomaly()

            # 检测频率异常
            self._detect_frequency_anomaly()

        except Exception as e:
            logger.error("检测异常失败", exc_info=True)

    def _detect_error_rate_anomaly(self):
        """检测错误率异常"""
        try:
            # 计算最近1小时的错误率
            recent_logs = [
                entry for entry in self.log_cache
                if entry.get('level') in ['ERROR', 'CRITICAL']
            ]

            total_logs = len(self.log_cache)
            error_count = len(recent_logs)

            if total_logs > 0:
                error_rate = error_count / total_logs

                # 计算历史错误率
                historical_rates = []
                # 这里应该从更长时间的数据计算历史基线
                baseline_error_rate = 0.05  # 5% 基线

                # 检测异常
                if error_rate > baseline_error_rate * 2:
                    anomaly = Anomaly(
                        id=f"error_rate_{int(time.time())}",
                        type="error_rate_spike",
                        severity="high" if error_rate > baseline_error_rate * 5 else "medium",
                        description=f"错误率异常升高: {error_rate:.2%}",
                        detected_at=datetime.now(),
                        affected_logs=[entry.get('message', '') for entry in recent_logs[:10]],
                        confidence=min(error_rate / baseline_error_rate, 1.0),
                        details={
                            'current_rate': error_rate,
                            'baseline_rate': baseline_error_rate,
                            'error_count': error_count,
                            'total_logs': total_logs
                        }
                    )
                    self.anomalies.append(anomaly)

        except Exception as e:
            logger.error("检测错误率异常失败", exc_info=True)

    def _detect_performance_anomaly(self):
        """检测性能异常"""
        try:
            for metric_name, values in self.metric_history.items():
                if len(values) < 30:  # 需要足够的数据点
                    continue

                recent_values = values[-30:]
                historical_values = values[:-30] if len(values) > 30 else []

                if len(historical_values) < 10:
                    continue

                # 计算统计量
                historical_mean = mean(historical_values)
                historical_std = stdev(historical_values) if len(historical_values) > 1 else 0
                recent_mean = mean(recent_values)

                # 检测异常
                if historical_std > 0:
                    z_score = abs(recent_mean - historical_mean) / historical_std
                    if z_score > self.anomaly_threshold:
                        anomaly = Anomaly(
                            id=f"perf_{metric_name}_{int(time.time())}",
                            type="performance_anomaly",
                            severity="high" if z_score > 3 else "medium",
                            description=f"性能指标异常: {metric_name}",
                            detected_at=datetime.now(),
                            affected_logs=[f"Recent value: {recent_mean:.2f}, Historical avg: {historical_mean:.2f}"],
                            confidence=min(z_score / 3, 1.0),
                            details={
                                'metric_name': metric_name,
                                'recent_mean': recent_mean,
                                'historical_mean': historical_mean,
                                'z_score': z_score,
                                'threshold': self.anomaly_threshold
                            }
                        )
                        self.anomalies.append(anomaly)

        except Exception as e:
            logger.error("检测性能异常失败", exc_info=True)

    def _detect_frequency_anomaly(self):
        """检测频率异常"""
        try:
            # 按时间窗口统计日志频率
            time_buckets = defaultdict(int)
            current_time = datetime.now()

            for log_entry in self.log_cache:
                try:
                    timestamp = datetime.fromisoformat(log_entry.get('timestamp', ''))
                    bucket = timestamp.replace(second=0, microsecond=0)
                    time_buckets[bucket] += 1
                except (ValueError, TypeError):
                    continue

            if len(time_buckets) < 5:
                return

            # 计算频率统计
            frequencies = list(time_buckets.values())
            avg_frequency = mean(frequencies)
            std_frequency = stdev(frequencies) if len(frequencies) > 1 else 0

            # 检测异常
            for bucket, count in time_buckets.items():
                if std_frequency > 0:
                    z_score = abs(count - avg_frequency) / std_frequency
                    if z_score > self.anomaly_threshold:
                        anomaly = Anomaly(
                            id=f"freq_{int(bucket.timestamp())}_{int(time.time())}",
                            type="frequency_anomaly",
                            severity="medium",
                            description=f"日志频率异常: {count} logs/minute",
                            detected_at=datetime.now(),
                            affected_logs=[f"Time: {bucket}, Count: {count}"],
                            confidence=min(z_score / 3, 1.0),
                            details={
                                'bucket_time': bucket.isoformat(),
                                'log_count': count,
                                'avg_frequency': avg_frequency,
                                'z_score': z_score
                            }
                        )
                        self.anomalies.append(anomaly)

        except Exception as e:
            logger.error("检测频率异常失败", exc_info=True)

    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)

            # 清理异常记录
            self.anomalies = [
                anomaly for anomaly in self.anomalies
                if anomaly.detected_at >= cutoff_time
            ]

            # 清理性能指标历史
            for metric_name in self.metric_history:
                if len(self.metric_history[metric_name]) > 1000:
                    self.metric_history[metric_name] = self.metric_history[metric_name][-1000:]

        except Exception as e:
            logger.error("清理旧数据失败", exc_info=True)

    def generate_analysis_report(self, hours: int = 24) -> AnalysisResult:
        """生成分析报告"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            # 筛选时间范围内的数据
            recent_logs = [
                entry for entry in self.log_cache
                if self._parse_timestamp(entry.get('timestamp', '')) >= start_time
            ]

            # 生成洞察
            insights = self._generate_insights(recent_logs)
            recommendations = self._generate_recommendations(insights)

            return AnalysisResult(
                analysis_type=AnalysisType.FREQUENCY,
                time_range={'start': start_time, 'end': end_time},
                total_logs=len(recent_logs),
                patterns=list(self.pattern_cache.values()),
                metrics=self._calculate_performance_metrics(),
                anomalies=self.anomalies[-50:],  # 最近50个异常
                insights=insights,
                recommendations=recommendations,
                generated_at=datetime.now()
            )

        except Exception as e:
            logger.error("生成分析报告失败", exc_info=True)
            return AnalysisResult(
                analysis_type=AnalysisType.FREQUENCY,
                time_range={},
                total_logs=0,
                patterns=[],
                metrics={},
                anomalies=[],
                insights=[f"分析失败: {str(e)}"],
                recommendations=[],
                generated_at=datetime.now()
            )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """解析时间戳"""
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return datetime.min

    def _generate_insights(self, logs: List[Dict]) -> List[str]:
        """生成洞察"""
        insights = []
        try:
            if not logs:
                return ["没有可分析的日志数据"]

            # 错误率洞察
            error_count = sum(1 for log in logs if log.get('level') in ['ERROR', 'CRITICAL'])
            error_rate = error_count / len(logs)
            if error_rate > 0.1:
                insights.append(f"错误率较高 ({error_rate:.1%})，需要关注")
            elif error_rate < 0.01:
                insights.append("错误率很低，系统运行稳定")

            # 日志量洞察
            if len(logs) > 10000:
                insights.append("日志量较大，考虑优化日志级别或增加轮转策略")

            # 模式洞察
            if self.pattern_cache:
                top_pattern = max(self.pattern_cache.values(), key=lambda p: p.count)
                insights.append(f"最常见的日志模式: {top_pattern.pattern[:50]}... (出现{top_pattern.count}次)")

            # 异常洞察
            if len(self.anomalies) > 10:
                insights.append(f"检测到较多异常 ({len(self.anomalies)}个)，建议深入分析")

        except Exception as e:
            insights.append(f"生成洞察失败: {e}")

        return insights

    def _generate_recommendations(self, insights: List[str]) -> List[str]:
        """生成建议"""
        recommendations = []
        try:
            for insight in insights:
                if "错误率较高" in insight:
                    recommendations.extend([
                        "检查错误日志，识别根本原因",
                        "增加错误监控和告警",
                        "考虑实施熔断机制"
                    ])
                elif "日志量较大" in insight:
                    recommendations.extend([
                        "调整日志级别，减少DEBUG日志",
                        "实施日志聚合和压缩",
                        "考虑使用日志管理服务"
                    ])
                elif "异常" in insight:
                    recommendations.extend([
                        "分析异常模式，优化系统稳定性",
                        "增加自动恢复机制",
                        "完善监控告警规则"
                    ])

            # 去重
            recommendations = list(set(recommendations))

        except Exception as e:
            recommendations.append(f"生成建议失败: {e}")

        return recommendations

    def _calculate_performance_metrics(self) -> Dict[str, PerformanceMetric]:
        """计算性能指标"""
        metrics = {}
        try:
            for metric_name, values in self.metric_history.items():
                if len(values) < 2:
                    continue

                sorted_values = sorted(values)
                n = len(values)

                performance_metric = PerformanceMetric(
                    metric_name=metric_name,
                    avg_value=mean(values),
                    min_value=min(values),
                    max_value=max(values),
                    p50=sorted_values[int(n * 0.5)],
                    p95=sorted_values[int(n * 0.95)],
                    p99=sorted_values[int(n * 0.99)],
                    trend=self._calculate_trend(values[-self.trend_window:]),
                    time_series=[]  # 这里可以添加时间序列数据
                )

                metrics[metric_name] = performance_metric

        except Exception as e:
            logger.error("计算性能指标失败", exc_info=True)

        return metrics

    def search_logs(self, query: str, level: str = None, hours: int = 24) -> List[Dict]:
        """搜索日志"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            query_lower = query.lower()

            results = []
            for log_entry in self.log_cache:
                try:
                    timestamp = self._parse_timestamp(log_entry.get('timestamp', ''))
                    if timestamp < start_time:
                        continue

                    if level and log_entry.get('level') != level:
                        continue

                    # 搜索消息和详情
                    message = log_entry.get('message', '').lower()
                    details = str(log_entry.get('details', {})).lower()

                    if query_lower in message or query_lower in details:
                        results.append(log_entry)

                except Exception:
                    continue

            return results

        except Exception as e:
            logger.error("搜索日志失败", exc_info=True)
            return []

    def get_top_patterns(self, limit: int = 20) -> List[LogPattern]:
        """获取top模式"""
        with self._lock:
            sorted_patterns = sorted(
                self.pattern_cache.values(),
                key=lambda p: p.count,
                reverse=True
            )
            return sorted_patterns[:limit]

    def get_recent_anomalies(self, hours: int = 24) -> List[Anomaly]:
        """获取最近的异常"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            anomaly for anomaly in self.anomalies
            if anomaly.detected_at >= cutoff_time
        ]


# 全局日志分析器实例
log_analyzer = LogAnalyzer()