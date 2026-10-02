#!/usr/bin/env python3
"""Refresh the current SCFL season in index.html from Yahoo Fantasy Sports."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
API_ROOT = "https://fantasysports.yahooapis.com/fantasy/v2"
REDIRECT_URI = "https://jah0708.github.io/siler-city-fantasy/"


def request_json(url: str, *, data: dict[str, str] | None = None, token: str | None = None) -> dict:
    body = urlencode(data).encode() if data else None
    headers = {"Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urlopen(request, timeout=45) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Yahoo request failed ({exc.code}): {detail[:500]}") from exc


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


def containers(node, key: str):
    found = []
    if isinstance(node, dict):
        if key in node:
            found.append(node[key])
        for value in node.values():
            found.extend(containers(value, key))
    elif isinstance(node, list):
        for value in node:
            found.extend(containers(value, key))
    return found


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def refresh_access_token() -> str:
    result = request_json(
        "https://api.login.yahoo.com/oauth2/get_token",
        data={
            "client_id": os.environ["YAHOO_CLIENT_ID"],
            "client_secret": os.environ["YAHOO_CLIENT_SECRET"],
            "refresh_token": os.environ["YAHOO_REFRESH_TOKEN"],
            "redirect_uri": REDIRECT_URI,
            "grant_type": "refresh_token",
        },
    )
    if not result.get("access_token"):
        raise RuntimeError("Yahoo did not return an access token")
    return result["access_token"]


def api(path: str, token: str) -> dict:
    separator = "&" if "?" in path else "?"
    return request_json(f"{API_ROOT}/{path}{separator}format=json", token=token)


def find_league(token: str) -> tuple[str, str, int]:
    wanted_id = os.getenv("YAHOO_LEAGUE_ID", "844486")
    wanted_season = int(os.getenv("YAHOO_SEASON", str(datetime.now(timezone.utc).year)))
    # Resolve the season's NFL game key without using the user collection. This
    # is both faster and avoids Yahoo's more restrictive identity endpoint.
    data = api(f"games;game_codes=nfl;seasons={wanted_season}", token)
    game_keys = []
    for entity in containers(data, "game"):
        game_key = first_value(entity, "game_key")
        season = int(number(first_value(entity, "season"), 0))
        if game_key and season == wanted_season:
            game_keys.append(str(game_key))
    if not game_keys:
        raise RuntimeError(f"Yahoo did not return an NFL game key for {wanted_season}")
    return f"{game_keys[0]}.l.{wanted_id}", "Siler City Fantasy League", wanted_season


def league_meta(token: str, league_key: str) -> dict:
    data = api(f"league/{league_key}/metadata", token)
    entity = containers(data, "league")[0]
    return {
        "current_week": int(number(first_value(entity, "current_week"), 1)),
        "start_week": int(number(first_value(entity, "start_week"), 1)),
        "end_week": int(number(first_value(entity, "end_week"), 17)),
    }


def week_matchups(token: str, league_key: str, week: int):
    data = api(f"league/{league_key}/scoreboard;week={week}", token)
    games = []
    for matchup in containers(data, "matchup"):
        teams = []
        seen = set()
        for entity in containers(matchup, "team"):
            team_key = str(first_value(entity, "team_key") or "")
            name = str(first_value(entity, "name") or "")
            if not team_key or not name or team_key in seen:
                continue
            score = number(first_value(first_value(entity, "team_points") or {}, "total"), None)
            if score is None:
                score = number(first_value(entity, "total"), 0.0)
            teams.append((team_key, name, round(score, 2)))
            seen.add(team_key)
        if len(teams) >= 2:
            games.append(teams[:2])
    return games


def build_current_season(token: str, league_key: str, current_week: int):
    all_weeks = {}
    team_rows = {}
    latest_week = 0
    for week in range(1, current_week + 1):
        games = week_matchups(token, league_key, week)
        if not games:
            continue
        latest_week = week
        all_weeks[str(week)] = [[a[1], a[2], b[1], b[2]] for a, b in games]
        weekly_scores = sorted(
            [(team[2], team[0]) for game in games for team in game],
            key=lambda item: (-item[0], item[1]),
        )
        point_winners = {key for _, key in weekly_scores[: max(1, len(weekly_scores) // 2)]}
        for left, right in games:
            for team, opponent in ((left, right), (right, left)):
                row = team_rows.setdefault(team[0], {"name": team[1], "weeks": []})
                if team[2] > opponent[2]:
                    result = "W"
                elif team[2] < opponent[2]:
                    result = "L"
                else:
                    result = "T"
                row["weeks"].append(
                    {
                        "week": week,
                        "result": result,
                        "pointResult": "P" if team[0] in point_winners else "X",
                        "points": team[2],
                    }
                )

    standings = []
    for row in team_rows.values():
        weeks = row["weeks"]
        wins = sum(item["result"] == "W" for item in weeks)
        losses = sum(item["result"] == "L" for item in weeks)
        point_wins = sum(item["pointResult"] == "P" for item in weeks)
        point_losses = len(weeks) - point_wins
        points = round(sum(item["points"] for item in weeks), 2)
        standings.append(
            {
                "rank": 0,
                "name": row["name"],
                "points": points,
                "average": round(points / len(weeks), 2) if weeks else 0,
                "wins": wins,
                "losses": losses,
                "adjustedWins": wins + point_wins,
                "adjustedLosses": losses + point_losses,
                "pointWins": point_wins,
                "pointLosses": point_losses,
                "weeks": weeks,
            }
        )
    standings.sort(key=lambda row: (-row["adjustedWins"], -row["points"], row["name"].lower()))
    for rank, row in enumerate(standings, 1):
        row["rank"] = rank
    return latest_week, standings, all_weeks


def update_index(season: int, league_name: str, week: int, standings: list, matchups: dict):
    text = INDEX.read_text(encoding="utf-8")
    pattern = re.compile(r'(<script id="league-data" type="application/json">)(.*?)(</script>)', re.S)
    match = pattern.search(text)
    if not match:
        raise RuntimeError("The embedded league data block was not found")
    database = json.loads(match.group(2))
    database["currentSeason"] = str(season)
    database["currentTeams"] = [row["name"] for row in standings]
    database["currentStandings"] = standings
    database["matchups"] = matchups
    database["yahoo"] = {
        "leagueName": league_name,
        "lastUpdated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "week": week,
    }
    encoded = json.dumps(database, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    text = pattern.sub(lambda m: m.group(1) + encoded + m.group(3), text, count=1)
    text = re.sub(r"Week \d+ complete", f"Week {week} complete", text)
    text = re.sub(rf"{season} season · results through Week \d+", f"{season} season · results through Week {week}", text)
    text = re.sub(rf"{season} results through Week \d+", f"{season} results through Week {week}", text)
    INDEX.write_text(text, encoding="utf-8")


def main():
    token = refresh_access_token()
    league_key, league_name, season = find_league(token)
    meta = league_meta(token, league_key)
    week, standings, matchups = build_current_season(token, league_key, meta["current_week"])
    if not week or not standings:
        raise RuntimeError("Yahoo returned no scored matchups for the current season")
    update_index(season, league_name, week, standings, matchups)
    print(f"Updated {league_name} through Week {week}: {len(standings)} teams")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Update failed: {exc}", file=sys.stderr)
        raise
