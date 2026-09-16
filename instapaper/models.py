"""Objects returned by the Instapaper API.

Every model is a frozen dataclass built with ``from_dict``, which ignores keys it doesn't
know about so new server fields don't break older versions of this library.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, overload


class BookmarkCategory(IntEnum):
    """What kind of thing a bookmark is. Unknown values are treated as ARTICLE."""

    ARTICLE = 0
    EMAIL = 1
    VIDEO = 2
    PDF = 3
    SOCIAL = 4

    @classmethod
    def parse(cls, value: Any) -> BookmarkCategory:
        try:
            return cls(int(value))
        except (TypeError, ValueError):
            return cls.ARTICLE


def _opt_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _opt_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _dicts(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


@dataclass(frozen=True)
class User:
    """An Instapaper account."""

    id: int
    username: str
    #: Whether the account has Instapaper Premium. None when the response didn't say,
    #: as in the OAuth token response.
    premium: bool | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> User:
        premium = data.get("premium")
        return cls(
            id=int(data["id"]),
            username=str(data.get("username") or ""),
            premium=None if premium is None else bool(premium),
        )


@dataclass(frozen=True)
class Tag:
    id: int
    name: str
    slug: str = ""
    count: int = 0
    baton: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Tag:
        return cls(
            id=int(data["id"]),
            name=str(data.get("name") or ""),
            slug=str(data.get("slug") or ""),
            count=int(data.get("count") or 0),
            baton=_opt_str(data.get("baton")),
        )


@dataclass(frozen=True)
class Progress:
    """Reading progress: how far through the article, and when that was recorded."""

    percentage: float = 0.0
    timestamp: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Progress:
        if not data:
            return cls()
        return cls(
            percentage=float(data.get("percentage") or 0.0),
            timestamp=int(data.get("timestamp") or 0),
        )


@dataclass(frozen=True)
class Bookmark:
    id: int
    url: str | None = None
    title: str | None = None
    description: str | None = None
    image: str | None = None
    progress: Progress = field(default_factory=Progress)
    liked: bool = False
    archived: bool = False
    #: When it was saved, as a Unix timestamp.
    time: int = 0
    #: When the article was published, as a Unix timestamp, when known.
    pubtime: int | None = None
    author: str | None = None
    #: The folder it's in, or None for the home list.
    folder_id: int | None = None
    tags: list[Tag] = field(default_factory=list)
    private_source: str | None = None
    category: BookmarkCategory = BookmarkCategory.ARTICLE

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Bookmark:
        return cls(
            id=int(data["id"]),
            url=_opt_str(data.get("url")),
            title=_opt_str(data.get("title")),
            description=_opt_str(data.get("description")),
            image=_opt_str(data.get("image")),
            progress=Progress.from_dict(data.get("progress")),
            liked=bool(data.get("liked")),
            archived=bool(data.get("archived")),
            time=int(data.get("time") or 0),
            pubtime=_opt_int(data.get("pubtime")),
            author=_opt_str(data.get("author")),
            folder_id=_opt_int(data.get("folder_id")),
            tags=[Tag.from_dict(tag) for tag in _dicts(data.get("tags"))],
            private_source=_opt_str(data.get("private_source")),
            category=BookmarkCategory.parse(data.get("category")),
        )


@dataclass(frozen=True)
class Folder:
    id: int
    title: str
    slug: str = ""
    position: int = 0
    #: Whether the folder is published on the user's public profile.
    public: bool = False
    count: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Folder:
        return cls(
            id=int(data["id"]),
            title=str(data.get("title") or ""),
            slug=str(data.get("slug") or ""),
            position=int(data.get("position") or 0),
            public=bool(data.get("public")),
            count=int(data.get("count") or 0),
        )


@dataclass(frozen=True)
class Highlight:
    id: int
    bookmark_id: int
    text: str
    note: str | None = None
    #: Which occurrence of ``text`` in the article body this highlight marks, counting from 0.
    position: int = 0
    time: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Highlight:
        return cls(
            id=int(data["id"]),
            bookmark_id=int(data["bookmark_id"]),
            text=str(data.get("text") or ""),
            note=_opt_str(data.get("note")),
            position=int(data.get("position") or 0),
            time=int(data.get("time") or 0),
        )


@dataclass(frozen=True)
class ArticleAuthor:
    name: str
    url: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ArticleAuthor:
        return cls(name=str(data.get("name") or ""), url=_opt_str(data.get("url")))


@dataclass(frozen=True)
class ArticleMetadata:
    title: str | None = None
    author: ArticleAuthor | None = None
    pubtime: int | None = None
    thumbnail: str | None = None
    description: str | None = None
    private_source: str | None = None
    category: BookmarkCategory = BookmarkCategory.ARTICLE

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> ArticleMetadata:
        data = data or {}
        author = data.get("author")
        return cls(
            title=_opt_str(data.get("title")),
            author=ArticleAuthor.from_dict(author) if isinstance(author, Mapping) else None,
            pubtime=_opt_int(data.get("pubtime")),
            thumbnail=_opt_str(data.get("thumbnail")),
            description=_opt_str(data.get("description")),
            private_source=_opt_str(data.get("private_source")),
            category=BookmarkCategory.parse(data.get("category")),
        )


@dataclass(frozen=True)
class ArticleContent:
    #: The article as UTF-8 HTML, with scripts stripped.
    body: str | None = None
    images: list[str] = field(default_factory=list)
    words: int | None = None
    paywalled: bool = False
    #: ``ltr`` or ``rtl``.
    direction: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> ArticleContent:
        data = data or {}
        images = data.get("images")
        return cls(
            body=_opt_str(data.get("body")),
            images=[str(image) for image in images] if isinstance(images, list) else [],
            words=_opt_int(data.get("words")),
            paywalled=bool(data.get("paywalled")),
            direction=_opt_str(data.get("direction")),
        )


@dataclass(frozen=True)
class ParsedArticle:
    """The parsed, reader-ready version of a saved article."""

    metadata: ArticleMetadata
    content: ArticleContent

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ParsedArticle:
        return cls(
            metadata=ArticleMetadata.from_dict(data.get("metadata")),
            content=ArticleContent.from_dict(data.get("content")),
        )


@dataclass(frozen=True)
class BookmarkList(Sequence[Bookmark]):
    """One page of bookmarks. ``total`` is the size of the whole section, not this page.

    The page behaves like a list of its bookmarks, so you can loop over it, index it, and
    take its ``len`` directly. ``bookmarks`` holds the same items as a plain list.
    """

    bookmarks: list[Bookmark]
    total: int

    def __iter__(self) -> Iterator[Bookmark]:
        return iter(self.bookmarks)

    def __len__(self) -> int:
        return len(self.bookmarks)

    @overload
    def __getitem__(self, index: int) -> Bookmark: ...

    @overload
    def __getitem__(self, index: slice) -> list[Bookmark]: ...

    def __getitem__(self, index: int | slice) -> Bookmark | list[Bookmark]:
        return self.bookmarks[index]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BookmarkList:
        return cls(
            bookmarks=[Bookmark.from_dict(item) for item in _dicts(data.get("bookmarks"))],
            total=int(data.get("total") or 0),
        )


@dataclass(frozen=True)
class BookmarkChanges:
    """Bookmarks changed since a timestamp, plus the IDs of any deleted since then."""

    bookmarks: list[Bookmark]
    deleted_ids: list[int]
    total: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BookmarkChanges:
        deleted = data.get("deleted_ids")
        return cls(
            bookmarks=[Bookmark.from_dict(item) for item in _dicts(data.get("bookmarks"))],
            deleted_ids=[int(item) for item in deleted] if isinstance(deleted, list) else [],
            total=int(data.get("total") or 0),
        )


@dataclass(frozen=True)
class TagChanges:
    """A bookmark's tags after an update, and the tags that update created."""

    tags: list[Tag]
    created_tags: list[Tag]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TagChanges:
        return cls(
            tags=[Tag.from_dict(item) for item in _dicts(data.get("tags"))],
            created_tags=[Tag.from_dict(item) for item in _dicts(data.get("created_tags"))],
        )


@dataclass(frozen=True)
class AccessToken:
    """The result of exchanging an OAuth 2 authorization code."""

    access_token: str
    token_type: str = "Bearer"
    user: User | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AccessToken:
        user = data.get("user")
        return cls(
            access_token=str(data["access_token"]),
            token_type=str(data.get("token_type") or "Bearer"),
            user=User.from_dict(user) if isinstance(user, Mapping) and "id" in user else None,
        )

    def __repr__(self) -> str:
        # Keep the token itself out of logs and tracebacks.
        return f"AccessToken(token_type={self.token_type!r}, user={self.user!r})"
