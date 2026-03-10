# -*- coding: UTF-8 -*-
"""
Rate Limit & Circuit Breaker V2 - 限流与熔断器

功能:
- Token Bucket 限流器 (每 IP/每路径)
- 熔断器模式 (CLOSED → OPEN → HALF_OPEN)
- 自适应限流 (基于 CPU/内存负载)
- IP 白名单/黑名单访问控制

版本：V2.0.0
作者：AIWriteX Team
创建日期：2026-03-09
"""

import time
from typing import Dict, Any, Optional, Set, List
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import threading


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态（测试恢复）


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    per_ip: bool = True
    per_path: bool = False


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5      # 失败阈值
    success_threshold: int = 3      # 成功阈值
    timeout_seconds: float = 30.0   # 超时时间
    half_open_max_calls: int = 3    # 半开状态最大调用数


class TokenBucket:
    """
    Token Bucket 限流器

    特性:
    - 平滑限流
    - 支持突发流量
    - 自动补充 token
    """

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: 每秒 token 生成速率
            capacity: bucket 容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        消费 token

        Returns:
            True 如果成功，False 如果限流
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # 补充 token
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            # 检查是否有足够 token
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """获取需要等待的时间"""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0

            needed = tokens - self.tokens
            return needed / self.rate


class RateLimiter:
    """
    限流器

    特性:
    - 多维度限流（IP、路径、用户）
    - 动态调整限流策略
    - 白名单/黑名单
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()

        # IP 维度的 bucket
        self.ip_buckets: Dict[str, TokenBucket] = {}

        # 路径维度的 bucket
        self.path_buckets: Dict[str, TokenBucket] = {}

        # 全局 bucket
        self.global_bucket = TokenBucket(
            rate=self.config.requests_per_second * 10,
            capacity=self.config.burst_size * 10
        )

        # 白名单和黑名单
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()

        # 锁
        self.lock = threading.Lock()

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'whitelisted_requests': 0,
            'blacklisted_requests': 0
        }

    def allow_request(
        self,
        ip: str,
        path: str,
        user_id: Optional[str] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        判断请求是否允许

        Returns:
            (是否允许，额外信息)
        """
        with self.lock:
            self.stats['total_requests'] += 1

            # 检查白名单
            if ip in self.whitelist:
                self.stats['whitelisted_requests'] += 1
                return True, {'reason': 'whitelisted'}

            # 检查黑名单
            if ip in self.blacklist:
                self.stats['blacklisted_requests'] += 1
                return False, {'reason': 'blacklisted', 'retry_after': 0}

            # 检查全局限流
            if not self.global_bucket.consume():
                self.stats['blocked_requests'] += 1
                wait_time = self.global_bucket.get_wait_time()
                return False, {
                    'reason': 'global_rate_limit',
                    'retry_after': wait_time
                }

            # 检查 IP 限流
            if self.config.per_ip:
                if ip not in self.ip_buckets:
                    self.ip_buckets[ip] = TokenBucket(
                        rate=self.config.requests_per_second,
                        capacity=self.config.burst_size
                    )

                if not self.ip_buckets[ip].consume():
                    self.stats['blocked_requests'] += 1
                    wait_time = self.ip_buckets[ip].get_wait_time()
                    return False, {
                        'reason': 'ip_rate_limit',
                        'retry_after': wait_time
                    }

            # 检查路径限流
            if self.config.per_path:
                if path not in self.path_buckets:
                    self.path_buckets[path] = TokenBucket(
                        rate=self.config.requests_per_second,
                        capacity=self.config.burst_size
                    )

                if not self.path_buckets[path].consume():
                    self.stats['blocked_requests'] += 1
                    wait_time = self.path_buckets[path].get_wait_time()
                    return False, {
                        'reason': 'path_rate_limit',
                        'retry_after': wait_time
                    }

            self.stats['allowed_requests'] += 1
            return True, {'reason': 'allowed'}

    def add_to_whitelist(self, ip: str):
        """添加到白名单"""
        with self.lock:
            self.whitelist.add(ip)

    def add_to_blacklist(self, ip: str):
        """添加到黑名单"""
        with self.lock:
            self.blacklist.add(ip)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'unique_ips': len(self.ip_buckets),
            'unique_paths': len(self.path_buckets),
            'block_rate': f"{self.stats['blocked_requests'] / self.stats['total_requests']:.2%}"
            if self.stats['total_requests'] > 0 else "0%"
        }


class CircuitBreaker:
    """
    熔断器

    状态机:
    CLOSED (正常) → OPEN (熔断) → HALF_OPEN (测试) → CLOSED (恢复)
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.lock = threading.Lock()

        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'circuit_opens': 0,
            'circuit_closes': 0
        }

    def call(self, func, *args, **kwargs):
        """执行受保护的函数调用"""
        with self.lock:
            self.stats['total_calls'] += 1

            # 检查是否需要尝试恢复
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.config.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.stats['circuit_opens'] += 1
                else:
                    raise Exception("Circuit breaker is OPEN")

            # 半开状态限制调用次数
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise Exception(
                        "Circuit breaker is HALF_OPEN (max calls reached)")
                self.half_open_calls += 1

        # 执行调用
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def call_async(self, func, *args, **kwargs):
        """异步调用"""
        with self.lock:
            self.stats['total_calls'] += 1

            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.config.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.stats['circuit_opens'] += 1
                else:
                    raise Exception("Circuit breaker is OPEN")

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise Exception(
                        "Circuit breaker is HALF_OPEN (max calls reached)")
                self.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """成功回调"""
        with self.lock:
            self.stats['successful_calls'] += 1

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.stats['circuit_closes'] += 1

    def _on_failure(self):
        """失败回调"""
        with self.lock:
            self.stats['failed_calls'] += 1
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态失败，立即回到熔断状态
                self.state = CircuitState.OPEN
                self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.stats['circuit_opens'] += 1

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        with self.lock:
            # 检查是否需要从 OPEN 转为 HALF_OPEN
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.config.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
        return self.state

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'current_state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    自适应限流器

    根据系统负载动态调整限流参数
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        super().__init__(config)

        # 系统负载阈值
        self.cpu_threshold = 0.8
        self.memory_threshold = 0.85

        # 降级因子
        self.degradation_factor = 0.5

    def adjust_for_load(self, cpu_usage: float, memory_usage: float):
        """根据系统负载调整限流"""
        if cpu_usage > self.cpu_threshold or memory_usage > self.memory_threshold:
            # 高负载，降低限流值
            with self.lock:
                for bucket in list(self.ip_buckets.values()) + list(self.path_buckets.values()):
                    bucket.rate *= self.degradation_factor
                    bucket.capacity = max(
                        1, int(bucket.capacity * self.degradation_factor))

    def get_current_limits(self) -> Dict[str, Any]:
        """获取当前限流配置"""
        return {
            'global_rate': self.global_bucket.rate,
            'global_capacity': self.global_bucket.capacity,
            'avg_ip_rate': sum(b.rate for b in self.ip_buckets.values()) / len(self.ip_buckets) if self.ip_buckets else 0,
            'degradation_active': any(
                b.rate < self.config.requests_per_second
                for b in list(self.ip_buckets.values()) + list(self.path_buckets.values())
            )
        }


# 示例用法
if __name__ == "__main__":
    # 测试限流器
    limiter = RateLimiter(RateLimitConfig(
        requests_per_second=2,
        burst_size=5,
        per_ip=True
    ))

    print("测试限流器:")
    for i in range(10):
        allowed, info = limiter.allow_request(
            ip="192.168.1.1", path="/api/test")
        print(f"请求{i+1}: {'允许' if allowed else '拒绝'} - {info}")

    print(f"\n限流统计：{limiter.get_stats()}")

    # 测试熔断器
    print("\n测试熔断器:")
    cb = CircuitBreaker(CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=5
    ))

    def failing_function():
        raise Exception("模拟失败")

    for i in range(5):
        try:
            cb.call(failing_function)
            print(f"调用{i+1}: 成功")
        except Exception as e:
            print(f"调用{i+1}: 失败 - {e}")

    print(f"熔断器状态：{cb.get_state().value}")
    print(f"熔断器统计：{cb.get_stats()}")
