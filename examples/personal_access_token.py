"""Read and save bookmarks for your own account with a personal access token.

Generate a token on your application's page at https://www.instapaper.com/developers/applications,
then run:

    INSTAPAPER_ACCESS_TOKEN=... python examples/personal_access_token.py
"""

import os
import sys

from instapaper import AuthenticationError, Instapaper


def main() -> None:
    token = os.environ.get("INSTAPAPER_ACCESS_TOKEN")
    if not token:
        sys.exit("Set INSTAPAPER_ACCESS_TOKEN to an access token from your application's page.")

    client = Instapaper(token)
    try:
        me = client.me()
    except AuthenticationError:
        sys.exit("That access token isn't valid. Generate a new one on your application's page.")

    print(f"Signed in as {me.username}")

    page = client.bookmarks.list(limit=10)
    print(f"{page.total} bookmarks in your home list. The newest {len(page)}:")
    for bookmark in page:
        print(f"  {bookmark.id}  {bookmark.title or bookmark.url}")

    folders = client.folders.list()
    if folders:
        print("Folders: " + ", ".join(f"{folder.title} ({folder.count})" for folder in folders))


if __name__ == "__main__":
    main()
