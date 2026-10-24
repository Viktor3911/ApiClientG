"""Исключения клиента.

Сервер отвечает на ошибку JSON вида ``{"detail", "code", "request_id"}``;
``detail`` уже переведён на язык из ``Accept-Language``. Прокси перед
сервером (Caddy) может ответить и не JSON, тогда ``code`` будет ``None``.
"""

from __future__ import annotations

from typing import Any

# Файлы диалога загружены под ключом Gemini, который сейчас недоступен.
FILES_KEY_UNAVAILABLE = 35
# Тело запроса больше лимита сервера (по умолчанию 100 МБ).
REQUEST_TOO_LARGE = 43


class GApiError(Exception):
    """Базовое исключение клиента."""


class APIConnectionError(GApiError):
    """Не удалось связаться с сервером."""


class APITimeoutError(APIConnectionError):
    """Сервер не ответил за отведённое время."""


class APIStatusError(GApiError):
    """Сервер ответил ошибкой.

    Attributes:
        status_code: HTTP-статус ответа.
        detail: Текст ошибки от сервера.
        code: Числовой код ошибки сервера или ``None``, если ответ не JSON.
        request_id: ID запроса для поиска в логах сервера.
        errors: Ошибки отдельных полей при 422.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        code: int | None = None,
        request_id: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(f"{status_code}: {detail}" if detail else str(status_code))
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.request_id = request_id
        self.errors = errors or []


class AuthenticationError(APIStatusError):
    """401: API-ключ не передан, неверен или отозван."""


class PermissionDeniedError(APIStatusError):
    """403: например, учётная запись отключена."""


class NotFoundError(APIStatusError):
    """404: например, неизвестная модель."""


class RequestTooLargeError(APIStatusError):
    """413: тело запроса (файлы) больше лимита сервера."""


class ValidationError(APIStatusError):
    """422: неверные параметры запроса, подробности в ``errors``."""


class RateLimitError(APIStatusError):
    """429: исчерпана квота у Gemini."""


class ServerError(APIStatusError):
    """5xx: ошибка на сервере или у Gemini."""


class FilesUnavailableError(ServerError):
    """Файлы диалога привязаны к недоступному ключу Gemini.

    Очистите контекст (``clear_context()``) и приложите файлы заново.
    """


_BY_STATUS: dict[int, type[APIStatusError]] = {
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    413: RequestTooLargeError,
    422: ValidationError,
    429: RateLimitError,
}


def error_class(status_code: int, code: int | None) -> type[APIStatusError]:
    if code == FILES_KEY_UNAVAILABLE:
        return FilesUnavailableError
    if status_code in _BY_STATUS:
        return _BY_STATUS[status_code]
    return ServerError if status_code >= 500 else APIStatusError
