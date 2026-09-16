from __future__ import annotations

import pytest

from instapaper import BadRequestError, Folder, Highlight, Instapaper, PermissionDeniedError, Tag

from .conftest import BASE, FakeTransport, folder_data, highlight_data, tag_data

# ----- folders ------------------------------------------------------------


def test_list_folders(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"folders": [folder_data(), folder_data(id=100, title="Travel", public=True, position=2)]})

    folders = client.folders.list()

    assert transport.last.method == "GET"
    assert transport.last.url == f"{BASE}/folders"
    assert folders == [
        Folder(id=99, title="Recipes", slug="recipes", position=1, public=False, count=12),
        Folder(id=100, title="Travel", slug="recipes", position=2, public=True, count=12),
    ]


def test_create_folder(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(folder_data())

    folder = client.folders.create("Recipes")

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/folders"
    assert transport.last.json() == {"title": "Recipes"}
    assert folder.id == 99


def test_delete_folder(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(status=200)

    client.folders.delete(99)

    assert transport.last.method == "DELETE"
    assert transport.last.url == f"{BASE}/folders/99"


def test_reorder_folders(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"folders": [folder_data(id=100, position=1), folder_data(id=99, position=2)]})

    folders = client.folders.reorder({100: 1, 99: 2})

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/folders/reorder"
    assert transport.last.json() == {"order": [{"folder_id": 100, "position": 1}, {"folder_id": 99, "position": 2}]}
    assert [folder.id for folder in folders] == [100, 99]


def test_reorder_requires_positions(client: Instapaper, transport: FakeTransport) -> None:
    with pytest.raises(ValueError):
        client.folders.reorder({})
    assert transport.requests == []


def test_reorder_rejects_positions_below_one(client: Instapaper, transport: FakeTransport) -> None:
    # The API silently skips a position of 0, so it's rejected up front.
    with pytest.raises(ValueError):
        client.folders.reorder({99: 0})
    assert transport.requests == []


# ----- tags ---------------------------------------------------------------


def test_list_tags(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"tags": [tag_data()]})

    tags = client.tags.list()

    assert transport.last.method == "GET"
    assert transport.last.url == f"{BASE}/tags"
    assert tags == [Tag(id=9, name="Recipes", slug="recipes", count=12, baton=None)]


def test_create_tag(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(tag_data(count=0))

    tag = client.tags.create("Recipes")

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/tags"
    assert transport.last.json() == {"name": "Recipes"}
    assert tag.count == 0


def test_rename_tag(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(tag_data(name="Cooking", slug="cooking"))

    tag = client.tags.rename(9, "Cooking")

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/tags/9"
    assert transport.last.json() == {"name": "Cooking"}
    assert tag.slug == "cooking"


# ----- highlights ---------------------------------------------------------


def test_list_highlights(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue({"highlights": [highlight_data(), highlight_data(id=502, note=None)]})

    highlights = client.highlights.list(12345)

    assert transport.last.method == "GET"
    assert transport.last.url == f"{BASE}/bookmarks/12345/highlights"
    assert highlights[0] == Highlight(
        id=501,
        bookmark_id=12345,
        text="The passage the reader marked.",
        note="Worth revisiting.",
        position=0,
        time=1755000000,
    )
    assert highlights[1].note is None


def test_create_highlight(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(highlight_data())

    highlight = client.highlights.create(12345, "The passage.", note="Worth revisiting.", position=1)

    assert transport.last.method == "POST"
    assert transport.last.url == f"{BASE}/bookmarks/12345/highlights"
    assert transport.last.json() == {"text": "The passage.", "note": "Worth revisiting.", "position": 1}
    assert highlight.id == 501


def test_create_highlight_defaults(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(highlight_data())
    client.highlights.create(12345, "The passage.")
    assert transport.last.json() == {"text": "The passage.", "position": 0}


def test_create_highlight_rejects_blank_text(client: Instapaper, transport: FakeTransport) -> None:
    with pytest.raises(ValueError):
        client.highlights.create(12345, "   ")
    assert transport.requests == []


def test_highlight_limit_is_permission_denied(client: Instapaper, transport: FakeTransport) -> None:
    message = "Non-subscribers are limited to 5 highlights per month"
    transport.queue({"error": {"code": 403, "message": message}}, status=403)

    with pytest.raises(PermissionDeniedError) as info:
        client.highlights.create(12345, "The passage.")

    assert info.value.message == message


def test_delete_highlight(client: Instapaper, transport: FakeTransport) -> None:
    transport.queue(status=200)

    client.highlights.delete(501)

    assert transport.last.method == "DELETE"
    assert transport.last.url == f"{BASE}/highlights/501"


def test_delete_missing_highlight_raises(client: Instapaper, transport: FakeTransport) -> None:
    # A highlight that doesn't exist, belongs to someone else, or was already deleted is a 400.
    message = "Invalid or missing highlight_id"
    transport.queue({"error": {"code": 400, "message": message}}, status=400)

    with pytest.raises(BadRequestError) as info:
        client.highlights.delete(99999)

    assert info.value.message == message
