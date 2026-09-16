"""Helpers for the OAuth 2 authorization code flow."""

from __future__ import annotations

import urllib.parse

from ._http import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, USER_AGENT
from ._transport import HTTPRequest, Transport, decode_body, urllib_transport
from .errors import OAuthError
from .models import AccessToken


class OAuth:
    """Send users through Instapaper's consent page and exchange the code for an access token.

    Example:
        >>> oauth = OAuth("client-id", "client-secret", "https://yourapp.example.com/callback")
        >>> url = oauth.authorization_url(state="random-state")
        >>> # ...redirect the user to url; Instapaper sends them back with ?code=...&state=...
        >>> token = oauth.exchange_code(code)

    ``redirect_uri`` must exactly match one of the callback URIs registered on your application.
    Keep ``client_secret`` on your server.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Transport | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or urllib_transport

    def authorization_url(self, state: str | None = None) -> str:
        """The URL to send the user to. Pass ``state`` and check it on the way back to defend against CSRF."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        if state is not None:
            params["state"] = state
        return f"{self.base_url}/oauth2/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> AccessToken:
        """Redeem an authorization code for an access token.

        Codes expire an hour after they're issued and can only be redeemed once.
        """
        body = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            }
        ).encode("utf-8")
        response = self._transport(
            HTTPRequest(
                method="POST",
                url=f"{self.base_url}/oauth2/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                body=body,
                timeout=self.timeout,
            )
        )
        data = decode_body(response.body)
        if not 200 <= response.status < 300:
            error = description = None
            if isinstance(data, dict):
                error = data.get("error") if isinstance(data.get("error"), str) else None
                description = data.get("error_description") if isinstance(data.get("error_description"), str) else None
            raise OAuthError(response.status, error, description)
        if not isinstance(data, dict) or not data.get("access_token"):
            raise OAuthError(response.status, None, "The token response didn't include an access token")
        return AccessToken.from_dict(data)

    def __repr__(self) -> str:
        return f"OAuth(client_id={self.client_id!r}, redirect_uri={self.redirect_uri!r})"
