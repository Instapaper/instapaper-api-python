"""The HTTP layer. Everything the client sends goes through a Transport."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .errors import InstapaperConnectionError


@dataclass(frozen=True)
class HTTPRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    timeout: float = 30.0

    def json(self) -> Any:
        """The request body decoded as JSON, or None if there's no body."""
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)


Transport = Callable[[HTTPRequest], HTTPResponse]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand redirects back to the caller instead of silently following them.

    Following a redirect would resend the Authorization header to wherever it points.
    """

    def redirect_request(self, *args: Any, **kwargs: Any) -> urllib.request.Request | None:
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def urllib_transport(request: HTTPRequest) -> HTTPResponse:
    """Send a request with the standard library. Non-2xx statuses are returned, not raised."""
    urllib_request = urllib.request.Request(
        request.url,
        data=request.body,
        headers=request.headers,
        method=request.method,
    )
    try:
        with _opener.open(urllib_request, timeout=request.timeout) as response:
            return HTTPResponse(
                status=response.status,
                body=response.read(),
                headers=dict(response.headers.items()),
            )
    except urllib.error.HTTPError as error:
        try:
            body = error.read()
        except OSError:
            body = b""
        headers = dict(error.headers.items()) if error.headers else {}
        return HTTPResponse(status=error.code, body=body, headers=headers)
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as error:
        reason = getattr(error, "reason", None) or error
        raise InstapaperConnectionError(f"Could not reach Instapaper: {reason}") from error


def decode_body(body: bytes) -> Any:
    """Parse a response body: JSON when possible, raw text otherwise, None when empty."""
    if not body or not body.strip():
        return None
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text
