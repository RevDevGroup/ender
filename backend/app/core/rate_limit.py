"""
Rate limiting configuration using SlowAPI.

This module configures rate limiting to protect the API from abuse.
Uses in-memory storage by default (suitable for single-instance deployments).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


# Custom key function that uses X-Forwarded-For header if behind a proxy
def get_client_ip(request) -> str:
    """
    Get the client IP address, handling proxy headers.

    Priority:
    1. X-Forwarded-For header (first IP)
    2. X-Real-IP header
    3. Direct connection IP
    """
    # Check for proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, get the first (client IP)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    return get_remote_address(request)


# Initialize the limiter with in-memory storage
# For production with multiple instances, consider using Redis:
# limiter = Limiter(key_func=get_client_ip, storage_uri="redis://localhost:6379")
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    enabled=settings.RATE_LIMIT_ENABLED,
)


# Rate limit configurations for different endpoint types
class RateLimits:
    """
    Predefined rate limits for different endpoint categories.

    Format: "X per Y" where Y can be second, minute, hour, day
    Examples: "5/minute", "100/hour", "1000/day"
    """

    # Authentication endpoints (strict to prevent brute force)
    AUTH_LOGIN = "5/minute"
    AUTH_SIGNUP = "3/minute"
    AUTH_PASSWORD_RESET = "3/minute"
    AUTH_EMAIL_VERIFICATION = "5/minute"

    # API endpoints (normal usage)
    API_READ = "60/minute"
    API_WRITE = "30/minute"

    # SMS endpoints (can be expensive)
    SMS_SEND = "10/minute"

    # Webhook endpoints (external calls)
    WEBHOOK = "100/minute"

    # Admin endpoints
    ADMIN = "30/minute"
