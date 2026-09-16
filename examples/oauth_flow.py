"""Walk through the OAuth 2 authorization code flow from the command line.

In a real web application the user is redirected to the authorization URL and back to your
callback. Here you open the URL yourself and paste the callback URL you land on.

    INSTAPAPER_CLIENT_ID=... INSTAPAPER_CLIENT_SECRET=... \\
    INSTAPAPER_REDIRECT_URI=https://yourapp.example.com/callback \\
    python examples/oauth_flow.py
"""

import os
import secrets
import sys
from urllib.parse import parse_qs, urlparse

from instapaper import Instapaper, OAuth, OAuthError


def main() -> None:
    try:
        oauth = OAuth(
            client_id=os.environ["INSTAPAPER_CLIENT_ID"],
            client_secret=os.environ["INSTAPAPER_CLIENT_SECRET"],
            redirect_uri=os.environ["INSTAPAPER_REDIRECT_URI"],
        )
    except KeyError as missing:
        sys.exit(f"Set {missing.args[0]}.")

    state = secrets.token_urlsafe(16)
    print("Open this URL, approve access, then paste the URL you were sent back to:")
    print(oauth.authorization_url(state=state))

    callback = urlparse(input("> ").strip())
    params = parse_qs(callback.query)
    if params.get("state", [None])[0] != state:
        sys.exit("The state doesn't match. Start over.")
    if "error" in params:
        sys.exit(f"Authorization failed: {params.get('error_description', params['error'])[0]}")

    try:
        token = oauth.exchange_code(params["code"][0])
    except OAuthError as error:
        sys.exit(f"Couldn't exchange the code: {error}")

    client = Instapaper(token.access_token)
    print(f"Connected as {client.me().username}. Store the access token; it doesn't expire.")


if __name__ == "__main__":
    main()
