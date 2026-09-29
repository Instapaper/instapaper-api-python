"""Official Python client for the Instapaper API v2."""

__version__ = "1.0.0"

from ._transport import HTTPRequest, HTTPResponse, Transport  # noqa: E402
from .client import Instapaper  # noqa: E402
from .errors import (  # noqa: E402
    APIError,
    AuthenticationError,
    BadRequestError,
    InstapaperConnectionError,
    InstapaperError,
    NotFoundError,
    OAuthError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
)
from .models import (  # noqa: E402
    AccessToken,
    ArticleAuthor,
    ArticleContent,
    ArticleMetadata,
    Bookmark,
    BookmarkCategory,
    BookmarkChanges,
    BookmarkList,
    Folder,
    Highlight,
    ParsedArticle,
    Progress,
    Tag,
    TagChanges,
    User,
)
from .oauth import OAuth  # noqa: E402

__all__ = [
    "__version__",
    "Instapaper",
    "OAuth",
    "HTTPRequest",
    "HTTPResponse",
    "Transport",
    "InstapaperError",
    "InstapaperConnectionError",
    "APIError",
    "BadRequestError",
    "AuthenticationError",
    "QuotaExceededError",
    "PermissionDeniedError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "OAuthError",
    "AccessToken",
    "ArticleAuthor",
    "ArticleContent",
    "ArticleMetadata",
    "Bookmark",
    "BookmarkCategory",
    "BookmarkChanges",
    "BookmarkList",
    "Folder",
    "Highlight",
    "ParsedArticle",
    "Progress",
    "Tag",
    "TagChanges",
    "User",
]
