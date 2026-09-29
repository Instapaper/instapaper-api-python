# Instapaper API Python Library

The official Python client for the [Instapaper API v2](https://www.instapaper.com/developers/overview/getting-started). Save articles, keep a user's library in sync, organize bookmarks into folders and tags, work with highlights, and read parsed article text.

It has no dependencies outside the Python standard library.

## Installation

```bash
pip install instapaper-api
```

Requires Python 3.10 or later.

## Quick start

If you're calling the API for your own Instapaper account, such as from a script or a personal tool, you don't need the OAuth flow. [Register an application](https://www.instapaper.com/developers/applications/create), then generate an access token on its page. See [Accessing your own account](https://www.instapaper.com/developers/overview/authentication#accessing-your-own-account).

```python
from instapaper import Instapaper

client = Instapaper("your-access-token")

me = client.me()
print(f"Signed in as {me.username}")

bookmark = client.bookmarks.save("https://example.com/article", title="An Article")
client.bookmarks.like(bookmark.id)

for bookmark in client.bookmarks.list():
    print(bookmark.title, bookmark.url)
```

## Authenticating other users with OAuth

To act on behalf of other Instapaper users, send them through the OAuth 2 authorization code flow. Add your redirect URI to your application's callback URIs first; it has to match exactly.

```python
import secrets

from instapaper import Instapaper, OAuth

oauth = OAuth(
    client_id="your-client-id",
    client_secret="your-client-secret",
    redirect_uri="https://yourapp.example.com/callback",
)

state = secrets.token_urlsafe(16)
url = oauth.authorization_url(state=state)
# Redirect the user to `url`. Instapaper sends them back to your redirect URI
# with ?code=...&state=... once they approve.

# In your callback, check that `state` matches, then:
token = oauth.exchange_code(code)
client = Instapaper(token.access_token)
```

Access tokens don't expire, so store the token rather than the code. Keep your client secret on your server.

## Bookmarks

```python
# One page of a section: home (default), archive, liked, folder, or tag
page = client.bookmarks.list(section="archive", limit=50)
print(f"{len(page)} of {page.total}")
for bookmark in page:
    print(bookmark.title)

# Every bookmark in a folder, fetched page by page
for bookmark in client.bookmarks.iterate(folder_id=99):
    ...

# Save with tags, straight into a folder
client.bookmarks.save("https://example.com/recipe", tags=["Recipes"], folder_id=99)

# Save content that has no public URL
client.bookmarks.save(private_source="Acme Reader", content="<p>...</p>", title="A Private Article")

client.bookmarks.update(12345, progress=0.42)
client.bookmarks.archive(12345)
client.bookmarks.move_to_folder(12345, 99)
client.bookmarks.update_tags(12345, add=["Recipes"], remove=[7])
client.bookmarks.delete(12345)  # permanent, not the same as archiving
```

### Syncing

`sync` returns everything that changed since a Unix timestamp, across every section, including the IDs of bookmarks deleted since then.

```python
import time

started = int(time.time())
changes = client.bookmarks.sync(since=last_sync)
for bookmark in changes.bookmarks:
    ...  # insert or update your local copy
for bookmark_id in changes.deleted_ids:
    ...  # remove it locally
last_sync = started
```

Use `changes` instead if you want to fetch one page at a time.

### Article text

```python
article = client.bookmarks.parse(12345)
print(article.metadata.title)
print(article.content.body)  # HTML with scripts stripped
```

Parsing without a key is allowed for personal use, when the account you're reading belongs to the developer who registered the application. To read other users' articles, pass your own [Instaparser](https://www.instaparser.com) key as `instaparser_api_key`. See [Non-personal use](https://www.instapaper.com/developers/v2/reference/bookmarks#non-personal-use), and read the [API Terms of Use](https://www.instapaper.com/developers/overview/api-terms) for what you may do with article text.

## Folders, tags, and highlights

```python
folder = client.folders.create("Recipes")
client.folders.reorder({folder.id: 1})
client.folders.delete(folder.id)  # its bookmarks move back to the home list

tag = client.tags.create("Cooking")
client.tags.rename(tag.id, "Food")

highlight = client.highlights.create(12345, "The passage the reader marked.")
client.highlights.list(12345)
client.highlights.delete(highlight.id)
```

Accounts without Instapaper Premium can create five highlights a month. Past that, `create` raises `PermissionDeniedError`.

## Errors

Every error this library raises is an `InstapaperError`. When the API answers with an error status you get an `APIError` subclass carrying `status` and `message`:

| Exception               | Status | When                                                               |
| ----------------------- | ------ | ------------------------------------------------------------------ |
| `BadRequestError`       | 400    | A missing or invalid argument                                      |
| `AuthenticationError`   | 401    | The access token is missing, unknown, or revoked                   |
| `QuotaExceededError`    | 402    | Instaparser credits ran out                                        |
| `PermissionDeniedError` | 403    | The application isn't approved or is suspended, or a Premium limit |
| `NotFoundError`         | 404    | No such endpoint                                                   |
| `RateLimitError`        | 429    | Too many requests                                                  |
| `ServerError`           | 5xx    | Something went wrong on Instapaper's side                          |

`InstapaperConnectionError` means the request never got a response, and `OAuthError` comes from `OAuth.exchange_code`.

```python
from instapaper import AuthenticationError, RateLimitError

try:
    client.bookmarks.save("https://example.com/article")
except AuthenticationError:
    ...  # ask the user to reconnect
except RateLimitError:
    ...  # back off and try again later
```

Branch on the exception type or `status`, not on `message`, which may be reworded over time.

## Documentation

The full API reference lives at [instapaper.com/developers](https://www.instapaper.com/developers/overview/getting-started).

## License

MIT. See [LICENSE](LICENSE).
