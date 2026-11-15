"""Read-only league dashboard imports. Never collect private claims or pending trades."""
from __future__ import annotations
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from time import sleep


def value(node, key, default=None):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            found = value(v, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = value(v, key)
            if found is not None:
                return found
    return default


def entities(node, key):
    """Stop at the entity boundary: don't duplicate nested entities."""
    if isinstance(node, dict):
        if key in node:
            return [node[key]]
        return [v for child in node.values() for v in entities(child, key)]
    if isinstance(node, list):
        return [v for child in node for v in entities(child, key)]
    return []


def num(v):
    try:
        return round(float(v), 2) if v is not None and v != '' else None
    except (ValueError, TypeError):
        return None


def player(entity):
    name = value(entity, 'name', {})
    name = name.get('full', '') if isinstance(name, dict) else str(name)
    stat_data = value(entity, 'player_stats', {})
    stats = {str(value(s, 'stat_id')): value(s, 'value') for s in entities(stat_data, 'stat')}
    ownership = value(entity, 'ownership', {})
    return {
        'key': str(value(entity, 'player_key', '')), 'name': name,
        'position': value(entity, 'display_position', ''),
        'eligible': [x for x in entities(value(entity, 'eligible_positions', []), 'position') if isinstance(x, str)],
        'nflTeam': value(entity, 'editorial_team_abbr', ''),
        'status': value(entity, 'status', ''),
        'statusNote': value(entity, 'status_full', ''),
        'slot': value(value(entity, 'selected_position', {}), 'position', ''),
        'bye': value(value(entity, 'bye_weeks', {}), 'week'),
        'image': value(value(entity, 'headshot', {}), 'url', ''),
        'points': num(value(value(entity, 'player_points', {}), 'total')),
        'stats': stats, 'ownership': value(ownership, 'ownership_type', ''),
    }


def collect(token, league_key, current, end, previous, api):
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    previous = previous if isinstance(previous, dict) and previous.get('leagueKey', league_key) == league_key else {}
    hub = dict(previous)
    hub.update(version=1, leagueKey=league_key, week=current, checkedAt=now, errors={})
    sections = dict(previous.get('sections', {}))
    hub['sections'] = sections

    def section(name, fetch):
        try:
            result = fetch()
            hub[name] = result
            sections[name] = {'updatedAt': now, 'status': 'ok'}
        except Exception as exc:
            # Do not expose exception bodies or account details to public CI logs.
            hub['errors'][name] = 'Latest refresh unavailable; showing the last saved data.'
            sections[name] = {**sections.get(name, {}), 'status': 'stale' if name in hub else 'unavailable'}
            print(f'::warning::League hub {name} refresh unavailable ({type(exc).__name__}, HTTP {getattr(exc, 'code', 'n/a')}).')

    def get(path):
        for attempt in range(3):
            try:
                return api(path, token)
            except Exception as exc:
                if attempt == 2 or getattr(exc, 'code', 0) not in (429, 500, 502, 503, 504):
                    raise
                sleep(2 ** attempt)

    def teams():
        result = []
        for t in entities(get(f'league/{league_key}/teams'), 'team'):
            managers = entities(value(t, 'managers', {}), 'manager')
            result.append({'key': value(t, 'team_key'), 'name': value(t, 'name', ''),
                'logo': value(value(t, 'team_logos', {}), 'url', ''),
                'managers': [value(m, 'nickname', 'Manager') for m in managers],
                'moves': value(t, 'number_of_moves'), 'trades': value(t, 'number_of_trades')})
        if len(result) != 10 or len({t['key'] for t in result}) != 10:
            raise ValueError('Incomplete team list')
        return result
    section('teams', teams)
    section('statCategories', lambda: {str(value(s, 'stat_id')): value(s, 'display_name', value(s, 'name', 'Stat')) for s in entities(get(f'game/{league_key.split(".")[0]}/stat_categories'), 'stat')})
    keys = [t['key'] for t in hub.get('teams', [])]
    if not keys:
        return hub

    def rosters():
        history = dict(previous.get('rosters', {}))
        needed = [week for week in range(1, current + 1) if str(week) not in history or week >= current - 1]
        def one(task):
            week, key = task
            data = get(f'team/{key}/roster;week={week}/players/stats;type=week;week={week}')
            players = [player(p) for p in entities(data, 'player')]
            if not players or any(not p['key'] or not p['name'] for p in players):
                raise ValueError('Incomplete roster')
            return week, key, players
        with ThreadPoolExecutor(max_workers=4) as pool:
            fetched = list(pool.map(one, [(w, k) for w in needed for k in keys]))
        for week in needed:
            history[str(week)] = {key: ps for w, key, ps in fetched if w == week}
        return history
    section('rosters', rosters)

    def season_players():
        unique = sorted({p['key'] for roster in hub.get('rosters', {}).get(str(current), {}).values() for p in roster})
        result = {}
        for start in range(0, len(unique), 25):
            ids = ','.join(unique[start:start+25])
            data = get(f'league/{league_key}/players;player_keys={ids}/stats;type=season')
            result.update({p['key']: p for p in map(player, entities(data, 'player'))})
        if len(result) != len(unique) or not unique:
            raise ValueError('Incomplete player stats')
        return result
    section('playerStats', season_players)

    def available():
        result, seen = [], set()
        # A useful, bounded pool sorted by actual season points; never claim it is the entire universe.
        for start in range(0, 200, 25):
            data = get(f'league/{league_key}/players;status=A;sort=PTS;sort_type=season;start={start};count=25;out=ownership/stats;type=season')
            page = [player(p) for p in entities(data, 'player')]
            for p in page:
                if p['key'] and p['key'] not in seen:
                    seen.add(p['key']); result.append(p)
            if len(page) < 25:
                break
        if not result:
            raise ValueError('No available player data')
        return result
    section('available', available)

    def transactions():
        result, seen = [], set()
        for start in range(0, 100, 25):
            data = get(f'league/{league_key}/transactions;types=add,drop,trade;start={start};count=25')
            page = entities(data, 'transaction')
            for t in page:
                kind = value(t, 'type', '')
                if kind not in ('add', 'drop', 'add/drop', 'trade'):
                    continue
                key = value(t, 'transaction_key')
                if key in seen:
                    continue
                seen.add(key)
                moves = []
                for p in entities(t, 'player'):
                    details = value(p, 'transaction_data', {})
                    moves.append({'name': player(p)['name'], 'type': value(details, 'type', ''),
                        'from': value(details, 'source_team_name', ''), 'to': value(details, 'destination_team_name', '')})
                result.append({'key': key, 'type': kind, 'status': value(t, 'status', ''),
                    'timestamp': value(t, 'timestamp'), 'players': moves})
            if len(page) < 25:
                break
        return result
    section('transactions', transactions)

    def draft():
        picks = [{'pick': value(d, 'pick'), 'round': value(d, 'round'),
                  'teamKey': value(d, 'team_key'), 'playerKey': value(d, 'player_key'),
                  'cost': value(d, 'cost')} for d in entities(get(f'league/{league_key}/draftresults'), 'draft_result')]
        if not picks:
            raise ValueError('Draft results unavailable')
        known = dict(hub.get('playerStats', {}))
        unknown = sorted({d['playerKey'] for d in picks} - set(known))
        for start in range(0, len(unknown), 25):
            data = get(f'league/{league_key}/players;player_keys={",".join(unknown[start:start+25])}')
            known.update({p['key']: p for p in map(player, entities(data, 'player'))})
        for d in picks:
            p = known.get(d['playerKey'], {})
            d.update(name=p.get('name', 'Player unavailable'), position=p.get('position', ''))
        return sorted(picks, key=lambda p: int(p['pick'] or 0))
    section('draft', draft)

    def schedule():
        data = get(f'team/{keys[0]}/matchups;weeks={",".join(str(w) for w in range(1, end+1))}')
        # Request every team's schedule and deduplicate the pair for each week.
        all_data = [data] + [get(f'team/{k}/matchups') for k in keys[1:]]
        result, seen = {}, set()
        for data in all_data:
            for m in entities(data, 'matchup'):
                week = str(value(m, 'week', ''))
                pair = []
                for t in entities(m, 'team'):
                    pair.append({'key': value(t, 'team_key'), 'name': value(t, 'name', ''),
                                 'points': num(value(value(t, 'team_points', {}), 'total')),
                                 'projected': num(value(value(t, 'team_projected_points', {}), 'total'))})
                if len(pair) != 2:
                    continue
                identity = (week, tuple(sorted(p['key'] for p in pair)))
                if identity in seen:
                    continue
                seen.add(identity)
                result.setdefault(week, []).append({'teams': pair, 'status': value(m, 'status', ''),
                                                   'playoffs': value(m, 'is_playoffs', '0')})
        if not result:
            raise ValueError('No schedule')
        return result
    section('schedule', schedule)

    def playoffs():
        # Yahoo controls the actual bracket. Custom adjusted standings can show
        # a qualification picture, but must not invent Yahoo's final seeding.
        settings = get(f'league/{league_key}/settings')
        uses = value(settings, 'uses_playoff')
        start = value(settings, 'playoff_start_week')
        flag = str(uses).lower() if uses is not None else ''
        if flag in ('0', 'false'):
            return {'enabled': False, 'startWeek': None, 'endWeek': end,
                    'teamsCount': 0, 'weeks': {}}
        if flag not in ('1', 'true') and not (not flag and start is not None):
            raise ValueError('Yahoo playoff settings unavailable')
        start = int(start)
        count = int(value(settings, 'num_playoff_teams'))
        if not 1 <= start <= end or not 2 <= count <= len(keys):
            raise ValueError('Invalid Yahoo playoff settings')
        weeks = {}
        old_weeks = previous.get('playoffs', {}).get('weeks', {})
        for week in range(start, min(current, end) + 1):
            data = get(f'league/{league_key}/scoreboard;week={week}')
            games, seen = [], set()
            for matchup in entities(data, 'matchup'):
                raw_playoff = str(value(matchup, 'is_playoffs', '')).lower()
                raw_consolation = str(value(matchup, 'is_consolation', '')).lower()
                pair = []
                for team in entities(matchup, 'team'):
                    pair.append({'key': value(team, 'team_key'), 'name': value(team, 'name', ''),
                                 'points': num(value(value(team, 'team_points', {}), 'total'))})
                if len(pair) != 2 or any(not t['key'] or not t['name'] for t in pair):
                    continue
                identity = tuple(sorted(t['key'] for t in pair))
                if identity[0] == identity[1] or identity in seen:
                    continue
                seen.add(identity)
                consolation = (True if raw_consolation in ('1', 'true') else
                               False if raw_consolation in ('0', 'false') else None)
                playoff_flag = ('1' if raw_playoff in ('1', 'true') else
                                '0' if raw_playoff in ('0', 'false') else None)
                games.append({'teams': pair, 'status': value(matchup, 'status', ''),
                              'playoffs': playoff_flag,
                              'isConsolation': consolation,
                              'winnerKey': value(matchup, 'winner_team_key')})
            if len(games) < len(old_weeks.get(str(week), [])):
                raise ValueError('Previously published postseason matchups missing')
            if games:
                weeks[str(week)] = games
        return {'enabled': True, 'startWeek': start, 'endWeek': end,
                'teamsCount': count, 'weeks': weeks}
    section('playoffs', playoffs)
    print('League hub imported: ' + ', '.join(f'{k}={len(hub.get(k, []))}' for k in ['teams','rosters','playerStats','available','transactions','draft','schedule']))
    return hub
