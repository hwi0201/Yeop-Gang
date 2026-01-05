"""
Rate Limiting 미들웨어
- API 호출 제한
- IP 및 사용자별 제한
"""
import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimiter:
    """간단한 메모리 기반 Rate Limiter (프로덕션에서는 Redis 사용 권장)"""
    
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.max_requests: int = 100  # 시간당 최대 요청 수
        self.window_seconds: int = 3600  # 1시간
    
    def is_allowed(self, key: str) -> tuple[bool, Optional[int]]:
        """요청이 허용되는지 확인"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # 오래된 요청 제거
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        # 요청 수 확인
        if len(self.requests[key]) >= self.max_requests:
            # 남은 시간 계산
            if self.requests[key]:
                oldest_request = min(self.requests[key])
                reset_time = int(oldest_request + self.window_seconds - now)
                return False, reset_time
            return False, self.window_seconds
        
        # 요청 기록
        self.requests[key].append(now)
        return True, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting 미들웨어"""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 3600):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.rate_limiter.max_requests = max_requests
        self.rate_limiter.window_seconds = window_seconds
    
    async def dispatch(self, request: Request, call_next):
        # 헬스체크는 제외
        if request.url.path in ["/api/health", "/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Rate limit key 생성 (IP 주소 또는 사용자 ID)
        client_ip = request.client.host if request.client else "unknown"
        
        # 인증된 사용자의 경우 사용자 ID 사용
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from core.dh_auth import decode_access_token
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("sub")
            except Exception:
                pass
        
        rate_limit_key = f"{user_id}:{client_ip}" if user_id else f"anon:{client_ip}"
        
        # Rate limit 확인
        allowed, reset_time = self.rate_limiter.is_allowed(rate_limit_key)
        
        if not allowed:
            response = Response(
                content=f'{{"detail": "Rate limit exceeded. Try again in {reset_time} seconds."}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
            )
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.max_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_time)
            return response
        
        # 요청 처리
        response = await call_next(request)
        
        # Rate limit 헤더 추가
        remaining = self.rate_limiter.max_requests - len(self.rate_limiter.requests[rate_limit_key])
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.rate_limiter.window_seconds)
        
        return response

