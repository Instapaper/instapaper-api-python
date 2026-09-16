"""The Instapaper API v2 client."""

from __future__ import annotations

from ._http import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, APIRequester
from ._transport import Transport, urllib_transport
from .models import User
from .resources import Bookmarks, Folders, Highlights, Tags


class Instapaper:
    """Client for the Instapaper API v2.

    Example:
        >>> client = Instapaper("your-access-token")
        >>> for bookmark in client.bookmarks.iterate():
        ...     print(bookmark.title)

    Args:
        access_token: A bearer token, either generated on your application's page for your own
            account or obtained through the OAuth flow.
        base_url: Override the API host, e.g. for testing.
        timeout: Seconds to wait for each request.
        transport: Replace the HTTP layer. Mostly useful for tests.
    """

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Transport | None = None,
    ) -> None:
        if not access_token:
            raise ValueError("access_token is required")
        self._requester = APIRequester(access_token, base_url, timeout, transport or urllib_transport)
        self.bookmarks = Bookmarks(self._requester)
        self.folders = Folders(self._requester)
        self.tags = Tags(self._requester)
        self.highlights = Highlights(self._requester)

    def me(self) -> User:
        """The account the access token belongs to. A 401 means the token isn't valid."""
        return User.from_dict(self._requester.request_object("GET", "/me"))

    def __repr__(self) -> str:
        return f"Instapaper(base_url={self._requester.base_url!r})"
