#!/usr/bin/env python3
"""Exchange a one-time Yahoo OAuth authorization code for a refresh token.

Run only from the manually dispatched GitHub workflow after placing the Yahoo
authorization code in the YAHOO_AUTH_CODE Actions secret. No token or OAuth code
is logged or written as plaintext to git.
"""
from __future__ import annotations

import os
import sys

from urllib.parse import parse_qs, urlparse

from yahoo_token import persist_refresh_token
from update_from_yahoo import REDIRECT_URI, request_json


def main() -> None:
    names = ("YAHOO_CLIENT_ID", "YAHOO_CLIENT_SECRET", "YAHOO_REFRESH_TOKEN", "YAHOO_AUTH_CODE")
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError("Required GitHub secret(s) not configured: " + ", ".join(missing))

    # On a phone, copying the entire Yahoo callback URL is easier than editing it.
    # Accept either the bare short-lived authorization code or the exact callback URL.
    authorization_code = os.environ["YAHOO_AUTH_CODE"].strip()
    if authorization_code.startswith("https://"):
        callback = urlparse(authorization_code)
        registered = urlparse(REDIRECT_URI)
        if (callback.scheme, callback.netloc, callback.path) != (
            registered.scheme, registered.netloc, registered.path
        ):
            raise RuntimeError("Authorization URL is not the configured Yahoo callback")
        codes = parse_qs(callback.query).get("code", [])
        if len(codes) != 1 or not codes[0]:
            raise RuntimeError("Yahoo callback URL does not contain an authorization code")
        authorization_code = codes[0]
    result = request_json(
        "https://api.login.yahoo.com/oauth2/get_token",
        data={
            "client_id": os.environ["YAHOO_CLIENT_ID"],
            "client_secret": os.environ["YAHOO_CLIENT_SECRET"],
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "code": authorization_code,
        },
    )
    fresh = result.get("refresh_token")
    if not isinstance(fresh, str) or not fresh:
        raise RuntimeError("Yahoo authorization succeeded without returning a refresh token")
    persist_refresh_token(
        os.environ["YAHOO_CLIENT_SECRET"],
        os.environ["YAHOO_REFRESH_TOKEN"],
        fresh,
        replace_existing=True,
    )
    print("Yahoo reauthorization succeeded; replacement refresh token stored encrypted.")
    print("::notice::Remove the one-time YAHOO_AUTH_CODE Actions secret; it is no longer needed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "Yahoo reauthorization failed. Check that the Yahoo app's exact callback URL "
            "matches https://jah0708.github.io/siler-city-fantasy/ and that the "
            f"authorization code was copied immediately. Error: {type(exc).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

