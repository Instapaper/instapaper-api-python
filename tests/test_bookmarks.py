from __future__ import annotations

from typing import Any

import pytest

from instapaper import (
    Bookmark,
    BookmarkCategory,
    Instapaper,
    Progress,
    Tag,
)

from .conftest import BASE, FakeTransport, bookmark_data, split_url, tag_data


def page(count: int, total: int, start: int = 1, **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"bookmarks": [bookmark_data(id=start + i) for i in range(count)], "total": total}
    data.update(extra)
    return data


# ----- list / iterate -----------------------------------------------------


def test_list_defaults(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(2, total=214))

    result = client.bookmarks.list()

    url, query = split_url(transport.last.url)
    assert transport.last.method == "GET"
    assert url == f"{BASE}/bookmarks"
    # section is left to the server so folder_id or tag alone can imply it.
    assert query == {"limit": ["25"], "offset": ["0"]}
    assert result.total == 214
    assert [bookmark.id for bookmark in result.bookmarks] == [1, 2]


def test_list_parses_bookmark(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"bookmarks": [bookmark_data()], "total": 1})

    bookmark = client.bookmarks.list().bookmarks[0]

    assert bookmark == Bookmark(
        id=12345,
        url="https://example.com/article",
        title="An Article",
        description="The opening lines.",
        image="https://example.com/image.jpg",
        progress=Progress(percentage=0.42, timestamp=1755000000),
        liked=False,
        archived=False,
        time=1755000000,
        pubtime=1705276800,
        author="Jane Doe",
        folder_id=99,
        tags=[Tag(id=9, name="Recipes", slug="recipes", count=12, baton=None)],
        private_source=None,
        category=BookmarkCategory.ARTICLE,
    )


def test_list_with_section_folder_and_tag(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(0, total=0))
    client.bookmarks.list(section="archive", limit=50, offset=100)
    assert split_url(transport.last.url)[1] == {"section": ["archive"], "limit": ["50"], "offset": ["100"]}

    transport.queue(page(0, total=0))
    client.bookmarks.list(folder_id=99)
    assert split_url(transport.last.url)[1] == {"folder_id": ["99"], "limit": ["25"], "offset": ["0"]}

    transport.queue(page(0, total=0))
    client.bookmarks.list(tag="Big Recipes")
    assert "tag=Big+Recipes" in transport.last.url


@pytest.mark.parametrize(
    "kwargs",
    [
        {"folder_id": 1, "tag": "x"},
        {"section": "everything"},
        {"limit": 0},
        {"limit": 501},
    ],
)
def test_list_validates_arguments(client: Instapaper, transport: FakeTransport, kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        client.bookmarks.list(**kwargs)
    assert transport.requests == []


def test_iterate_walks_pages_until_short_page(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(2, total=5, start=1))
    transport.queue(page(2, total=5, start=3))
    transport.queue(page(1, total=5, start=5))

    ids = [bookmark.id for bookmark in client.bookmarks.iterate(section="liked", page_size=2)]

    assert ids == [1, 2, 3, 4, 5]
    offsets = [split_url(request.url)[1]["offset"] for request in transport.requests]
    assert offsets == [["0"], ["2"], ["4"]]
    assert all(split_url(request.url)[1]["section"] == ["liked"] for request in transport.requests)


def test_iterate_stops_when_total_reached(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(2, total=4, start=1))
    transport.queue(page(2, total=4, start=3))

    ids = [bookmark.id for bookmark in client.bookmarks.iterate(page_size=2)]

    assert ids == [1, 2, 3, 4]
    assert len(transport.requests) == 2


def test_iterate_empty_section(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(0, total=0))
    assert list(client.bookmarks.iterate(folder_id=7)) == []
    assert len(transport.requests) == 1


def test_iterate_validates_page_size(client: Instapaper) -> None:
    with pytest.raises(ValueError):
        next(client.bookmarks.iterate(page_size=1000))


# ----- changes / sync -----------------------------------------------------


def test_changes(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(1, total=3, deleted_ids=[12346, 12347]))

    changes = client.bookmarks.changes(1755000000.9, limit=100, offset=10)

    url, query = split_url(transport.last.url)
    assert url == f"{BASE}/bookmarks"
    assert query == {"since": ["1755000000"], "limit": ["100"], "offset": ["10"]}
    assert [bookmark.id for bookmark in changes.bookmarks] == [1]
    assert changes.deleted_ids == [12346, 12347]
    assert changes.total == 3


def test_changes_missing_deleted_ids(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(1, total=1))
    assert client.bookmarks.changes(100).deleted_ids == []


def test_changes_accepts_datetime(client: Instapaper, transport: FakeTransport) -> None:
    from datetime import datetime, timezone

    transport.queue(page(0, total=0, deleted_ids=[]))
    client.bookmarks.changes(datetime(2025, 8, 12, 12, 0, tzinfo=timezone.utc))
    _, query = split_url(transport.last.url)
    assert query["since"] == ["1755000000"]


@pytest.mark.parametrize(
    ("kwargs"),
    [
        {"section": "home", "folder_id": 99},
        {"section": "archive", "tag": "recipes"},
        {"section": "tag", "folder_id": 99},
    ],
)
def test_list_rejects_section_that_conflicts_with_folder_or_tag(
    client: Instapaper, transport: FakeTransport, kwargs: dict[str, Any]
) -> None:
    # The API ignores folder_id/tag when section is sent, so these would return the wrong list.
    with pytest.raises(ValueError):
        client.bookmarks.list(**kwargs)
    assert transport.requests == []


@pytest.mark.parametrize("since", [0, -5])
def test_changes_rejects_non_positive_since(client: Instapaper, since: int) -> None:
    # The API treats since=0 as "not syncing" and would return the home list instead.
    with pytest.raises(ValueError):
        client.bookmarks.changes(since)


def test_sync_aggregates_pages(client: Instapaper, transport: FakeTransport) -> None:
    # Deleted IDs fill page slots too, so a full page is bookmarks + deleted_ids.
    transport.queue(page(2, total=3, start=1, deleted_ids=[90]))
    transport.queue(page(1, total=3, start=3, deleted_ids=[91, 92]))
    transport.queue(page(0, total=3, deleted_ids=[93]))

    changes = client.bookmarks.sync(since=1755000000, page_size=3)

    assert [bookmark.id for bookmark in changes.bookmarks] == [1, 2, 3]
    assert changes.deleted_ids == [90, 91, 92, 93]
    assert changes.total == 3
    offsets = [split_url(request.url)[1]["offset"] for request in transport.requests]
    assert offsets == [["0"], ["3"], ["6"]]


def test_sync_single_page(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(page(0, total=0, deleted_ids=[]))
    changes = client.bookmarks.sync(since=5)
    assert changes.bookmarks == [] and changes.deleted_ids == [] and changes.total == 0
    assert split_url(transport.last.url)[1]["limit"] == ["500"]


# ----- save ---------------------------------------------------------------


def test_save_minimal(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(bookmark_data())

    bookmark = client.bookmarks.save("https://example.com/article")

    request = transport.last
    assert request.method == "POST"
    assert request.url == f"{BASE}/bookmarks"
    assert request.headers["Content-Type"] == "application/json"
    assert request.json() == {"url": "https://example.com/article"}
    assert bookmark.id == 12345


def test_save_all_fields(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(bookmark_data())

    client.bookmarks.save(
        "https://example.com/article",
        title="An Article",
        description="Summary",
        folder_id=99,
        archived=True,
        canonicalize=False,
        tags=["Recipes", "Dinner"],
    )

    assert transport.last.json() == {
        "url": "https://example.com/article",
        "title": "An Article",
        "description": "Summary",
        "folder_id": 99,
        "archived": True,
        "canonicalize": False,
        "tags": [{"name": "Recipes"}, {"name": "Dinner"}],
    }


def test_save_private_content(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(bookmark_data(url=None, private_source="Acme Reader"))

    bookmark = client.bookmarks.save(private_source="Acme Reader", content="<p>Hi</p>", title="Private")

    assert transport.last.json() == {"private_source": "Acme Reader", "content": "<p>Hi</p>", "title": "Private"}
    assert bookmark.url is None
    assert bookmark.private_source == "Acme Reader"


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        ((), {}),
        (("https://example.com",), {"private_source": "Acme", "content": "<p></p>"}),
        ((), {"private_source": "Acme"}),
    ],
)
def test_save_validates(
    client: Instapaper, transport: FakeTransport, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        client.bookmarks.save(*args, **kwargs)
    assert transport.requests == []


# ----- update / delete ----------------------------------------------------


def test_update_title_and_description(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(bookmark_data(title="New"))

    bookmark = client.bookmarks.update(12345, title="New", description="Desc")

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/bookmarks/12345"
    assert transport.last.json() == {"title": "New", "description": "Desc"}
    assert bookmark.title == "New"


def test_update_progress_with_timestamp(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(bookmark_data())
    client.bookmarks.update(12345, progress=0.5, progress_timestamp=1755000123)
    assert transport.last.json() == {"progress": {"percentage": 0.5, "timestamp": 1755000123}}


def test_update_progress_defaults_timestamp_to_now(
    client: Instapaper, transport: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("instapaper.resources.time.time", lambda: 1760000000.7)
    transport.queue(bookmark_data())
    client.bookmarks.update(12345, progress=1)
    assert transport.last.json() == {"progress": {"percentage": 1.0, "timestamp": 1760000000}}


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"progress": 1.5}, {"progress": -0.1}, {"progress_timestamp": 5}],
)
def test_update_validates(client: Instapaper, transport: FakeTransport, kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        client.bookmarks.update(1, **kwargs)
    assert transport.requests == []


def test_delete_accepts_empty_body(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(status=200)

    client.bookmarks.delete(12345)

    assert transport.last.method == "DELETE"
    assert transport.last.url == f"{BASE}/bookmarks/12345"
    assert transport.last.body is None


# ----- move / like --------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "args", "section"),
    [
        ("archive", (12345,), "archive"),
        ("unarchive", (12345,), "home"),
        ("move_to_folder", (12345, 99), "99"),
    ],
)
def test_moves(client: Instapaper, transport: FakeTransport, method: str, args: tuple[int, ...], section: str) -> None:
    transport.queue(bookmark_data(archived=section == "archive"))

    bookmark = getattr(client.bookmarks, method)(*args)

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/bookmarks/12345/move"
    assert transport.last.json() == {"section": section}
    assert isinstance(bookmark, Bookmark)


def test_like_and_unlike(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(bookmark_data(liked=True))
    assert client.bookmarks.like(12345).liked is True
    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/bookmarks/12345/like"
    # No payload, but an explicit empty body so proxies see a Content-Length.
    assert transport.last.body == b""
    assert "Content-Type" not in transport.last.headers

    transport.queue(bookmark_data(liked=False))
    assert client.bookmarks.unlike(12345).liked is False
    assert transport.last.method == "DELETE"
    assert transport.last.url == f"{BASE}/bookmarks/12345/like"


# ----- tags ---------------------------------------------------------------


def test_update_tags(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"created_tags": [tag_data(id=10, name="New")], "tags": [tag_data(), tag_data(id=10, name="New")]})

    changes = client.bookmarks.update_tags(12345, add=["New", 9], remove=[7, 8])

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/bookmarks/12345/tags"
    assert transport.last.json() == {
        "add_tags": [{"name": "New"}, {"id": 9}],
        "remove_tags": [{"id": 7}, {"id": 8}],
    }
    assert [tag.name for tag in changes.created_tags] == ["New"]
    assert [tag.id for tag in changes.tags] == [9, 10]


def test_update_tags_remove_only(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"created_tags": [], "tags": []})
    client.bookmarks.update_tags(1, remove=[7])
    assert transport.last.json() == {"remove_tags": [{"id": 7}]}


def test_update_tags_validates(client: Instapaper, transport: FakeTransport) -> None:
    with pytest.raises(ValueError):
        client.bookmarks.update_tags(1)
    with pytest.raises(TypeError):
        client.bookmarks.update_tags(1, add=[True])
    with pytest.raises(TypeError):
        client.bookmarks.update_tags(1, remove=["name"])  # type: ignore[list-item]
    assert transport.requests == []


# ----- parse --------------------------------------------------------------

PARSED = {
    "metadata": {
        "title": "An Article",
        "author": {"name": "Jane Doe", "url": "https://example.com/jane"},
        "pubtime": 1705276800,
        "thumbnail": "https://example.com/image.jpg",
        "description": "The opening lines.",
        "private_source": None,
        "category": 3,
    },
    "content": {
        "body": "<p>The article.</p>",
        "images": ["https://example.com/image.jpg"],
        "words": 1234,
        "paywalled": False,
        "direction": "ltr",
    },
}


def test_parse_get(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(PARSED)

    article = client.bookmarks.parse(12345)

    url, query = split_url(transport.last.url)
    assert transport.last.method == "GET"
    assert url == f"{BASE}/bookmarks/12345/parse"
    assert query == {}
    assert article.metadata.title == "An Article"
    assert article.metadata.author is not None and article.metadata.author.url == "https://example.com/jane"
    assert article.metadata.category is BookmarkCategory.PDF
    assert article.content.body == "<p>The article.</p>"
    assert article.content.images == ["https://example.com/image.jpg"]
    assert article.content.words == 1234
    assert article.content.direction == "ltr"


def test_parse_get_options(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(PARSED)
    client.bookmarks.parse(12345, use_cache=False, force=True, instaparser_api_key="ip-key")
    assert split_url(transport.last.url)[1] == {"use_cache": ["0"], "force": ["1"], "instaparser_api_key": ["ip-key"]}


def test_parse_post_with_content(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(PARSED)

    client.bookmarks.parse(12345, content="<html></html>", use_cache=False, instaparser_api_key="ip-key")

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/bookmarks/12345/parse"
    assert transport.last.json() == {
        "use_cache": False,
        "force": False,
        "content": "<html></html>",
        "instaparser_api_key": "ip-key",
    }


def test_parse_tolerates_sparse_response(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"metadata": {"category": 99}, "content": {}})

    article = client.bookmarks.parse(1)

    assert article.metadata.author is None
    assert article.metadata.category is BookmarkCategory.ARTICLE
    assert article.content.images == []
    assert article.content.paywalled is False
