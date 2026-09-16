from __future__ import annotations

import pytest

from instapaper import (
    APIError,
    AuthenticationError,
    BadRequestError,
    Instapaper,
    NotFoundError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    User,
    __version__,
)

from .conftest import BASE, FakeTransport


def test_requires_access_token() -> None:
    with pytest.raises(ValueError):
        Instapaper("")


def test_me_sends_auth_headers(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"id": 42, "username": "reader@example.com", "premium": True})

    user = client.me()

    assert user == User(id=42, username="reader@example.com", premium=True)
    request = transport.last
    assert request.method == "GET"
    assert request.url == f"{BASE}/me"
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Accept"] == "application/json"
    assert request.headers["User-Agent"] == f"instapaper-api-python/{__version__}"
    assert "Content-Type" not in request.headers
    assert request.body is None
    assert request.timeout == 30.0


def test_base_url_and_timeout_are_configurable(transport: FakeTransport) -> None:
    client = Instapaper("t", base_url="https://staging.example.com/", timeout=5, transport=transport)
    transport.queue({"id": 1, "username": "u", "premium": False})

    client.me()

    assert transport.last.url == "https://staging.example.com/api/2/me"
    assert transport.last.timeout == 5


def test_repr_hides_token(client: Instapaper) -> None:
    assert "test-token" not in repr(client)


@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (402, QuotaExceededError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
        (418, APIError),
    ],
)
def test_error_statuses_map_to_exceptions(
    client: Instapaper, transport: FakeTransport, status: int, error_class: type[APIError]
) -> None:
    body = {"error": {"code": status, "message": "Something specific"}}
    transport.queue(body, status=status)

    with pytest.raises(error_class) as info:
        client.me()

    assert type(info.value) is error_class
    assert info.value.status == status
    assert info.value.message == "Something specific"
    assert str(info.value) == "Something specific"
    assert info.value.body == body


def test_empty_401_body_gets_a_default_message(client: Instapaper, transport: FakeTransport) -> None:
    # A bad or missing token comes back as a bare 401 with no body.
    transport.queue(status=401)

    with pytest.raises(AuthenticationError) as info:
        client.me()

    assert info.value.message == "Authentication failed"
    assert info.value.body is None


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (400, "Bad request"),
        (402, "Quota exceeded"),
        (403, "Permission denied"),
        (404, "Not found"),
        (429, "Rate limit exceeded"),
        (502, "Server error"),
        (418, "Request failed with status 418"),
    ],
)
def test_non_json_error_body_falls_back(
    client: Instapaper, transport: FakeTransport, status: int, message: str
) -> None:
    transport.queue(raw=b"<html>Bad Gateway</html>", status=status)

    with pytest.raises(APIError) as info:
        client.me()

    assert info.value.message == message
    assert info.value.body == "<html>Bad Gateway</html>"


def test_json_error_without_message_falls_back(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"error": "nope"}, status=403)

    with pytest.raises(PermissionDeniedError) as info:
        client.me()

    assert info.value.message == "Permission denied"


def test_non_json_success_body_raises(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(raw=b"not json", status=200)

    with pytest.raises(APIError) as info:
        client.me()

    assert info.value.status == 200
    assert info.value.body == "not json"


def test_empty_success_body_where_object_expected_raises(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(status=200)

    with pytest.raises(APIError):
        client.me()


def test_error_repr(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(status=429)
    with pytest.raises(RateLimitError) as info:
        client.me()
    assert repr(info.value) == "RateLimitError(status=429, message='Rate limit exceeded')"
