"""Клиент против подменённого сервера: заголовки, форма, ответы и ошибки."""

import asyncio
from email.parser import BytesParser
from email.policy import HTTP

import httpx
import pytest

from g_api_view import (
    APIConnectionError,
    APITimeoutError,
    AsyncClient,
    AuthenticationError,
    Client,
    FilesUnavailableError,
    GenerateResult,
    Model,
    RateLimitError,
    RequestTooLargeError,
    ServerError,
    Source,
    ValidationError,
    __version__,
)

KEY = "asg_" + "k" * 43
ANSWER = {
    "answer": "Привет!",
    "grounding_links": [
        "• <a href='https://example.test/?a=1&amp;b=2'>Пример &amp; Ко</a>"
    ],
    "tokens_used": 42,
    "error": None,
}


class Server:
    """Записывает запросы и отвечает, как скажет тест."""

    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return self.answer(request) if callable(self.answer) else self.answer


def reply(body, status=200, request_id="req-1"):
    return httpx.Response(status, json=body, headers={"X-Request-ID": request_id})


def client_for(answer, **options):
    server = Server(answer)
    options.setdefault("base_url", "http://api.test")
    return Client(KEY, transport=httpx.MockTransport(server), **options), server


def form(request):
    """Поля multipart-формы: строки и пары (имя файла, содержимое)."""
    head = b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n"
    message = BytesParser(policy=HTTP).parsebytes(head + request.read())
    fields = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        content = part.get_payload(decode=True)
        filename = part.get_filename()
        value = (filename, content, part.get_content_type()) if filename else content
        fields.setdefault(name, []).append(value if filename else value.decode("utf-8"))
    return fields


def test_every_request_carries_the_key_language_and_version():
    client, server = client_for(reply({"user_id": 7}), language="en")

    assert client.me() == 7

    (request,) = server.requests
    assert str(request.url) == "http://api.test/api/auth/me"
    assert request.headers["X-API-Key"] == KEY
    assert request.headers["Accept-Language"] == "en"
    assert request.headers["User-Agent"] == f"g-api-view/{__version__}"


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """A folder of its own, so no real .env or variables leak into the test."""
    monkeypatch.chdir(tmp_path)
    for name in ("G_API_KEY", "G_API_URL"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def test_key_and_address_come_from_the_dotenv_file(workdir):
    (workdir / ".env").write_text(
        f"G_API_KEY={KEY}\nG_API_URL=http://dotenv.test/api/\n", encoding="utf-8"
    )
    server = Server(reply({"status": "ok"}))

    client = Client(transport=httpx.MockTransport(server))

    assert client.health() is True
    assert str(server.requests[0].url) == "http://dotenv.test/api/health"
    assert server.requests[0].headers["X-API-Key"] == KEY
    assert KEY not in repr(client)


def test_environment_beats_dotenv_and_arguments_beat_both(workdir, monkeypatch):
    (workdir / ".env").write_text(
        "G_API_KEY=asg_from_file\nG_API_URL=http://dotenv.test\n", encoding="utf-8"
    )
    monkeypatch.setenv("G_API_URL", "http://env.test")
    server = Server(reply({"status": "ok"}))

    from_env = Client(transport=httpx.MockTransport(server))
    explicit = Client(
        KEY, base_url="http://arg.test", transport=httpx.MockTransport(server)
    )

    assert from_env.base_url == "http://env.test"
    assert explicit.base_url == "http://arg.test"
    explicit.health()
    assert server.requests[0].headers["X-API-Key"] == KEY


@pytest.mark.parametrize(
    ("dotenv", "missing"),
    [("", "G_API_KEY"), (f"G_API_KEY={KEY}\n", "G_API_URL")],
)
def test_missing_key_or_address_is_refused_before_any_request(workdir, dotenv, missing):
    (workdir / ".env").write_text(dotenv, encoding="utf-8")

    with pytest.raises(ValueError, match=missing):
        Client()


def test_generate_sends_the_form_and_files(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("заметки", encoding="utf-8")
    client, server = client_for(reply(ANSWER))

    result = client.generate(
        "Что в файлах?",
        files=[notes, ("photo.png", b"\x89PNG")],
        model="gemini-3.8-flash",
        system_instruction="Отвечай кратко",
        search=True,
    )

    (request,) = server.requests
    assert str(request.url) == "http://api.test/api/generate"
    fields = form(request)
    assert fields["user_message_text"] == ["Что в файлах?"]
    assert fields["model_name"] == ["gemini-3.8-flash"]
    assert fields["system_instruction"] == ["Отвечай кратко"]
    assert fields["flag_search"] == ["true"]
    assert fields["files"] == [
        ("notes.txt", "заметки".encode(), "text/plain"),
        ("photo.png", b"\x89PNG", "image/png"),
    ]
    assert result == GenerateResult(
        answer="Привет!",
        grounding_links=ANSWER["grounding_links"],
        tokens_used=42,
        request_id="req-1",
    )
    assert result.sources == [Source("Пример & Ко", "https://example.test/?a=1&b=2")]


def test_generate_sends_only_what_is_set():
    client, server = client_for(reply(ANSWER))

    assert client.ask("Привет") == "Привет!"

    fields = httpx.QueryParams(server.requests[0].read().decode())
    assert dict(fields) == {"flag_search": "false", "user_message_text": "Привет"}


def test_missing_file_fails_before_sending(tmp_path):
    client, server = client_for(reply(ANSWER))

    with pytest.raises(FileNotFoundError):
        client.generate("Что тут?", files=[tmp_path / "absent.pdf"])

    assert server.requests == []


def test_models_context_and_health():
    models = {
        "models": [
            {"model_index": 1, "model_name": "Gemini 3.8 Flash", "model_code": "a"},
            {"model_index": 3, "model_name": "Gemma 4", "model_code": "b"},
        ]
    }

    def answer(request):
        if request.url.path == "/api/list_models":
            return reply(models)
        return reply({"message": "ok", "user_id": 7})

    client, server = client_for(answer)

    assert client.list_models() == [
        Model(index=1, name="Gemini 3.8 Flash", code="a"),
        Model(index=3, name="Gemma 4", code="b"),
    ]
    listed = server.requests[0]
    assert (listed.method, listed.url.path) == ("GET", "/api/list_models")
    client.clear_context()

    cleared = server.requests[-1]
    assert (cleared.method, cleared.url.path) == ("POST", "/api/clear_context")
    assert cleared.read() == b""


def error(status, code, detail="ошибка", **extra):
    body = {"detail": detail, "code": code, "request_id": "req-9", **extra}
    return httpx.Response(status, json=body)


@pytest.mark.parametrize(
    ("response", "kind", "code", "detail"),
    [
        (error(401, 41), AuthenticationError, 41, "ошибка"),
        (error(413, 43), RequestTooLargeError, 43, "ошибка"),
        (error(429, 19), RateLimitError, 19, "ошибка"),
        (error(503, 35), FilesUnavailableError, 35, "ошибка"),
        # Прокси перед сервером отвечает не JSON.
        (
            httpx.Response(413, text="<html>Request Entity Too Large</html>"),
            RequestTooLargeError,
            None,
            "<html>Request Entity Too Large</html>",
        ),
        (httpx.Response(502), ServerError, None, "Bad Gateway"),
    ],
)
def test_errors_keep_the_server_code_and_detail(response, kind, code, detail):
    client, _ = client_for(response)

    with pytest.raises(kind) as raised:
        client.ask("Привет")

    assert raised.value.status_code == response.status_code
    assert (raised.value.code, raised.value.detail) == (code, detail)
    assert raised.value.request_id == ("req-9" if code else None)


def test_validation_error_lists_the_fields():
    issue = {"loc": ["body", "user_id"], "type": "int_parsing", "message": "…"}
    client, _ = client_for(error(422, 2, errors=[issue]))

    with pytest.raises(ValidationError) as raised:
        client.ask("Привет")

    assert raised.value.errors == [issue]


@pytest.mark.parametrize(
    ("failure", "kind"),
    [(httpx.ReadTimeout, APITimeoutError), (httpx.ConnectError, APIConnectionError)],
)
def test_network_failures_become_client_errors(failure, kind):
    def broken(request):
        raise failure("нет связи", request=request)

    client, _ = client_for(broken)

    with pytest.raises(kind):
        client.ask("Привет")
    assert client.health() is False


def test_long_generations_have_time_by_default():
    client, server = client_for(reply(ANSWER))

    client.ask("Подумай подольше")

    timeout = server.requests[0].extensions["timeout"]
    assert timeout["connect"] == 15.0 and timeout["read"] == 360.0


def test_async_client_works_the_same_way():
    server = Server(reply(ANSWER))

    async def run():
        async with AsyncClient(
            KEY, base_url="http://api.test", transport=httpx.MockTransport(server)
        ) as client:
            return await client.ask("Привет", model="gemini-3.8-flash")

    assert asyncio.run(run()) == "Привет!"
    assert dict(httpx.QueryParams(server.requests[0].read().decode())) == {
        "flag_search": "false",
        "user_message_text": "Привет",
        "model_name": "gemini-3.8-flash",
    }


def test_async_client_raises_the_same_errors():
    async def run():
        async with AsyncClient(
            KEY,
            base_url="http://api.test",
            transport=httpx.MockTransport(lambda request: error(401, 41)),
        ) as client:
            await client.me()

    with pytest.raises(AuthenticationError):
        asyncio.run(run())


def test_async_client_uploads_files(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("заметки", encoding="utf-8")
    server = Server(reply(ANSWER))

    async def run():
        async with AsyncClient(
            KEY, base_url="http://api.test", transport=httpx.MockTransport(server)
        ) as client:
            return await client.generate(
                "Что в файлах?", files=[notes, ("photo.png", b"\x89PNG")]
            )

    assert asyncio.run(run()).answer == "Привет!"
    assert form(server.requests[0])["files"] == [
        ("notes.txt", "заметки".encode(), "text/plain"),
        ("photo.png", b"\x89PNG", "image/png"),
    ]


def test_async_client_lists_models_with_get():
    server = Server(reply({"models": []}))

    async def run():
        async with AsyncClient(
            KEY, base_url="http://api.test", transport=httpx.MockTransport(server)
        ) as client:
            return await client.list_models()

    assert asyncio.run(run()) == []
    assert server.requests[0].method == "GET"
