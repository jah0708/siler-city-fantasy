"""Encrypted hardcoded weekly-score fallback for a public GitHub Pages repository.

All manual input is encrypted to an X25519 public key before being committed.
The corresponding private key is encrypted with SCFL_SITE_PASSWORD by GitHub
Actions. Only a GitHub Actions runner with that secret can apply a manual update.

The resulting complete league snapshot is encrypted as usual for the website.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from secrets import token_bytes

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from secure_site import ROOT, load_records, store_records

PUBLIC_KEY = ROOT / ".github" / "fallback-public-key.json"
PRIVATE_KEY = ROOT / ".github" / "fallback-key.enc.json"
MANUAL_FILE = ROOT / "data" / "manual-fallback.enc.json"
A_KEY = b"scfl-manual-private-v1"
A_DATA = b"scfl-manual-score-data-v1"
INFO = b"scfl-fallback-hkdf-v1"
ITERATIONS = 400_000


def enc(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def dec(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def password_key(password: str, salt: bytes) -> bytes:
    if len(password) < 20:
        raise RuntimeError("SCFL_SITE_PASSWORD must contain at least 20 characters")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


def generate_key_files(password: str) -> bool:
    """Create a stable public key and encrypted private key on GitHub's runner."""
    if PUBLIC_KEY.exists() or PRIVATE_KEY.exists():
        if not (PUBLIC_KEY.exists() and PRIVATE_KEY.exists()):
            raise RuntimeError("Only one manual fallback key file exists; refusing rotation")
        validate_private_key(password)
        return False
    private = x25519.X25519PrivateKey.generate()
    private_raw = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    salt, nonce = token_bytes(16), token_bytes(12)
    secret = AESGCM(password_key(password, salt)).encrypt(nonce, private_raw, A_KEY)
    PUBLIC_KEY.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_KEY.write_text(json.dumps({"version": 1, "algorithm": "X25519", "public_key": enc(public_raw)}) + "\n")
    PRIVATE_KEY.write_text(
        json.dumps({"version": 1, "iterations": ITERATIONS, "salt": enc(salt),
                    "nonce": enc(nonce), "ciphertext": enc(secret)}) + "\n"
    )
    print("Prepared encrypted static-fallback key; public key can receive manual scores.")
    return True


def validate_private_key(password: str) -> x25519.X25519PrivateKey:
    try:
        private_data = json.loads(PRIVATE_KEY.read_text(encoding="utf-8"))
        public_data = json.loads(PUBLIC_KEY.read_text(encoding="utf-8"))
        if private_data["version"] != 1 or public_data["version"] != 1:
            raise ValueError("Invalid fallback key versions")
        key = password_key(password, dec(private_data["salt"]))
        raw = AESGCM(key).decrypt(dec(private_data["nonce"]), dec(private_data["ciphertext"]), A_KEY)
        private = x25519.X25519PrivateKey.from_private_bytes(raw)
        if private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw) != dec(public_data["public_key"]):
            raise ValueError("Fallback private/public keys disagree")
        return private
    except (OSError, KeyError, ValueError, TypeError, InvalidTag) as exc:
        raise RuntimeError("Could not unlock private manual-fallback key with the site password") from exc


def encrypt_manual_payload(manual: dict, public_data: dict) -> dict:
    public = x25519.X25519PublicKey.from_public_bytes(dec(public_data["public_key"]))
    ephemeral = x25519.X25519PrivateKey.generate()
    salt, nonce = token_bytes(16), token_bytes(12)
    shared = ephemeral.exchange(public)
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=INFO).derive(shared)
    clear = json.dumps(manual, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, clear, A_DATA)
    return {"version": 1, "ephemeral_public": enc(ephemeral.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
            "salt": enc(salt), "nonce": enc(nonce), "ciphertext": enc(ciphertext)}


def decrypt_manual_payload(private: x25519.X25519PrivateKey, blob: dict) -> dict:
    if blob.get("version") != 1:
        raise ValueError("Unsupported manual fallback payload")
    other = x25519.X25519PublicKey.from_public_bytes(dec(blob["ephemeral_public"]))
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=dec(blob["salt"]), info=INFO).derive(private.exchange(other))
    result = json.loads(AESGCM(key).decrypt(dec(blob["nonce"]), dec(blob["ciphertext"]), A_DATA))
    if not isinstance(result, dict):
        raise ValueError("Invalid manual snapshot")
    return result


def validate_matchups(matchups: dict, *, expected_names: set[str] | None = None) -> None:
    if not matchups:
        raise ValueError("No matchups")
    for week, games in matchups.items():
        if not str(week).isdigit() or not isinstance(games, list) or len(games) != 5:
            raise ValueError("Each week must have five games")
        names = []
        for game in games:
            if not isinstance(game, list) or len(game) != 4:
                raise ValueError("Matchup must include both teams and scores")
            a, points_a, b, points_b = game
            if not isinstance(a, str) or not isinstance(b, str):
                raise ValueError("Invalid team name")
            if (not isinstance(points_a, (float, int)) or isinstance(points_a, bool)
                    or not isinstance(points_b, (float, int)) or isinstance(points_b, bool)
                    or not 0 <= points_a <= 1000 or not 0 <= points_b <= 1000):
                raise ValueError("Invalid team score")
            if round(points_a, 2) != points_a or round(points_b, 2) != points_b:
                raise ValueError("Scores must use two decimal places")
            names.extend([a, b])
        if len(set(names)) != 10:
            raise ValueError(f"Duplicate or missing team in Week {week}")
        if expected_names is not None and set(names) != expected_names:
            raise ValueError(f"Week {week} team identities do not match league")


def compute_standings(all_matchups: dict, names: set[str]) -> list[dict]:
    """Deterministically calculate original SCFL VS and top-five point-win records."""
    validate_matchups(all_matchups, expected_names=names)
    rows = {name: {"name": name, "weeks": [], "wins": 0, "losses": 0,
                   "ties": 0, "pointWins": 0, "pointLosses": 0, "cents": 0} for name in names}
    weeks = sorted(int(key) for key in all_matchups)
    if weeks != list(range(1, weeks[-1] + 1)):
        raise ValueError("Missing a week in the cumulative standings")
    for week in weeks:
        matches = all_matchups[str(week)]
        scores = [(name, int(round(score * 100))) for a, a_score, b, b_score in matches
                  for name, score in ((a, a_score), (b, b_score))]
        top_five = {name for name, _ in sorted(scores, key=lambda t: (-t[1], t[0]))[:5]}
        for a, a_score, b, b_score in matches:
            left, right = int(round(a_score * 100)), int(round(b_score * 100))
            for name, score, other in ((a, left, right), (b, right, left)):
                row = rows[name]
                result = "W" if score > other else "L" if score < other else "T"
                point = "P" if name in top_five else "X"
                row["weeks"].append({"week": week, "result": result, "pointResult": point,
                                    "points": score / 100})
                row["wins"] += int(result == "W")
                row["losses"] += int(result == "L")
                row["ties"] += int(result == "T")
                row["pointWins"] += int(point == "P")
                row["pointLosses"] += int(point == "X")
                row["cents"] += score
    result = []
    for row in rows.values():
        points = row.pop("cents")
        row["points"] = points / 100
        row["average"] = round(points / 100 / len(weeks), 2)
        row["adjustedWins"] = row["wins"] + row["pointWins"]
        row["adjustedLosses"] = row["losses"] + row["pointLosses"]
        result.append(row)
    result.sort(key=lambda t: (-t["adjustedWins"], -t["points"], t["name"].lower()))
    for number, row in enumerate(result, 1):
        row["rank"] = number
    return result


def apply_manual_fallback(password: str) -> bool:
    """Use the static encrypted snapshot until Yahoo has at least this many weeks."""
    if not MANUAL_FILE.exists():
        return False
    private = validate_private_key(password)
    ciphertext = MANUAL_FILE.read_bytes()
    digest = hashlib.sha256(ciphertext).hexdigest()
    manual = decrypt_manual_payload(private, json.loads(ciphertext))
    weeks = manual.get("matchups")
    if manual.get("season") != 2026 or set(weeks or {}) != {"4", "5"}:
        raise ValueError("Only approved 2026 Week 4-5 manual fallback is allowed")
    names = set()
    db = load_records(password)
    names = {team["name"] for team in db["currentStandings"]}
    if len(names) != 10:
        raise RuntimeError("Unrecognized legacy team roster")
    validate_matchups(weeks, expected_names=names)
    yahoo = db.get("yahoo", {})
    yahoo_week = int(yahoo.get("week", 0))
    is_live = yahoo.get("source") != "manual" and yahoo_week >= 5
    if is_live:
        print("Live Yahoo data includes Week 5; retained live scores over manual backup.")
        return False
    if db.get("manualFallback", {}).get("fingerprint") == digest:
        print("Static manual Week 4-5 fallback already present.")
        return False
    combined = dict(db.get("matchups", {}))
    # Preserve any complete newer live weeks when they have already arrived.
    for week, games in weeks.items():
        if yahoo.get("source") != "manual" and int(week) <= yahoo_week:
            continue
        combined[week] = games
    if not all(str(i) in combined for i in range(1, 6)):
        raise RuntimeError("Cannot calculate Week 5 standings without Weeks 1-3")
    standings = compute_standings(combined, names)
    db["currentStandings"] = standings
    db["currentTeams"] = [row["name"] for row in standings]
    db["matchups"] = combined
    db["yahoo"] = {"week": 5, "source": "manual", "lastUpdated": "2026-10-16",
                   "label": "Saved Week 4–5 results (Yahoo connection pending)"}
    db["manualFallback"] = {"fingerprint": digest, "weeks": [4, 5]}
    store_records(db, password)
    print("Applied encrypted manual Week 4-5 backup and recalculated ten-team standings.")
    return True


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["bootstrap"]:
        generate_key_files(os.environ["SCFL_SITE_PASSWORD"])
    elif sys.argv[1:] == ["apply"]:
        apply_manual_fallback(os.environ["SCFL_SITE_PASSWORD"])
    else:
        raise SystemExit("Usage: python scripts/manual_fallback.py bootstrap|apply")
