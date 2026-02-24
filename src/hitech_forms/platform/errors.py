from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def bad_request(message: str) -> AppError:
    return AppError(code="bad_request", message=message, status_code=400)


def unauthorized(message: str = "admin token required") -> AppError:
    return AppError(code="unauthorized", message=message, status_code=401)


def forbidden(message: str = "forbidden") -> AppError:
    return AppError(code="forbidden", message=message, status_code=403)


def not_found(message: str) -> AppError:
    return AppError(code="not_found", message=message, status_code=404)


def conflict(message: str) -> AppError:
    return AppError(code="conflict", message=message, status_code=409)


def rate_limited(message: str = "rate limit exceeded") -> AppError:
    return AppError(code="rate_limited", message=message, status_code=429)
