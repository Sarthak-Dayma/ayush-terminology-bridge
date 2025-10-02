"""
Custom middleware for AYUSH Terminology Bridge API
Handles: Audit logging, Rate limiting, Request timing, CORS, Security headers
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import time
from typing import Callable, Optional
import json
from collections import defaultdict
from datetime import datetime, timedelta

from services.audit_service import AuditService
from services.abha_auth import AuthMiddleware as ABHAAuthMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests to audit trail
    Captures: endpoint, method, user, IP, timing, response status
    """
    
    def __init__(self, app, audit_service: AuditService, auth_middleware: ABHAAuthMiddleware):
        super().__init__(app)
        self.audit_service = audit_service
        self.auth_middleware = auth_middleware
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Extract user info if available
        auth_header = request.headers.get('authorization')
        user_id = None
        user_role = None
        
        if auth_header:
            user = self.auth_middleware.authenticate_request(auth_header)
            if user:
                user_id = user.get('user_id')
                user_role = user.get('role')
        
        # Store request details for potential error logging
        request.state.start_time = start_time
        request.state.user_id = user_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Log to audit trail (skip health checks)
            if not request.url.path.endswith('/health'):
                self.audit_service.log_api_call(
                    action_type=f"{request.method}_{request.url.path}",
                    user_id=user_id,
                    user_role=user_role,
                    endpoint=str(request.url.path),
                    method=request.method,
                    ip_address=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get('user-agent'),
                    response_status=response.status_code,
                    response_time_ms=response_time
                )
            
            # Add custom headers
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            response.headers["X-API-Version"] = "2.0.0"
            
            return response
            
        except Exception as e:
            # Log error
            response_time = (time.time() - start_time) * 1000
            
            self.audit_service.log_api_call(
                action_type=f"ERROR_{request.method}_{request.url.path}",
                user_id=user_id,
                user_role=user_role,
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get('user-agent'),
                response_status=500,
                response_time_ms=response_time,
                metadata={'error': str(e)}
            )
            
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware
    Limits: 100 requests per minute per IP
    """
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path.endswith('/health'):
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Clean old entries
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if req_time > cutoff_time
        ]
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per {self.window_seconds} seconds",
                    "retry_after": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.max_requests - len(self.request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((current_time + timedelta(seconds=self.window_seconds)).timestamp()))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    Protects against: XSS, clickjacking, MIME sniffing
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Detailed request/response logging for debugging
    Logs request body and response for non-health endpoints
    """
    
    def __init__(self, app, log_bodies: bool = False):
        super().__init__(app)
        self.log_bodies = log_bodies
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks
        if request.url.path.endswith('/health'):
            return await call_next(request)
        
        # Log request
        print(f"\n{'='*60}")
        print(f"[{datetime.now().isoformat()}] {request.method} {request.url.path}")
        print(f"Client: {request.client.host if request.client else 'unknown'}")
        print(f"User-Agent: {request.headers.get('user-agent', 'N/A')}")
        
        # Log request body if enabled (be careful with sensitive data)
        if self.log_bodies and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    print(f"Request Body: {body.decode('utf-8')[:500]}")  # Limit to 500 chars
            except:
                pass
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        response_time = (time.time() - start_time) * 1000
        
        # Log response
        print(f"Status: {response.status_code}")
        print(f"Response Time: {response_time:.2f}ms")
        print(f"{'='*60}\n")
        
        return response


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory cache for GET requests
    Caches: Terminology lookups, ICD-11 entities
    """
    
    def __init__(self, app, ttl_seconds: int = 300):
        super().__init__(app)
        self.cache = {}
        self.ttl_seconds = ttl_seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Skip caching for certain endpoints
        skip_paths = ['/health', '/audit', '/analytics']
        if any(path in request.url.path for path in skip_paths):
            return await call_next(request)
        
        # Generate cache key
        cache_key = f"{request.method}:{request.url.path}:{request.url.query}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            
            # Check if cache is still valid
            if (datetime.now() - cached_time).total_seconds() < self.ttl_seconds:
                # Return cached response
                return JSONResponse(
                    content=cached_data,
                    headers={"X-Cache": "HIT", "X-Cache-Age": str(int((datetime.now() - cached_time).total_seconds()))}
                )
        
        # Process request
        response = await call_next(request)
        
        # Cache successful GET responses
        if response.status_code == 200 and request.method == "GET":
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Parse JSON
                response_data = json.loads(body.decode())
                
                # Store in cache
                self.cache[cache_key] = (response_data, datetime.now())
                
                # Clean old cache entries (keep last 1000)
                if len(self.cache) > 1000:
                    # Remove oldest 200 entries
                    sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])
                    for key in sorted_keys[:200]:
                        del self.cache[key]
                
                # Return new response
                return JSONResponse(
                    content=response_data,
                    headers={"X-Cache": "MISS"}
                )
            except:
                pass
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware
    Catches unhandled exceptions and returns structured error responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Log error
            print(f"[ERROR] Unhandled exception in {request.url.path}: {str(e)}")
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e),
                    "path": request.url.path,
                    "method": request.method,
                    "timestamp": datetime.now().isoformat()
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collect API metrics for monitoring
    Tracks: Request counts, response times, error rates
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "endpoint_counts": defaultdict(int),
            "response_times": defaultdict(list),
            "status_codes": defaultdict(int)
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Update metrics
            self.metrics["total_requests"] += 1
            self.metrics["endpoint_counts"][request.url.path] += 1
            self.metrics["status_codes"][response.status_code] += 1
            
            response_time = (time.time() - start_time) * 1000
            self.metrics["response_times"][request.url.path].append(response_time)
            
            # Keep only last 100 response times per endpoint
            if len(self.metrics["response_times"][request.url.path]) > 100:
                self.metrics["response_times"][request.url.path] = \
                    self.metrics["response_times"][request.url.path][-100:]
            
            if response.status_code >= 400:
                self.metrics["total_errors"] += 1
            
            return response
            
        except Exception as e:
            self.metrics["total_errors"] += 1
            raise
    
    def get_metrics(self):
        """Get current metrics"""
        metrics_summary = {
            "total_requests": self.metrics["total_requests"],
            "total_errors": self.metrics["total_errors"],
            "error_rate": self.metrics["total_errors"] / max(self.metrics["total_requests"], 1),
            "top_endpoints": sorted(
                self.metrics["endpoint_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "status_codes": dict(self.metrics["status_codes"]),
            "avg_response_times": {
                endpoint: sum(times) / len(times) if times else 0
                for endpoint, times in self.metrics["response_times"].items()
            }
        }
        return metrics_summary


# Utility function to configure all middleware
def configure_middleware(app, services):
    """
    Configure all middleware in correct order
    Order matters: Security -> CORS -> Rate Limit -> Cache -> Audit -> Metrics -> Error Handling
    """
    
    # 1. Security headers (first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 2. CORS (already added in main.py, but here for reference)
    # app.add_middleware(CORSMiddleware, ...)
    
    # 3. Rate limiting
    app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
    
    # 4. Cache middleware
    app.add_middleware(CacheMiddleware, ttl_seconds=300)
    
    # 5. Audit logging
    app.add_middleware(
        AuditMiddleware,
        audit_service=services.audit_service,
        auth_middleware=services.auth_middleware
    )
    
    # 6. Metrics collection
    metrics_middleware = MetricsMiddleware(app)
    app.add_middleware(MetricsMiddleware)
    
    # 7. Request logging (development only)
    # app.add_middleware(RequestLoggingMiddleware, log_bodies=False)
    
    # 8. Error handling (last)
    app.add_middleware(ErrorHandlingMiddleware)
    
    return metrics_middleware  # Return for metrics endpoint access


# Health check enhancement
def create_health_check_response(services, metrics_middleware=None):
    """Create comprehensive health check response"""
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "namaste_parser": "active" if services.namaste_parser else "inactive",
            "icd11_client": "active" if services.icd_client else "inactive",
            "mapping_engine": "active" if services.mapping_engine else "inactive",
            "fhir_generator": "active" if services.fhir_gen else "inactive",
            "ml_matcher": "active" if services.ml_matcher else "inactive",
            "audit_service": "active" if services.audit_service else "inactive",
            "auth_service": "active" if services.auth_service else "inactive"
        }
    }
    
    # Add metrics if available
    if metrics_middleware:
        health_status["metrics"] = metrics_middleware.get_metrics()
    
    return health_status