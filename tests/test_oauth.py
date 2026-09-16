from __future__ import annotations

from urllib.parse import parse_qs

import pytest

from instapaper import AccessToken, OAuth, OAuthError, User, __version__

from .conftest import FakeTransport, split_url


@pytest.fixture
def oauth(transport: FakeTransport) -> OAuth:
    return OAuth("client-id", "client-secret", "https://app.example.com/callback", transport=transport)


def test_authorization_url(oauth: OAuth) -> None:
    url, query = split_url(oauth.authorization_url(state="xyz 123"))

    assert url == "https://www.instapaper.com/oauth2/authorize"
    assert query == {
        "client_id": ["client-id"],
        "redirect_uri": ["https://app.example.com/callback"],
        "response_type": ["code"],
        "state": ["xyz 123"],
    }


def test_authorization_url_without_state(transport: FakeTransport) -> None:
    oauth = OAuth("id", "secret", "https://app.example.com/cb", base_url="https://staging.example.com/")
    url, query = split_url(oauth.authorization_url())
    assert url == "https://staging.example.com/oauth2/authorize"
    assert "state" not in query


def test_exchange_code(oauth: OAuth, transport: FakeTransport) -> None:
    transport.queue(
        {
            "token_type": "Bearer",
            "access_token": "aabbccdd11223344",
            "user": {"id": 42, "username": "reader@example.com"},
        }
    )

    token = oauth.exchange_code("1a2b3c4d")

    request = transport.last
    assert request.method == "POST"
    assert request.url == "https://www.instapaper.com/oauth2/token"
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.headers["User-Agent"] == f"instapaper-api-python/{__version__}"
    assert "Authorization" not in request.headers
    assert request.body is not None
    assert parse_qs(request.body.decode()) == {
        "client_id": ["client-id"],
        "client_secret": ["client-secret"],
        "redirect_uri": ["https://app.example.com/callback"],
        "code": ["1a2b3c4d"],
    }
    # The token response's user carries no premium flag.
    assert token == AccessToken(
        access_token="aabbccdd11223344",
        token_type="Bearer",
        user=User(id=42, username="reader@example.com", premium=None),
    )
    assert "aabbccdd11223344" not in repr(token)


@pytest.mark.parametrize(
    ("status", "error"),
    [(400, "invalid_grant"), (401, "invalid_client"), (403, "unauthorized_client")],
)
def test_exchange_code_errors(oauth: OAuth, transport: FakeTransport, status: int, error: str) -> None:
    transport.queue({"error": error, "error_description": "Explained."}, status=status)

    with pytest.raises(OAuthError) as info:
        oauth.exchange_code("code")

    assert info.value.status == status
    assert info.value.error == error
    assert info.value.description == "Explained."
    assert str(info.value) == "Explained."
    assert repr(info.value) == f"OAuthError(status={status}, error='{error}', description='Explained.')"


def test_exchange_code_error_without_body(oauth: OAuth, transport: FakeTransport) -> None:
    transport.queue(raw=b"<html>oops</html>", status=502)

    with pytest.raises(OAuthError) as info:
        oauth.exchange_code("code")

    assert info.value.error is None
    assert str(info.value) == "OAuth request failed with status 502"


def test_exchange_code_without_access_token(oauth: OAuth, transport: FakeTransport) -> None:
    transport.queue({"token_type": "Bearer"})
    with pytest.raises(OAuthError):
        oauth.exchange_code("code")


def test_repr_hides_secret(oauth: OAuth) -> None:
    assert "client-secret" not in repr(oauth)
