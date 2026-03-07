# -*- coding: UTF-8 -*-
"""
Web 中间件模块 V15.0

包含:
- performance: 性能优化中间件 (缓存、压缩、指标收集)
- rate_limit: 限流与熔断中间件
"""

from .performance import (
    ORJSONResponse,
    ResponseCacheMiddleware,
    PerformanceMetricsMiddleware,
    RequestLoggingMiddleware,
    setup_performance_middlewares,
    cache_response,
    get_orjson_response,
)

from .rate_limit import (
    TokenBucket,
    CircuitBreaker,
    CircuitState,
    RateLimitMiddleware,
    CircuitBreakerMiddleware,
    AdaptiveRateLimiter,
    rate_limit,
    setup_rate_limiting,
)

__all__ = [
    # Performance
    "ORJSONResponse",
    "ResponseCacheMiddleware",
    "PerformanceMetricsMiddleware",
    "RequestLoggingMiddleware",
    "setup_performance_middlewares",
    "cache_response",
    "get_orjson_response",
    # Rate Limit
    "TokenBucket",
    "CircuitBreaker",
    "CircuitState",
    "RateLimitMiddleware",
    "CircuitBreakerMiddleware",
    "AdaptiveRateLimiter",
    "rate_limit",
    "setup_rate_limiting",
]
