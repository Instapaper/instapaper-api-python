"""API resources: bookmarks, folders, tags, and highlights."""

from __future__ import annotations

import builtins
import time
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from typing import Any

from ._http import APIRequester, path_id
from .models import (
    Bookmark,
    BookmarkChanges,
    BookmarkList,
    Folder,
    Highlight,
    ParsedArticle,
    Tag,
    TagChanges,
)

SECTIONS = ("home", "archive", "liked", "folder", "tag")
MAX_PAGE_SIZE = 500


def _check_page_size(value: int, name: str) -> None:
    if not 1 <= value <= MAX_PAGE_SIZE:
        raise ValueError(f"{name} must be between 1 and {MAX_PAGE_SIZE}")


def _check_since(since: int | float | datetime) -> int:
    since = int(since.timestamp()) if isinstance(since, datetime) else int(since)
    # The API treats since=0 as "no since", which silently returns the home list instead.
    if since < 1:
        raise ValueError("since must be a positive Unix timestamp")
    return since


class _Resource:
    def __init__(self, requester: APIRequester) -> None:
        self._requester = requester


class Bookmarks(_Resource):
    """List, save, update, move, like, tag, delete, and read bookmarks."""

    def list(
        self,
        *,
        section: str | None = None,
        folder_id: int | None = None,
        tag: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> BookmarkList:
        """Fetch one page of bookmarks.

        ``section`` is ``home`` (the default), ``archive``, ``liked``, ``folder``, or ``tag``.
        Passing ``folder_id`` or ``tag`` on its own implies that section.
        """
        if folder_id is not None and tag is not None:
            raise ValueError("folder_id and tag can't be used together")
        if section is not None and section not in SECTIONS:
            raise ValueError(f"section must be one of: {', '.join(SECTIONS)}")
        # The API ignores folder_id and tag whenever section is sent, so a mismatch would
        # silently return a different list.
        if section is not None and folder_id is not None and section != "folder":
            raise ValueError("folder_id can only be used with section='folder'")
        if section is not None and tag is not None and section != "tag":
            raise ValueError("tag can only be used with section='tag'")
        _check_page_size(limit, "limit")
        data = self._requester.request_object(
            "GET",
            "/bookmarks",
            params={
                "section": section,
                "folder_id": folder_id,
                "tag": tag,
                "limit": limit,
                "offset": offset,
            },
        )
        return BookmarkList.from_dict(data)

    def iterate(
        self,
        *,
        section: str | None = None,
        folder_id: int | None = None,
        tag: str | None = None,
        page_size: int = 100,
    ) -> Iterator[Bookmark]:
        """Yield every bookmark in a section, fetching pages as needed."""
        _check_page_size(page_size, "page_size")
        offset = 0
        while True:
            page = self.list(section=section, folder_id=folder_id, tag=tag, limit=page_size, offset=offset)
            yield from page.bookmarks
            offset += len(page.bookmarks)
            if len(page.bookmarks) < page_size or offset >= page.total:
                return

    def changes(self, since: int | float | datetime, *, limit: int = MAX_PAGE_SIZE, offset: int = 0) -> BookmarkChanges:
        """Fetch one page of everything changed since a Unix timestamp, across every section.

        ``total`` is the number of changed bookmarks.
        """
        _check_page_size(limit, "limit")
        data = self._requester.request_object(
            "GET",
            "/bookmarks",
            params={"since": _check_since(since), "limit": limit, "offset": offset},
        )
        return BookmarkChanges.from_dict(data)

    def sync(self, since: int | float | datetime, *, page_size: int = MAX_PAGE_SIZE) -> BookmarkChanges:
        """Fetch everything changed since a Unix timestamp, across all pages.

        Record the time before you call this and pass it as ``since`` next time.
        """
        _check_page_size(page_size, "page_size")
        bookmarks: builtins.list[Bookmark] = []
        deleted_ids: builtins.list[int] = []
        offset = 0
        total = 0
        while True:
            page = self.changes(since, limit=page_size, offset=offset)
            bookmarks.extend(page.bookmarks)
            deleted_ids.extend(page.deleted_ids)
            total = page.total
            # Deleted bookmarks take up slots in a page just like changed ones do.
            count = len(page.bookmarks) + len(page.deleted_ids)
            offset += count
            if count < page_size:
                return BookmarkChanges(bookmarks=bookmarks, deleted_ids=deleted_ids, total=total)

    def save(
        self,
        url: str | None = None,
        *,
        title: str | None = None,
        description: str | None = None,
        folder_id: int | None = None,
        archived: bool | None = None,
        canonicalize: bool | None = None,
        tags: Iterable[str] | None = None,
        content: str | None = None,
        private_source: str | None = None,
    ) -> Bookmark:
        """Save a URL, or private content with no URL (``private_source`` plus ``content``).

        Saving a URL the account already has updates the existing bookmark instead of
        creating a duplicate. Sending ``title`` avoids a slower server-side lookup.
        """
        if url and private_source:
            raise ValueError("Pass either url or private_source, not both")
        if not url and not private_source:
            raise ValueError("url is required unless you're saving private content with private_source")
        if private_source and not content:
            raise ValueError("private_source requires content")

        body: dict[str, Any] = {}
        optional = {
            "url": url,
            "title": title,
            "description": description,
            "folder_id": folder_id,
            "archived": archived,
            "canonicalize": canonicalize,
            "content": content,
            "private_source": private_source,
        }
        for key, value in optional.items():
            if value is not None:
                body[key] = value
        if tags is not None:
            body["tags"] = [{"name": name} for name in tags]
        return Bookmark.from_dict(self._requester.request_object("POST", "/bookmarks", json_body=body))

    def update(
        self,
        bookmark_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        progress: float | None = None,
        progress_timestamp: int | None = None,
    ) -> Bookmark:
        """Update a bookmark's title, description, or reading progress.

        ``progress`` runs from 0.0 to 1.0. ``progress_timestamp`` is when that position was
        recorded and defaults to now. A progress update older than the one on file is ignored.
        """
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if progress is not None:
            if not 0.0 <= progress <= 1.0:
                raise ValueError("progress must be between 0.0 and 1.0")
            timestamp = int(time.time()) if progress_timestamp is None else int(progress_timestamp)
            body["progress"] = {"percentage": float(progress), "timestamp": timestamp}
        elif progress_timestamp is not None:
            raise ValueError("progress_timestamp requires progress")
        if not body:
            raise ValueError("Nothing to update: pass title, description, or progress")
        data = self._requester.request_object("POST", f"/bookmarks/{path_id(bookmark_id)}", json_body=body)
        return Bookmark.from_dict(data)

    def delete(self, bookmark_id: int) -> None:
        """Permanently delete a bookmark. This is not the same as archiving."""
        self._requester.request("DELETE", f"/bookmarks/{path_id(bookmark_id)}")

    def _move(self, bookmark_id: int, section: str) -> Bookmark:
        data = self._requester.request_object(
            "POST", f"/bookmarks/{path_id(bookmark_id)}/move", json_body={"section": section}
        )
        return Bookmark.from_dict(data)

    def archive(self, bookmark_id: int) -> Bookmark:
        return self._move(bookmark_id, "archive")

    def unarchive(self, bookmark_id: int) -> Bookmark:
        """Move a bookmark back to the home list."""
        return self._move(bookmark_id, "home")

    def move_to_folder(self, bookmark_id: int, folder_id: int) -> Bookmark:
        return self._move(bookmark_id, str(folder_id))

    def like(self, bookmark_id: int) -> Bookmark:
        return Bookmark.from_dict(self._requester.request_object("POST", f"/bookmarks/{path_id(bookmark_id)}/like"))

    def unlike(self, bookmark_id: int) -> Bookmark:
        return Bookmark.from_dict(self._requester.request_object("DELETE", f"/bookmarks/{path_id(bookmark_id)}/like"))

    def update_tags(
        self,
        bookmark_id: int,
        *,
        add: Iterable[str | int] = (),
        remove: Iterable[int] = (),
    ) -> TagChanges:
        """Add and remove tags on a bookmark.

        ``add`` takes tag names (created if they don't exist yet) or tag IDs. ``remove`` takes tag IDs.
        """
        add_tags: builtins.list[dict[str, Any]] = []
        for item in add:
            if isinstance(item, bool) or not isinstance(item, str | int):
                raise TypeError("add takes tag names (str) or tag IDs (int)")
            add_tags.append({"name": item} if isinstance(item, str) else {"id": item})
        remove_tags: builtins.list[dict[str, Any]] = []
        for tag_id in remove:
            if isinstance(tag_id, bool) or not isinstance(tag_id, int):
                raise TypeError("remove takes tag IDs (int)")
            remove_tags.append({"id": tag_id})
        if not add_tags and not remove_tags:
            raise ValueError("Pass at least one tag to add or remove")

        body: dict[str, Any] = {}
        if add_tags:
            body["add_tags"] = add_tags
        if remove_tags:
            body["remove_tags"] = remove_tags
        data = self._requester.request_object("POST", f"/bookmarks/{path_id(bookmark_id)}/tags", json_body=body)
        return TagChanges.from_dict(data)

    def parse(
        self,
        bookmark_id: int,
        *,
        use_cache: bool = True,
        force: bool = False,
        content: str | None = None,
        instaparser_api_key: str | None = None,
    ) -> ParsedArticle:
        """Fetch the parsed, reader-ready text of a saved article.

        Pass ``content`` to have HTML you already have parsed instead of fetching the URL.
        Applications reading accounts other than their owner's need an ``instaparser_api_key``.
        """
        path = f"/bookmarks/{path_id(bookmark_id)}/parse"
        if content is not None:
            body: dict[str, Any] = {"use_cache": use_cache, "force": force, "content": content}
            if instaparser_api_key is not None:
                body["instaparser_api_key"] = instaparser_api_key
            data = self._requester.request_object("POST", path, json_body=body)
        else:
            params = {
                "use_cache": None if use_cache else "0",
                "force": "1" if force else None,
                "instaparser_api_key": instaparser_api_key,
            }
            data = self._requester.request_object("GET", path, params=params)
        return ParsedArticle.from_dict(data)


class Folders(_Resource):
    """The user-created folders in the sidebar. Home, archive, and liked are not folders."""

    def list(self) -> builtins.list[Folder]:
        """All folders, in the user's own order."""
        data = self._requester.request_object("GET", "/folders")
        return [Folder.from_dict(item) for item in data.get("folders") or []]

    def create(self, title: str) -> Folder:
        return Folder.from_dict(self._requester.request_object("POST", "/folders", json_body={"title": title}))

    def delete(self, folder_id: int) -> None:
        """Delete a folder. Its bookmarks move back to the home list."""
        self._requester.request("DELETE", f"/folders/{path_id(folder_id)}")

    def reorder(self, positions: Mapping[int, int]) -> builtins.list[Folder]:
        """Set folder positions from a ``{folder_id: position}`` mapping.

        Folders you leave out keep their positions. Returns the full list in its new order.
        """
        if not positions:
            raise ValueError("Pass at least one folder position")
        order = [{"folder_id": int(folder_id), "position": int(position)} for folder_id, position in positions.items()]
        # The API silently skips entries without a truthy position.
        if any(entry["position"] < 1 for entry in order):
            raise ValueError("Folder positions must be 1 or greater")
        data = self._requester.request_object("POST", "/folders/reorder", json_body={"order": order})
        return [Folder.from_dict(item) for item in data.get("folders") or []]


class Tags(_Resource):
    """The user's tags. To tag a bookmark, use ``client.bookmarks.update_tags``."""

    def list(self) -> builtins.list[Tag]:
        data = self._requester.request_object("GET", "/tags")
        return [Tag.from_dict(item) for item in data.get("tags") or []]

    def create(self, name: str) -> Tag:
        return Tag.from_dict(self._requester.request_object("POST", "/tags", json_body={"name": name}))

    def rename(self, tag_id: int, name: str) -> Tag:
        return Tag.from_dict(
            self._requester.request_object("POST", f"/tags/{path_id(tag_id)}", json_body={"name": name})
        )


class Highlights(_Resource):
    """Passages a user has marked inside an article."""

    def list(self, bookmark_id: int) -> builtins.list[Highlight]:
        data = self._requester.request_object("GET", f"/bookmarks/{path_id(bookmark_id)}/highlights")
        return [Highlight.from_dict(item) for item in data.get("highlights") or []]

    def create(self, bookmark_id: int, text: str, *, note: str | None = None, position: int = 0) -> Highlight:
        """Create a highlight. Accounts without Premium are limited to five a month.

        ``position`` is which occurrence of ``text`` in the article body to highlight, counting from 0.
        The default, 0, is the first occurrence.
        """
        if not text or not text.strip():
            raise ValueError("text can't be empty")
        body: dict[str, Any] = {"text": text, "position": position}
        if note is not None:
            body["note"] = note
        data = self._requester.request_object("POST", f"/bookmarks/{path_id(bookmark_id)}/highlights", json_body=body)
        return Highlight.from_dict(data)

    def delete(self, highlight_id: int) -> None:
        """Delete a highlight.

        Raises ``BadRequestError`` if the highlight doesn't exist, belongs to someone else, or was already deleted.
        """
        self._requester.request("DELETE", f"/highlights/{path_id(highlight_id)}")
