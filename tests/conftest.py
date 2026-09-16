from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from instapaper import HTTPRequest, HTTPResponse, Instapaper

BASE = "https://www.instapaper.com/api/2"


class FakeTransport:
    """Records requests and replies with queued responses."""

    def __init__(self) -> None:
        self.requests: list[HTTPRequest] = []
        self.responses: list[HTTPResponse] = []

    def queue(self, body: Any = None, status: int = 200, raw: bytes | None = None) -> None:
        if raw is None:
            raw = b"" if body is None else json.dumps(body).encode("utf-8")
        self.responses.append(HTTPResponse(status=status, body=raw))

    def __call__(self, request: HTTPRequest) -> HTTPResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")
        return self.responses.pop(0)

    @property
    def last(self) -> HTTPRequest:
        return self.requests[-1]


def split_url(url: str) -> tuple[str, dict[str, list[str]]]:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}", parse_qs(parts.query)


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def client(transport: FakeTransport) -> Instapaper:
    return Instapaper("test-token", transport=transport)


def tag_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"id": 9, "name": "Recipes", "slug": "recipes", "count": 12, "baton": None}
    data.update(overrides)
    return data


def bookmark_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": 12345,
        "url": "https://example.com/article",
        "title": "An Article",
        "description": "The opening lines.",
        "image": "https://example.com/image.jpg",
        "progress": {"percentage": 0.42, "timestamp": 1755000000},
        "liked": False,
        "archived": False,
        "time": 1755000000,
        "pubtime": 1705276800,
        "author": "Jane Doe",
        "folder_id": 99,
        "tags": [tag_data()],
        "private_source": None,
        "category": 0,
    }
    data.update(overrides)
    return data


def folder_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": 99,
        "title": "Recipes",
        "slug": "recipes",
        "position": 1,
        "public": False,
        "count": 12,
    }
    data.update(overrides)
    return data


def highlight_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": 501,
        "bookmark_id": 12345,
        "text": "The passage the reader marked.",
        "note": "Worth revisiting.",
        "position": 0,
        "time": 1755000000,
    }
    data.update(overrides)
    return data
