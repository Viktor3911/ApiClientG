"""Клиент ApiServerG: доступ к Google Gemini по API-ключу."""

from ._version import __version__
from .client import AsyncClient, Client
from .errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    FilesUnavailableError,
    GApiError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    RequestTooLargeError,
    ServerError,
    ValidationError,
)
from .settings import Settings
from .types import GenerateResult, Model, Source

__all__ = [
    "APIConnectionError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncClient",
    "AuthenticationError",
    "Client",
    "FilesUnavailableError",
    "GApiError",
    "GenerateResult",
    "Model",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "RequestTooLargeError",
    "ServerError",
    "Settings",
    "Source",
    "ValidationError",
    "__version__",
]
