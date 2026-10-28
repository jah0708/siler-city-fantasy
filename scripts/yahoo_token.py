"""Persist Yahoo's rotating OAuth refresh token without storing secrets in public Git.

The GitHub Actions secret YAHOO_CLIENT_SECRET encrypts an evolving token state.
Only ciphertext is committed to the repository. An updated GitHub Actions
YAHOO_REFRESH_TOKEN overrides the prior encrypted chain for reauthorization.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from secrets import token_bytes

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".github" / "yahoo-oauth.enc.json"
AAD = b"scfl-yahoo-oauth-state-v1"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.b64decode(data, validate=True)


def _derive_key(client_secret: str) -> bytes:
    if not client_secret:
        raise RuntimeError("Missing YAHOO_CLIENT_SECRET")
    return hashlib.sha256(b"scfl-oauth-v1\x00" + client_secret.encode("utf-8")).digest()


def _fingerprint(seed_token: str) -> str:
    return hashlib.sha256(seed_token.encode("utf-8")).hexdigest()


def _read_state(client_secret: str) -> dict | None:
    if not STATE_PATH.exists():
        return None
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if payload.get("version") != 1:
            raise ValueError("Unsupported version")
        raw = AESGCM(_derive_key(client_secret)).decrypt(
            _unb64(payload["nonce"]), _unb64(payload["ciphertext"]), AAD
        )
        state = json.loads(raw)
        if not isinstance(state.get("token"), str) or not isinstance(state.get("seed_fingerprint"), str):
            raise ValueError("Invalid token-state data")
        return state
    except (KeyError, ValueError, TypeError, InvalidTag) as exc:
        raise RuntimeError(
            "Stored Yahoo refresh-token state cannot be decrypted with YAHOO_CLIENT_SECRET. "
            "Review GitHub secrets before syncing."
        ) from exc


def select_refresh_token(client_secret: str, seed_token: str) -> str:
    if not seed_token:
        raise RuntimeError("Missing YAHOO_REFRESH_TOKEN GitHub secret")
    state = _read_state(client_secret)
    if state is None:
        return seed_token
    if state["seed_fingerprint"] != _fingerprint(seed_token):
        print("::notice::New seed Yahoo refresh token detected; replacing saved token chain.")
        return seed_token
    return state["token"]


def persist_refresh_token(
    client_secret: str, seed_token: str, latest_token: str, *, replace_existing: bool = False
) -> bool:
    """Save a token, replacing a prior app's state only after a fresh OAuth grant.

    Ordinary refreshes must still fail closed if the stored state cannot be
    decrypted. A successful authorization-code exchange can explicitly start a
    new chain, including when Yahoo requires a new app and client secret.
    """
    if not latest_token:
        raise ValueError("Cannot store an empty Yahoo refresh token")
    seed_fingerprint = _fingerprint(seed_token)
    state = None if replace_existing else _read_state(client_secret)
    if state and state == {"token": latest_token, "seed_fingerprint": seed_fingerprint}:
        return False
    raw = json.dumps(
        {"token": latest_token, "seed_fingerprint": seed_fingerprint},
        separators=(",", ":"),
    ).encode("utf-8")
    nonce = token_bytes(12)
    ciphertext = AESGCM(_derive_key(client_secret)).encrypt(nonce, raw, AAD)
    payload = {"version": 1, "nonce": _b64(nonce), "ciphertext": _b64(ciphertext)}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, STATE_PATH)
    return True

