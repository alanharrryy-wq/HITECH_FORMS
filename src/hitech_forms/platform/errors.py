from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def bad_request(message: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError(code="bad_request", message=message, status_code=400, details=details)


def unauthorized(message: str = "admin token required", details: dict[str, Any] | None = None) -> AppError:
    return AppError(code="unauthorized", message=message, status_code=401, details=details)


def forbidden(message: str = "forbidden", details: dict[str, Any] | None = None) -> AppError:
    return AppError(code="forbidden", message=message, status_code=403, details=details)


def not_found(message: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError(code="not_found", message=message, status_code=404, details=details)


def conflict(message: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError(code="conflict", message=message, status_code=409, details=details)


def rate_limited(message: str = "rate limit exceeded", details: dict[str, Any] | None = None) -> AppError:
    return AppError(code="rate_limited", message=message, status_code=429, details=details)
