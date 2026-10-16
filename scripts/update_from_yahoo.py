#!/usr/bin/env python3
"""Fetch Yahoo Fantasy results and publish only encrypted league records.

Yahoo's pending provisioning response causes a safe no-op. Incomplete scoreboards,
bad credentials and malformed data never replace the last good snapshot.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from secure_site import ENCRYPTED, INDEX, load_records, store_records

API_ROOT = "https://fantasysports.yahooapis.com/fantasy/v2"
REDIRECT_URI = "https://jah0708.github.io/siler-city-fantasy/"


class YahooError(RuntimeError):
    def __init__(self, code: int, description: str):
        self.code = code
        self.description = description
        super().__init__(f"Yahoo returned HTTP {code}: {description}")


def request_json(url: str, *, data: dict[str, str] | None = None, token: str | None = None) -> dict:
    body = urlencode(data).encode("utf-8") if data else None
    headers = {"Accept": "application/json", "User-Agent": "SCFL-private-league/1.0"}
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urlopen(request, timeout=45) as response:
            return json.load(response)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            item = json.loads(raw)
            inner = item.get("error", {})
            message = inner.get("description", "") if isinstance(inner, dict) else item.get("error_description", "")
        except (TypeError, AttributeError, ValueError):
            message = ""
        raise YahooError(exc.code, str(message or raw[:180])) from exc
    except URLError as exc:
        raise RuntimeError("Network error contacting Yahoo; last good data retained") from exc


def first_value(node, key: str):
    if isinstance(node, dict):
        if key in node and not isinstance(node[key], (list, tuple)):
            return node[key]
        for value in node.values():
            found = first_value(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = first_value(value, key)
            if found is not None:
                return found
    return None


def containers(node, key: str) -> list:
    output = []
    if isinstance(node, dict):
        if key in node:
            output.append(node[key])
        for value in node.values():
            output.extend(containers(value, key))
    elif isinstance(node, list):
        for value in node:
            output.extend(containers(value, key))
    return output


def numeric(value, default=None):
    try:
        result = float(value)
        if not -1_000_000 < result < 1_000_000:
            return default
        return result
    except (TypeError, ValueError):
        return default


def refresh_access_token() -> str:
    values = ("YAHOO_CLIENT_ID", "YAHOO_CLIENT_SECRET", "YAHOO_REFRESH_TOKEN")
    missing = [name for name in values if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing GitHub Actions secrets: " + ", ".join(missing))
    response = request_json("https://api.login.yahoo.com/oauth2/get_token", data={
        "client_id": os.environ["YAHOO_CLIENT_ID"],
        "client_secret": os.environ["YAHOO_CLIENT_SECRET"],
        "refresh_token": os.environ["YAHOO_REFRESH_TOKEN"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token",
    })
    if not response.get("access_token"):
        raise RuntimeError("Yahoo OAuth refresh returned no access token")
    return response["access_token"]


def api(path: str, token: str) -> dict:
    separator = "&" if "?" in path else "?"
    return request_json(f"{API_ROOT}/{path}{separator}format=json", token=token)


def find_league(token: str) -> tuple[str, int]:
    season = int(os.getenv("YAHOO_SEASON", str(datetime.now(timezone.utc).year)))
    league_id = os.getenv("YAHOO_LEAGUE_ID", "844486")
    override = os.getenv("YAHOO_GAME_KEY")
    if override:
        return f"{override}.l.{league_id}", season
    games = api(f"games;game_codes=nfl;seasons={season}", token)
    for entity in containers(games, "game"):
        key = first_value(entity, "game_key")
        actual_season = numeric(first_value(entity, "season"))
        if key and actual_season == season:
            return f"{key}.l.{league_id}", season
    raise RuntimeError(f"Yahoo did not return an NFL game key for {season}; data unchanged")


def league_metadata(token: str, league_key: str) -> tuple[int, int, str]:
    leagues = containers(api(f"league/{league_key}/metadata", token), "league")
    if not leagues:
        raise RuntimeError("Yahoo league metadata missing")
    entity = leagues[0]
    week = int(numeric(first_value(entity, "current_week"), 0))
    end = int(numeric(first_value(entity, "end_week"), 18))
    name = str(first_value(entity, "name") or "Siler City Fantasy League")
    if not 1 <= week <= 19 or not 1 <= end <= 19:
        raise RuntimeError("Invalid season weeks from Yahoo")
    return week, end, name


def week_matchups(token: str, league_key: str, week: int) -> list:
    data = api(f"league/{league_key}/scoreboard;week={week}", token)
    games, seen_pairs = [], set()
    for matchup in containers(data, "matchup"):
        pair, seen_teams = [], set()
        for entity in containers(matchup, "team"):
            team_key = str(first_value(entity, "team_key") or "")
            name = str(first_value(entity, "name") or "")
            team_points = first_value(entity, "team_points") or {}
            score = numeric(first_value(team_points, "total"))
            if score is None:
                score = numeric(first_value(entity, "total"))
            if not team_key or not name or team_key in seen_teams or score is None:
                continue
            pair.append((team_key, name, round(score, 2)))
            seen_teams.add(team_key)
        if len(pair) != 2:
            continue
        keys = frozenset((pair[0][0], pair[1][0]))
        if keys in seen_pairs or len(keys) != 2:
            continue
        games.append(pair)
        seen_pairs.add(keys)
    return games


def standings_and_scores(token: str, league_key: str, current: int, end: int):
    games_by_week, rows, latest = {}, {}, 0
    for week in range(1, min(current, end) + 1):
        games = week_matchups(token, league_key, week)
        if not games:
            if week == current:
                continue
            raise RuntimeError(f"Missing Yahoo scoreboard for Week {week}; existing data retained")
        if len(games) != 5 or len({t[0] for game in games for t in game}) != 10:
            raise RuntimeError(f"Incomplete Yahoo scoreboard for Week {week}; existing data retained")
        latest = week
        games_by_week[str(week)] = [
            [left[1], left[2], right[1], right[2]] for left, right in games
        ]
        sorted_scores = sorted(
            ((team[2], team[0]) for game in games for team in game),
            key=lambda pair: (-pair[0], pair[1]),
        )
        winners = {key for _, key in sorted_scores[:len(sorted_scores) // 2]}
        for left, right in games:
            for team, opponent in ((left, right), (right, left)):
                row = rows.setdefault(team[0], {"name": team[1], "weeks": []})
                result = "W" if team[2] > opponent[2] else ("L" if team[2] < opponent[2] else "T")
                row["weeks"].append({
                    "week": week,
                    "result": result,
                    "pointResult": "P" if team[0] in winners else "X",
                    "points": team[2],
                })
    if latest == 0 or len(rows) != 10:
        raise RuntimeError("No complete ten-team Yahoo data; existing records retained")
    standings = []
    for row in rows.values():
        weeks = row["weeks"]
        wins = sum(w["result"] == "W" for w in weeks)
        losses = sum(w["result"] == "L" for w in weeks)
        ties = sum(w["result"] == "T" for w in weeks)
        point_wins = sum(w["pointResult"] == "P" for w in weeks)
        points = round(sum(w["points"] for w in weeks), 2)
        standings.append({
            "rank": 0, "name": row["name"], "points": points,
            "average": round(points / len(weeks), 2),
            "wins": wins, "losses": losses, "ties": ties,
            "adjustedWins": wins + point_wins,
            "adjustedLosses": losses + len(weeks) - point_wins,
            "pointWins": point_wins,
            "pointLosses": len(weeks) - point_wins,
            "weeks": weeks,
        })
    standings.sort(key=lambda row: (-row["adjustedWins"], -row["points"], row["name"].lower()))
    for rank, row in enumerate(standings, 1):
        row["rank"] = rank
    return latest, standings, games_by_week


def main() -> int:
    password = os.getenv("SCFL_SITE_PASSWORD", "")
    if len(password) < 20:
        raise RuntimeError(
            "Set SCFL_SITE_PASSWORD (20+ characters) in GitHub Actions secrets; no data published"
        )
    try:
        token = refresh_access_token()
        key, season = find_league(token)
        current, end, name = league_metadata(token, key)
        week, standings, matchups = standings_and_scores(token, key, current, end)
    except YahooError as exc:
        if exc.code == 403 and "not authorized" in exc.description.lower():
            print("::notice::Yahoo access not provisioned yet; will retry at next schedule.")
            return 0
        raise
    database = load_records(password)
    same = (
        database.get("currentSeason") == str(season)
        and database.get("currentStandings") == standings
        and database.get("matchups") == matchups
        and database.get("yahoo", {}).get("leagueName") == name
    )
    if same and ENCRYPTED.exists() and 'id="unlockPanel"' in INDEX.read_text(encoding="utf-8"):
        print(f"Yahoo results unchanged through Week {week}; no new commit.")
        return 0
    database.update({
        "currentSeason": str(season),
        "currentTeams": [r["name"] for r in standings],
        "currentStandings": standings,
        "matchups": matchups,
        "yahoo": {
            "leagueName": name,
            "lastUpdated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "week": week,
        },
    })
    store_records(database, password)
    print(f"Updated encrypted results through Week {week} for {len(standings)} teams.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Update failed safely; no new plaintext Yahoo records committed: {exc}", file=sys.stderr)
        raise
