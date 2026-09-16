"""Shared request plumbing for the API client."""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping
from typing import Any

from . import __version__
from ._transport import HTTPRequest, Transport, decode_body
from .errors import APIError, api_error_from_response

DEFAULT_BASE_URL = "https://www.instapaper.com"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = f"instapaper-api-python/{__version__}"

_BODY_METHODS = {"POST", "PUT", "PATCH"}


def query_string(params: Mapping[str, Any] | None) -> str:
    """Encode query parameters, dropping any that are None."""
    if not params:
        return ""
    pairs = [(key, str(value)) for key, value in params.items() if value is not None]
    return urllib.parse.urlencode(pairs)


class APIRequester:
    """Sends authenticated requests to ``/api/2`` and turns responses into data or errors."""

    def __init__(self, access_token: str, base_url: str, timeout: float, transport: Transport) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/api/2{path}"
        query = query_string(params)
        if query:
            url = f"{url}?{query}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        body: bytes | None = None
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif method in _BODY_METHODS:
            # Send an explicit empty body so proxies see a Content-Length.
            body = b""

        response = self.transport(HTTPRequest(method=method, url=url, headers=headers, body=body, timeout=self.timeout))
        data = decode_body(response.body)
        if not 200 <= response.status < 300:
            raise api_error_from_response(response.status, data)
        if isinstance(data, str):
            raise APIError(response.status, "The API returned a response that wasn't JSON", data)
        return data

    def request_object(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Like ``request``, but the response must be a JSON object."""
        data = self.request(method, path, params=params, json_body=json_body)
        if not isinstance(data, Mapping):
            raise APIError(200, "The API returned an unexpected response", data)
        return data


def path_id(value: int | str) -> str:
    """Format an ID for use in a URL path."""
    return urllib.parse.quote(str(value), safe="")
