"""Синхронный и асинхронный клиенты сервера ApiServerG."""

from __future__ import annotations

import mimetypes
import os
from collections.abc import Iterable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Union

import httpx

from ._version import __version__
from .errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    GApiError,
    error_class,
)
from .settings import API_KEY_ENV, BASE_URL_ENV, Settings
from .types import GenerateResult, Model

# Рассуждения, поиск и файлы занимают минуты: сервер ждёт Gemini до 300 секунд.
DEFAULT_TIMEOUT = httpx.Timeout(360.0, connect=15.0)

# Путь к файлу или пара «имя файла, содержимое». Имя важно: по расширению
# сервер определяет тип файла.
FileInput = Union[str, "os.PathLike[str]", tuple[str, bytes]]


class _BaseClient:
    def __init__(
        self, api_key: str | None, base_url: str | None, language: str | None
    ) -> None:
        settings = Settings() if not (api_key and base_url) else None
        key = api_key or (settings and settings.api_key)
        if not key:
            raise ValueError(f"Передайте api_key или задайте {API_KEY_ENV} в .env")
        root = base_url or (settings and settings.base_url)
        if not root:
            raise ValueError(f"Передайте base_url или задайте {BASE_URL_ENV} в .env")
        root = root.rstrip("/")
        self.base_url = root[: -len("/api")] if root.endswith("/api") else root
        self._headers = {"X-API-Key": key, "User-Agent": f"g-api-view/{__version__}"}
        if language:
            self._headers["Accept-Language"] = language

    def __repr__(self) -> str:
        # Ключ не попадает ни в repr, ни в логи.
        return f"{type(self).__name__}(base_url={self.base_url!r})"


def _generate_form(
    text: str | None, model: str | None, system_instruction: str | None, search: bool
) -> dict[str, str]:
    form = {"flag_search": "true" if search else "false"}
    if text is not None:
        form["user_message_text"] = text
    if model:
        form["model_name"] = model
    if system_instruction:
        form["system_instruction"] = system_instruction
    return form


def _file_parts(files: Iterable[FileInput], stack: ExitStack) -> list[Any]:
    parts = []
    for item in files:
        if isinstance(item, tuple):
            name, content = item
        else:
            path = Path(item)
            name, content = path.name, stack.enter_context(path.open("rb"))
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        parts.append(("files", (name, content, content_type)))
    return parts


@contextmanager
def _transport_errors() -> Iterator[None]:
    try:
        yield
    except httpx.TimeoutException as error:
        raise APITimeoutError(str(error) or "Сервер не ответил вовремя") from error
    except httpx.TransportError as error:
        raise APIConnectionError(str(error) or type(error).__name__) from error


def _status_error(response: httpx.Response) -> APIStatusError:
    try:
        body = response.json()
    except ValueError:
        body = None
    request_id = response.headers.get("X-Request-ID")
    code = None
    errors = None
    if isinstance(body, dict) and "detail" in body:
        detail = str(body["detail"])
        code = body.get("code") if isinstance(body.get("code"), int) else None
        request_id = body.get("request_id") or request_id
        errors = body.get("errors") if isinstance(body.get("errors"), list) else None
    else:
        # Например, 413 или 502 от прокси перед сервером: там не JSON.
        detail = response.text.strip()[:500] or response.reason_phrase
    return error_class(response.status_code, code)(
        response.status_code,
        detail,
        code=code,
        request_id=request_id,
        errors=errors,
    )


def _checked(response: httpx.Response) -> httpx.Response:
    if not response.is_success:
        raise _status_error(response)
    return response


def _generate_result(response: httpx.Response) -> GenerateResult:
    body = response.json()
    return GenerateResult(
        answer=body.get("answer") or "",
        grounding_links=list(body.get("grounding_links") or []),
        tokens_used=int(body.get("tokens_used") or 0),
        request_id=response.headers.get("X-Request-ID"),
    )


def _models(response: httpx.Response) -> list[Model]:
    return [
        Model(
            index=item["model_index"], name=item["model_name"], code=item["model_code"]
        )
        for item in response.json()["models"]
    ]


class Client(_BaseClient):
    """Синхронный клиент.

    Пример:
        >>> from g_api_view import Client
        >>> with Client("asg_...") as client:
        ...     print(client.ask("Привет!"))

    Args:
        api_key: Ключ ``asg_...``; если не передан, ``G_API_KEY`` из окружения
            или ``.env``.
        base_url: Адрес сервера; если не передан, ``G_API_URL`` из окружения
            или ``.env``.
        timeout: Таймаут в секундах или ``httpx.Timeout``.
        language: Язык текстов ошибок (``ru`` или ``en``); по умолчанию ``ru``.
        transport: Свой транспорт httpx, например для тестов.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        language: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(api_key, base_url, language)
        self._http = httpx.Client(
            base_url=f"{self.base_url}/api",
            headers=self._headers,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with _transport_errors():
            response = self._http.request(method, path, **kwargs)
        return _checked(response)

    def generate(
        self,
        text: str | None = None,
        *,
        files: Iterable[FileInput] = (),
        model: str | None = None,
        system_instruction: str | None = None,
        search: bool = False,
    ) -> GenerateResult:
        """Отправляет сообщение в текущий диалог и возвращает ответ модели.

        Args:
            text: Текст сообщения; нужен он или хотя бы один файл.
            files: Пути к файлам или пары ``(имя, содержимое)``.
            model: Код или название модели; по умолчанию модель номер 1.
            system_instruction: Системная инструкция.
            search: Разрешить поиск Google, если модель его поддерживает.
        """
        form = _generate_form(text, model, system_instruction, search)
        with ExitStack() as stack:
            parts = _file_parts(files, stack)
            response = self._request(
                "POST", "/generate", data=form, files=parts or None
            )
        return _generate_result(response)

    def ask(self, text: str, **kwargs: Any) -> str:
        """Как ``generate()``, но возвращает только текст ответа."""
        return self.generate(text, **kwargs).answer

    def clear_context(self) -> None:
        """Очищает историю диалога: следующий запрос начнёт новый."""
        self._request("POST", "/clear_context")

    def list_models(self) -> list[Model]:
        """Модели, доступные клиентам, по порядку."""
        return _models(self._request("GET", "/list_models"))

    def me(self) -> int:
        """ID пользователя, которому принадлежит ключ."""
        return int(self._request("GET", "/auth/me").json()["user_id"])

    def health(self) -> bool:
        """Отвечает ли сервер."""
        try:
            return self._request("GET", "/health").json().get("status") == "ok"
        except GApiError:
            return False


class AsyncClient(_BaseClient):
    """Асинхронный клиент с теми же методами, что у ``Client``.

    Пример:
        >>> async with AsyncClient("asg_...") as client:
        ...     print(await client.ask("Привет!"))
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        language: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(api_key, base_url, language)
        self._http = httpx.AsyncClient(
            base_url=f"{self.base_url}/api",
            headers=self._headers,
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with _transport_errors():
            response = await self._http.request(method, path, **kwargs)
        return _checked(response)

    async def generate(
        self,
        text: str | None = None,
        *,
        files: Iterable[FileInput] = (),
        model: str | None = None,
        system_instruction: str | None = None,
        search: bool = False,
    ) -> GenerateResult:
        """См. ``Client.generate()``."""
        form = _generate_form(text, model, system_instruction, search)
        with ExitStack() as stack:
            parts = _file_parts(files, stack)
            response = await self._request(
                "POST", "/generate", data=form, files=parts or None
            )
        return _generate_result(response)

    async def ask(self, text: str, **kwargs: Any) -> str:
        """Как ``generate()``, но возвращает только текст ответа."""
        return (await self.generate(text, **kwargs)).answer

    async def clear_context(self) -> None:
        """Очищает историю диалога: следующий запрос начнёт новый."""
        await self._request("POST", "/clear_context")

    async def list_models(self) -> list[Model]:
        """Модели, доступные клиентам, по порядку."""
        return _models(await self._request("GET", "/list_models"))

    async def me(self) -> int:
        """ID пользователя, которому принадлежит ключ."""
        return int((await self._request("GET", "/auth/me")).json()["user_id"])

    async def health(self) -> bool:
        """Отвечает ли сервер."""
        try:
            response = await self._request("GET", "/health")
        except GApiError:
            return False
        return response.json().get("status") == "ok"
