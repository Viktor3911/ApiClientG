"""Ответы сервера."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

# Сервер отдаёт ссылки поиска готовыми строками "• <a href='url'>title</a>".
_LINK = re.compile(r"<a href='([^']*)'>(.*?)</a>")


@dataclass(frozen=True)
class Source:
    """Источник из поиска Google."""

    title: str
    url: str


@dataclass(frozen=True)
class GenerateResult:
    """Ответ модели.

    Attributes:
        answer: Текст ответа.
        grounding_links: Ссылки поиска как их отдаёт сервер: HTML-строки
            вида ``• <a href='url'>title</a>``, удобные для Telegram.
        tokens_used: Сколько токенов ушло, включая рассуждения.
        request_id: ID запроса на сервере.
    """

    answer: str
    grounding_links: list[str] = field(default_factory=list)
    tokens_used: int = 0
    request_id: str | None = None

    @property
    def sources(self) -> list[Source]:
        """Ссылки поиска как пары «заголовок, адрес»."""
        found = []
        for link in self.grounding_links:
            match = _LINK.search(link)
            if match:
                url, title = match.groups()
                found.append(Source(html.unescape(title), html.unescape(url)))
        return found


@dataclass(frozen=True)
class Model:
    """Модель, доступная клиентам.

    Attributes:
        index: Порядковый номер; модель с номером 1 используется по умолчанию.
        name: Название для людей.
        code: Код модели, его и передают в ``generate(model=...)``.
    """

    index: int
    name: str
    code: str
