"""Exceptions raised by the Instapaper API client."""

from __future__ import annotations

from typing import Any

_DEFAULT_MESSAGES = {
    400: "Bad request",
    401: "Authentication failed",
    402: "Quota exceeded",
    403: "Permission denied",
    404: "Not found",
    429: "Rate limit exceeded",
}


class InstapaperError(Exception):
    """Base class for every error this library raises."""


class InstapaperConnectionError(InstapaperError):
    """The request never got a response: DNS failure, refused connection, timeout, and so on."""


class APIError(InstapaperError):
    """The API answered with an error status.

    Attributes:
        status: The HTTP status code.
        message: The server's message, or a generic one when the body didn't carry one.
        body: The parsed JSON body, the raw text if it wasn't JSON, or None if it was empty.
    """

    def __init__(self, status: int, message: str, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.body = body

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status!r}, message={self.message!r})"


class BadRequestError(APIError):
    """400: the request was malformed, or an argument was missing or invalid."""


class AuthenticationError(APIError):
    """401: the access token is missing, unknown, or revoked."""


class QuotaExceededError(APIError):
    """402: an external quota is exhausted, such as Instaparser credits."""


class PermissionDeniedError(APIError):
    """403: authenticated, but not allowed (unapproved or suspended application, subscriber-only feature)."""


class NotFoundError(APIError):
    """404: no such endpoint."""


class RateLimitError(APIError):
    """429: too many requests. Back off and retry later."""


class ServerError(APIError):
    """5xx: something went wrong on Instapaper's side. Retry with backoff."""


class OAuthError(InstapaperError):
    """The OAuth 2 token endpoint rejected a request.

    Attributes:
        status: The HTTP status code.
        error: The OAuth error code, e.g. ``invalid_grant``, when the server sent one.
        description: The server's human-readable description, when it sent one.
    """

    def __init__(self, status: int, error: str | None, description: str | None) -> None:
        super().__init__(description or error or f"OAuth request failed with status {status}")
        self.status = status
        self.error = error
        self.description = description

    def __repr__(self) -> str:
        return f"OAuthError(status={self.status!r}, error={self.error!r}, description={self.description!r})"


def _error_class(status: int) -> type[APIError]:
    if status == 400:
        return BadRequestError
    if status == 401:
        return AuthenticationError
    if status == 402:
        return QuotaExceededError
    if status == 403:
        return PermissionDeniedError
    if status == 404:
        return NotFoundError
    if status == 429:
        return RateLimitError
    if 500 <= status < 600:
        return ServerError
    return APIError


def api_error_from_response(status: int, body: Any) -> APIError:
    """Build the right APIError subclass for an error response.

    The v2 API normally answers with ``{"error": {"code": ..., "message": ...}}``, but some
    failures (a bad access token, for one) come back with an empty or non-JSON body.
    """
    message = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            message = error["message"]
    if not message:
        if status in _DEFAULT_MESSAGES:
            message = _DEFAULT_MESSAGES[status]
        elif 500 <= status < 600:
            message = "Server error"
        else:
            message = f"Request failed with status {status}"
    return _error_class(status)(status, message, body)
