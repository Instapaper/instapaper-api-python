from __future__ import annotations

import dataclasses

import pytest

from instapaper import (
    AccessToken,
    Bookmark,
    BookmarkCategory,
    BookmarkChanges,
    BookmarkList,
    Folder,
    Highlight,
    Progress,
    Tag,
    User,
)

from .conftest import bookmark_data


def test_models_ignore_unknown_keys() -> None:
    bookmark = Bookmark.from_dict(bookmark_data(hash="abc", something_new={"x": 1}))
    assert bookmark.id == 12345


def test_bookmark_tolerates_missing_optional_keys() -> None:
    bookmark = Bookmark.from_dict({"id": 1})
    assert bookmark == Bookmark(id=1)
    assert bookmark.progress == Progress(percentage=0.0, timestamp=0)
    assert bookmark.tags == []
    assert bookmark.category is BookmarkCategory.ARTICLE


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, BookmarkCategory.ARTICLE),
        (1, BookmarkCategory.EMAIL),
        (2, BookmarkCategory.VIDEO),
        (3, BookmarkCategory.PDF),
        (4, BookmarkCategory.SOCIAL),
        (42, BookmarkCategory.ARTICLE),
        (None, BookmarkCategory.ARTICLE),
        ("video", BookmarkCategory.ARTICLE),
    ],
)
def test_category_parsing(value: object, expected: BookmarkCategory) -> None:
    assert BookmarkCategory.parse(value) is expected


def test_models_are_frozen() -> None:
    tag = Tag(id=1, name="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        tag.name = "y"  # type: ignore[misc]


def test_user_premium_is_optional() -> None:
    assert User.from_dict({"id": 1, "username": "u"}).premium is None
    assert User.from_dict({"id": 1, "username": "u", "premium": True}).premium is True


def test_folder_and_highlight_defaults() -> None:
    assert Folder.from_dict({"id": 1, "title": "x"}) == Folder(id=1, title="x")
    assert Highlight.from_dict({"id": 1, "bookmark_id": 2, "text": "t"}) == Highlight(id=1, bookmark_id=2, text="t")


def test_lists_skip_malformed_items() -> None:
    result = BookmarkList.from_dict({"bookmarks": [bookmark_data(id=1), "junk", None], "total": 3})
    assert [bookmark.id for bookmark in result.bookmarks] == [1]

    assert BookmarkChanges.from_dict({"bookmarks": None}).deleted_ids == []


def test_access_token_without_user() -> None:
    token = AccessToken.from_dict({"access_token": "abc"})
    assert token.token_type == "Bearer"
    assert token.user is None


def test_bookmark_list_behaves_like_a_list_of_bookmarks() -> None:
    page = BookmarkList.from_dict({"bookmarks": [bookmark_data(id=1), bookmark_data(id=2)], "total": 214})

    assert [bookmark.id for bookmark in page] == [1, 2]
    assert len(page) == 2
    assert page[0].id == 1
    assert page[-1].id == 2
    assert [bookmark.id for bookmark in page[:1]] == [1]
    assert page.bookmarks[1] in page
    assert page.total == 214


def test_empty_bookmark_list_is_falsy() -> None:
    page = BookmarkList.from_dict({"bookmarks": [], "total": 0})

    assert not page
    assert list(page) == []
