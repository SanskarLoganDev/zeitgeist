from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.cache import cache
from rest_framework.request import Request


class AuthRateLimitError(Exception):
    """Raised when a public auth endpoint receives too many attempts."""


def enforce_auth_rate_limit(
    request: Request,
    *,
    scope: str,
    email: str | None = None,
) -> None:
    """Apply per-IP and optional per-email limits for auth endpoints."""
    ip_identifier = _client_ip(request)
    _increment_or_raise(
        key_parts=("ip", scope, ip_identifier),
        limit=settings.AUTH_RATE_LIMIT_IP_REQUESTS,
    )

    if email:
        _increment_or_raise(
            key_parts=("email", scope, email.strip().lower()),
            limit=settings.AUTH_RATE_LIMIT_EMAIL_REQUESTS,
        )


def _increment_or_raise(*, key_parts: tuple[str, ...], limit: int) -> None:
    cache_key = _cache_key(key_parts)
    timeout = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS

    added = cache.add(cache_key, 1, timeout=timeout)
    if added:
        return

    try:
        attempts = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=timeout)
        return

    if attempts > limit:
        raise AuthRateLimitError


def _cache_key(key_parts: tuple[str, ...]) -> str:
    raw_key = ":".join(key_parts)
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"accounts:auth-rate-limit:{digest}"


def _client_ip(request: Request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return str(forwarded_for.split(",")[0].strip())
    remote_addr = request.META.get("REMOTE_ADDR", "")
    return str(remote_addr or "unknown")
