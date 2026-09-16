from __future__ import annotations

import http.client
import io
import urllib.error
from email.message import Message
from typing import Any

import pytest

from instapaper import HTTPRequest, Instapaper, InstapaperConnectionError, NotFoundError, User
from instapaper import _transport as transport_module
from instapaper._transport import decode_body, urllib_transport


class FakeResponse:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self._body = body
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def patch_open(monkeypatch: pytest.MonkeyPatch, handler: Any) -> list[Any]:
    calls: list[Any] = []

    def fake_open(request: Any, timeout: float) -> Any:
        calls.append((request, timeout))
        return handler(request)

    monkeypatch.setattr(transport_module._opener, "open", fake_open)
    return calls


def test_urllib_transport_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = patch_open(monkeypatch, lambda request: FakeResponse(200, b'{"ok": true}', {"X-Test": "1"}))

    response = urllib_transport(
        HTTPRequest(
            method="POST",
            url="https://www.instapaper.com/api/2/folders",
            headers={"Authorization": "Bearer t", "Content-Type": "application/json"},
            body=b'{"title": "x"}',
            timeout=12,
        )
    )

    assert response.status == 200
    assert response.body == b'{"ok": true}'
    assert response.headers["X-Test"] == "1"
    request, timeout = calls[0]
    assert timeout == 12
    assert request.get_method() == "POST"
    assert request.full_url == "https://www.instapaper.com/api/2/folders"
    assert request.data == b'{"title": "x"}'
    assert request.get_header("Authorization") == "Bearer t"


def test_urllib_transport_returns_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_http_error(request: Any) -> Any:
        headers = Message()
        headers["Content-Type"] = "application/json"
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", headers, io.BytesIO(b'{"error": {}}'))

    patch_open(monkeypatch, raise_http_error)

    response = urllib_transport(HTTPRequest(method="GET", url="https://www.instapaper.com/api/2/nope"))

    assert response.status == 404
    assert response.body == b'{"error": {}}'
    assert response.headers["Content-Type"] == "application/json"


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("Name or service not known"),
        TimeoutError("timed out"),
        ConnectionResetError("reset"),
        http.client.RemoteDisconnected("closed"),
    ],
)
def test_urllib_transport_wraps_connection_errors(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def raise_error(request: Any) -> Any:
        raise error

    patch_open(monkeypatch, raise_error)

    with pytest.raises(InstapaperConnectionError) as info:
        urllib_transport(HTTPRequest(method="GET", url="https://www.instapaper.com/api/2/me"))

    assert info.value.__cause__ is error


def test_client_uses_urllib_transport_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = patch_open(monkeypatch, lambda request: FakeResponse(200, b'{"id": 1, "username": "u", "premium": false}'))

    user = Instapaper("token").me()

    assert user == User(id=1, username="u", premium=False)
    request, _ = calls[0]
    assert request.get_header("Authorization") == "Bearer token"


def test_client_maps_urllib_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_http_error(request: Any) -> Any:
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", Message(), io.BytesIO(b""))

    patch_open(monkeypatch, raise_http_error)

    with pytest.raises(NotFoundError):
        Instapaper("token").me()


def test_redirects_are_returned_not_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    # A redirect would resend the Authorization header wherever it points, so urllib
    # hands it back as an HTTPError and the transport returns the 3xx response as-is.
    handler = transport_module._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", Message(), "https://elsewhere.example.com") is None

    def raise_redirect(request: Any) -> Any:
        raise urllib.error.HTTPError(request.full_url, 302, "Found", Message(), io.BytesIO(b""))

    patch_open(monkeypatch, raise_redirect)
    response = urllib_transport(HTTPRequest(method="GET", url="https://www.instapaper.com/api/2/me"))
    assert response.status == 302


def test_urllib_transport_tolerates_unreadable_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenBody(io.BytesIO):
        def read(self, *args: Any) -> bytes:
            raise OSError("connection dropped")

    def raise_http_error(request: Any) -> Any:
        raise urllib.error.HTTPError(request.full_url, 500, "Server Error", None, BrokenBody())  # type: ignore[arg-type]

    patch_open(monkeypatch, raise_http_error)

    response = urllib_transport(HTTPRequest(method="GET", url="https://www.instapaper.com/api/2/me"))

    assert response.status == 500
    assert response.body == b""
    assert response.headers == {}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b"", None),
        (b"  \n", None),
        (b'{"a": 1}', {"a": 1}),
        (b"[1, 2]", [1, 2]),
        (b"plain text", "plain text"),
    ],
)
def test_decode_body(body: bytes, expected: Any) -> None:
    assert decode_body(body) == expected


def test_request_json_helper() -> None:
    assert HTTPRequest(method="GET", url="u").json() is None
    assert HTTPRequest(method="POST", url="u", body=b'{"a": 1}').json() == {"a": 1}
