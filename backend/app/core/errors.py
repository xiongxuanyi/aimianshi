"""类型化错误层级。"""
from typing import Any


class AppError(Exception):
    """应用业务错误基类。"""

    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any = ""):
        detail = f"{resource} 不存在"
        if identifier != "":
            detail += f": {identifier}"
        super().__init__(detail, "NOT_FOUND", 404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权限执行此操作"):
        super().__init__(message, "FORBIDDEN", 403)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 422)
