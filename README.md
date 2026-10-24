# g-api-view

Python-клиент сервера ApiServerG: доступ к Google Gemini по API-ключу.
Синхронный и асинхронный, с типизированными ответами и ошибками.

## Установка

```bash
pip install git+https://github.com/Viktor3911/ApiClientG.git
```

Конкретная версия — по тегу: `...ApiClientG.git@v1.0.0`. Нужен Python 3.9+.

## Настройка

Ключ вида `asg_…` выдаёт администратор сервера (команда бота `/create_api_key`).
Регистрации, логина и пароля нет. Ключ и адрес сервера удобно держать в `.env`
в папке, откуда запускается программа (образец — `.env.example`):

```dotenv
G_API_KEY=asg_...
G_API_URL=http://127.0.0.1:8000
```

Их читает `g_api_view.Settings`. Переменные окружения важнее `.env`, а аргументы
`Client(api_key=..., base_url=...)` важнее обоих. Адреса по умолчанию нет.

## Использование

```python
from g_api_view import Client

with Client() as client:  # ключ и адрес из .env
    print(client.ask("Привет!"))

    result = client.generate(
        "Что на картинке и в документе?",
        files=["photo.jpg", ("notes.txt", b"текст")],
        model="gemini-3.8-flash",
        system_instruction="Отвечай кратко",
        search=True,
    )
    print(result.answer, result.tokens_used)
    for source in result.sources:
        print(source.title, source.url)

    client.clear_context()  # следующий запрос начнёт новый диалог
```

Асинхронно — то же самое через `AsyncClient`:

```python
from g_api_view import AsyncClient

async with AsyncClient() as client:  # ключ и адрес из .env
    answer = await client.ask("Привет!")
```

Сервер помнит историю диалога: каждый `generate()` продолжает её, пока не
вызван `clear_context()`.

## Методы

| Метод | Что делает |
| --- | --- |
| `generate(text, files=(), model=None, system_instruction=None, search=False)` | Ответ модели: `GenerateResult` |
| `ask(text, **kwargs)` | То же, но только текст ответа |
| `clear_context()` | Очистить историю диалога |
| `list_models()` | Доступные модели: `Model(index, name, code)` |
| `me()` | ID пользователя, которому принадлежит ключ |
| `health()` | `True`, если сервер отвечает |

- `model` — код (`gemini-3.8-flash`) или название из `list_models()`; без него
  берётся модель номер 1.
- `files` — пути к файлам или пары `(имя, содержимое)`. Имя важно: по расширению
  сервер определяет тип файла. Всё тело запроса — не больше 100 МБ.
- `GenerateResult.grounding_links` — ссылки поиска так, как их отдаёт сервер
  (HTML-строки для Telegram); `GenerateResult.sources` — те же ссылки как пары
  `title`, `url`.

Параметры `Client`: `api_key`, `base_url`, `timeout` (по умолчанию 360 секунд на
ответ и 15 на соединение: рассуждения модели идут минутами), `language` (`ru`
или `en` — язык текстов ошибок). Прокси берётся из `HTTPS_PROXY`.

## Ошибки

Все исключения наследуют `GApiError`. Ошибка от сервера — `APIStatusError` с
полями `status_code`, `code` (числовой код сервера), `detail` (текст) и
`request_id` (для поиска в логах сервера).

| Исключение | Когда |
| --- | --- |
| `AuthenticationError` | 401: нет ключа, ключ неверный или отозван |
| `PermissionDeniedError` | 403: например, учётная запись отключена |
| `NotFoundError` | 404: например, неизвестная модель |
| `RequestTooLargeError` | 413: файлы больше лимита |
| `ValidationError` | 422: неверные параметры, подробности в `errors` |
| `RateLimitError` | 429: исчерпана квота у Gemini |
| `FilesUnavailableError` | код 35: очистите контекст и приложите файлы заново |
| `ServerError` | 5xx |
| `APITimeoutError`, `APIConnectionError` | сервер не ответил или недоступен |

```python
from g_api_view import Client, GApiError, RateLimitError

try:
    answer = Client().ask("Привет!")
except RateLimitError:
    ...  # подождать и повторить
except GApiError as error:
    print("Не получилось:", error)
```

## Разработка

```bash
uv sync
uv run pytest
uv run ruff check .
uv build  # wheel и sdist в dist/
```

## Лицензия

MIT
