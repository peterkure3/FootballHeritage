"""Collect public sportsbook responses and timestamped football 1x2 snapshots."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import re
from pathlib import Path
import sys
import time
from uuid import uuid4
from urllib.parse import urlsplit
from typing import Any, Callable

import requests

sys.path.append(str(Path(__file__).parent.parent))
from config import BASE_DIR, RAW_DATA_DIR, THE_ODDS_API_KEY, THE_ODDS_API_BASE_URL
from etl.sportsbook_parsers import normalize_bovada
from etl.scrapling_transport import RobotsDisallowed
from etl.regional_sportsbooks import normalize_ababet, normalize_fortebet, normalize_betpawa, normalize_sportpesa, normalize_betika, normalize_cloudbet, normalize_1xbet, normalize_22bet, normalize_betonline, normalize_bookmaker

DIRECT_URLS = {
    "draftkings": "https://sportsbook.draftkings.com/sports/soccer",
    "fanduel": "https://sportsbook.fanduel.com/soccer",
    "betmgm": "https://sports.nj.betmgm.com/en/sports/football-4",
    "caesars": "https://sportsbook.caesars.com/",
    "thescorebet": "https://sportsbook.thescore.bet/",
    "fanatics": "https://sportsbook.fanatics.com/",
    "bet365": "https://www.bet365.com/",
    "betrivers": "https://www.betrivers.com/",
    "hardrockbet": "https://app.hardrock.bet/",
    "circa": "https://www.circasports.com/betting-menu-odds",
    "superbook": "https://www.superbook.com/",
    "ballybet": "https://play.ballybet.com/",
    "betfred": "https://www.betfred.com/sports/football",
    "betonlineag": "https://api-offering.betonline.ag/api/offering/Sports/offering-by-scheduletext",
    "bovada": "https://www.bovada.lv/services/sports/event/coupon/events/A/description/soccer?marketFilterId=def&preMatchOnly=true",
    "mybookieag": "https://www.mybookie.ag/",
    "bookmaker": "https://lines.bookmaker.eu/en/sports/soccer/uefa-champions-league/",
    "heritagesports": "https://heritagesports.eu/en",
    "everygame": "https://sports.everygame.eu/en",
    "sportsbettingag": "https://www.sportsbetting.ag/sportsbook/soccer",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def valid_price(value: object) -> float | None:
    try:
        price = float(value)
        return price if math.isfinite(price) and price > 1 else None
    except (TypeError, ValueError):
        return None


def request_primary_source(request: Callable[..., requests.Response], url: str, **kwargs: Any) -> requests.Response:
    """Retry transient transport failures only; denied/rate-limited responses return immediately."""
    for attempt in range(3):
        try:
            return request(url, **kwargs)
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def get_public_source(book: str, url: str, output: Path, http=None) -> dict:
    """Bounded anonymous public reads; no retries against denied access."""
    row = {"bookmaker": book, "source_url": url, "requested_at": utc_now(), "snapshots": 0}
    try:
        http = http or requests
        request = http.get
        kwargs = {}
        headers = {"User-Agent": "FootballHeritage public-odds collector/1.0", "Accept": "application/json,text/html"}
        if book == 'fortebet':
            headers['Referer'] = 'https://www.fortebet.ug/'
        if book == 'betonlineag':
            request = http.post
            headers.update({'gsetting': 'bolsassite', 'Origin': 'https://www.betonline.ag',
                'Referer': 'https://www.betonline.ag/', 'utc-offset': '0'})
            kwargs['json'] = {'Sport': 'soccer', 'League': 'uefa-cl',
                'ScheduleText': 'uefa-champions-league', 'filterTime': 0}
        if book == 'betika':
            headers.update({'Origin': 'https://www.betika.com', 'Referer': 'https://www.betika.com/'})
            kwargs['params'] = {'page': 1, 'limit': 1000, 'sub_type_id': '1', 'sport_id': '3',
                                'sort_id': 2, 'period_id': 9, 'esports': 'false'}
        if book == 'cloudbet':
            headers.update({'Referer': 'https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events',
                            'x-cloudbet-version': 'v1.2.27'})
            kwargs['params'] = [('from', str(int(datetime.now(timezone.utc).timestamp()))),
                ('include-all-event-types', 'false'), ('include-pretrading', 'false'), ('limit', '25'),
                ('locale', 'en'), ('markets', 'soccer.match_odds'), ('sports', 'soccer')]
        if book in {'1xbet', '22bet'}:
            referer = ('https://1xbet.com/en/line/football/' if book == '1xbet' else 'https://22bet.ug/line/football/') + '118587-uefa-champions-league'
            headers.update({'Referer': referer,
                'is-srv': 'false', 'x-app-n': '__BETTING_APP__',
                'x-requested-with': 'XMLHttpRequest', 'x-svc-source': '__BETTING_APP__'})
            kwargs['params'] = {'cfView': 3, 'count': 40, 'fcountry': 191, 'gr': 285,
                'grMode': 4, 'lng': 'en', 'ref': 1, 'selectedMs': '1.1.118587,2.1.118587'}
            if book == '22bet':
                kwargs['params'].update(gr=337, lng='en_GB', ref=151)
        if book == 'sportpesa':
            kwargs['params'] = {'sportId':1,'leagueId':70,'markets_layout':'single','page':1}
            metadata = http.get('https://www.sportpesa.com/api/default/markets',headers=headers,timeout=(5,15))
            (output/'raw/sportpesa_definitions.json').write_bytes(metadata.content)
            if metadata.status_code != 200:
                return row | {'http_status':metadata.status_code,'status':'market_definitions_unavailable','observed_at':utc_now()}
            definitions = [market for sport in metadata.json() if sport.get('sportId') == 1
                for market in sport.get('markets', []) if market.get('id') == 10 and market.get('specValue') == 0]
            if len(definitions) != 1 or definitions[0].get('name') != '1X2' or [selection['shortName'] for selection in definitions[0]['selections']] != ['1','X','2']:
                raise ValueError('Unverified SportPesa standard football market')
        if book == 'betpawa':
            # Public brand identifier comes from the operator's jurisdiction directory.
            headers.update({'X-Pawa-Brand':'betpawa-uganda','X-Pawa-Language':'en','Content-Type':'application/json'})
            metadata = http.get('https://www.betpawa.ug/api/sportsbook/v4/categories/list/2', headers=headers, timeout=(5,15))
            (output/'raw/betpawa_categories.json').write_bytes(metadata.content)
            if metadata.status_code != 200:
                return row | {'http_status':metadata.status_code,'status':'category_directory_unavailable','observed_at':utc_now()}
            ids = [competition['competition']['id'] for category in metadata.json().get('withRegions', [])
                   for region in category.get('regions', [])
                   for competition in region.get('competitions', [])
                   if (region['region']['name'], competition['competition']['name']) in {
                       ('England', 'Premier League'), ('International', 'UEFA Champions League')}]
            if not ids or len(ids) != len(set(ids)):
                return row | {'status':'ambiguous_competition_directory','observed_at':utc_now()}
            kwargs['params'] = {'q': json.dumps({'queries':[{'query':{'eventType':'UPCOMING','categories':['2'],
                'zones':{'competitions':[competition]},'hasOdds':True},'sort':{'startTime':'ASC'},'take':100}
                for competition in ids]})}
        send = request_primary_source if book == 'bovada' else lambda request, url, **kwargs: request(url, **kwargs)
        response = send(request, url, timeout=(5, 15), **kwargs, headers=headers)
        response_body = response.content
        if book == 'betika' and response.ok:
            payload = response.json()
            events = payload.get('data') or []
            total = int(payload.get('meta', {}).get('total') or len(events))
            page_count = (total + 999) // 1000
            if page_count > 5:
                return row | {'status': 'pagination_limit_exceeded', 'observed_at': utc_now()}
            pages = []
            raw_page = output / 'raw' / 'betika_page1.json'
            raw_page.write_bytes(response.content)
            pages.append(str(raw_page.relative_to(output)))
            for page in range(2, page_count + 1):
                page_response = http.get(url, headers=headers, timeout=(5, 15),
                    params=kwargs['params'] | {'page': page})
                page_response.raise_for_status()
                raw_page = output / 'raw' / f'betika_page{page}.json'
                raw_page.write_bytes(page_response.content)
                pages.append(str(raw_page.relative_to(output)))
                events.extend(page_response.json().get('data') or [])
            if len(events) != total or len({str(event['match_id']) for event in events}) != len(events):
                return row | {'status': 'pagination_incomplete', 'observed_at': utc_now()}
            payload['data'] = events
            response_body = json.dumps(payload).encode('utf-8')
            row['raw_pages'] = pages
        observed = utc_now()
        content_type = response.headers.get("Content-Type", "")
        suffix = ".json" if "json" in content_type else ".html"
        raw = output / "raw" / (book + suffix)
        raw.write_bytes(response_body)
        row.update(http_status=response.status_code, observed_at=observed,
                   final_url=response.url, content_type=content_type,
                   bytes=len(response_body), raw_capture_ref=str(raw.relative_to(output)))
        if book == 'sportpesa':
            row['content_range'] = response.headers.get('Content-Range')
        if response.status_code in {401, 403, 451}:
            row["status"] = "access_denied"
        elif response.status_code == 429:
            row["status"] = "rate_limited"
        elif not response.ok:
            row["status"] = "http_error"
        elif "_cf_chl_opt" in response.text or "<title>Just a moment" in response.text:
            row["status"] = "access_challenge"
        else:
            row["status"] = "public_response_needs_adapter"
    except RobotsDisallowed as exc:
        row.update(status="robots_disallowed", error_type=type(exc).__name__, observed_at=utc_now())
    except requests.RequestException as exc:
        row.update(status="connection_failed", error_type=type(exc).__name__, observed_at=utc_now())
    except (ValueError, KeyError, TypeError) as exc:
        row.update(status="source_metadata_invalid", error_type=type(exc).__name__, observed_at=utc_now())
    return row


def collect_target(target: dict, output: Path, http=None) -> dict:
    """Resolve researched inventory URLs; unresolved brands do not break a run."""
    book = target["bookmaker"]
    if not re.fullmatch(r"[a-z0-9_]+", book):
        raise ValueError("Bookmaker IDs must be safe stable slugs")
    url = DIRECT_URLS.get(book) or target.get("source_url")
    if book == 'fortebet':
        url = 'https://www.fortebet.ug/api/web/v1/offer/full-prematch-en'
    if book == 'betika':
        url = 'https://api-ug.betika.com/v1/uo/matches'
    if book == 'betpawa':
        url = 'https://www.betpawa.ug/api/sportsbook/v4/events/lists/by-queries'
    if book == 'sportpesa':
        url = 'https://www.sportpesa.com/api/upcoming/games'
    if not url:
        return {"bookmaker": book, "region": target.get("region"),
                "status": "source_verification_pending", "snapshots": 0}
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Public source must be an HTTPS URL without credentials")
    options = {'http': http} if http is not None else {}
    return get_public_source(book, url, output, **options) | {"region": 'GLOBAL' if book == 'sportpesa' else target.get("region")}


def normalize_provider_events(events: list[dict], targets: list[dict], observed: str,
                              raw_ref: str, run_id: str) -> list[dict]:
    """Convert observed provider h2h markets; keep collection route explicit."""
    mapping = {book["oddsapi"]["key"]: book["bookmaker"] for book in targets
               if book.get("oddsapi") and book["bookmaker"] != "bet365"}
    snapshots = []
    observation_time = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    for event in events:
        if not str(event.get("sport_key", "")).startswith("soccer_"):
            continue
        try:
            kickoff = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
            if kickoff.tzinfo is None or kickoff <= observation_time:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        home, away = event.get("home_team"), event.get("away_team")
        if not home or not away or home == away or not event.get("id"):
            continue
        for book in event.get("bookmakers", []):
            identity = mapping.get(book.get("key"))
            if identity is None:
                continue
            for market in book.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = {}
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    selection = "HOME" if name == home else "AWAY" if name == away else "DRAW" if str(name).casefold() == "draw" else None
                    price = valid_price(outcome.get("price"))
                    if selection and price:
                        if selection in outcomes:
                            outcomes = {}
                            break
                        outcomes[selection] = {"selection": selection, "selection_name_raw": name,
                                               "odds_decimal": price, "status": "UNKNOWN",
                                               "line": None, "participant": None}
                if set(outcomes) != {"HOME", "DRAW", "AWAY"}:
                    continue
                snapshots.append({"schema_version": "1.0", "snapshot_id": str(uuid4()),
                    "provider": "oddsapi", "collection_route": "provider_feed",
                    "bookmaker": identity, "provider_book_key": book["key"],
                    "provider_event_id": str(event["id"]), "sport": "football",
                    "competition": event.get("sport_title") or event["sport_key"],
                    "competition_key": event["sport_key"], "home_team": home, "away_team": away,
                    "commence_time": event["commence_time"], "observed_at": observed,
                    "source_updated_at": market.get("last_update") or book.get("last_update"),
                    "is_live": False, "event_status": "SCHEDULED", "market": "h2h",
                    "period": "FULL_TIME_90_MIN", "settlement_rule": "REGULATION_TIME",
                    "market_status": "UNKNOWN", "availability_note": "Provider returned prices but no explicit open/suspended flag; execution availability not verified.",
                    "outcomes": [outcomes[key] for key in ["HOME", "DRAW", "AWAY"]],
                    "region": None, "source_url": f"{THE_ODDS_API_BASE_URL}/sports/{event['sport_key']}/odds",
                    "scraper_version": "1.0.0", "scrape_run_id": run_id, "raw_capture_ref": raw_ref})
    return snapshots


def collect_provider(targets: list[dict], sports: list[str], output: Path, run_id: str) -> tuple[list[dict], list[dict]]:
    """Use the existing provider only when explicitly requested by CLI."""
    if not THE_ODDS_API_KEY or THE_ODDS_API_KEY.startswith("YOUR_"):
        return [], [{"status": "missing_provider_key"}]
    keys = sorted({book["oddsapi"]["key"] for book in targets
                   if book.get("oddsapi") and book["bookmaker"] != "bet365"})
    records, reports = [], []
    for sport in sports:
        endpoint = f"{THE_ODDS_API_BASE_URL}/sports/{sport}/odds"
        report = {"sport": sport, "endpoint": endpoint, "bookmaker_keys": keys}
        try:
            response = requests.get(endpoint, params={"apiKey": THE_ODDS_API_KEY,
                "bookmakers": ",".join(keys), "markets": "h2h", "oddsFormat": "decimal", "dateFormat": "iso"}, timeout=(5, 20))
            observed = utc_now()
            report.update(http_status=response.status_code, observed_at=observed,
                          quota_remaining=response.headers.get("x-requests-remaining"),
                          quota_last_cost=response.headers.get("x-requests-last"))
            if response.ok:
                events = response.json()
                if not isinstance(events, list):
                    raise ValueError("Provider response must be an event list")
                raw = output / "raw" / f"oddsapi_{sport}.json"
                raw.write_text(json.dumps({"fetched_at": observed, "events": events}, indent=2), encoding="utf-8")
                snapshots = normalize_provider_events(events, targets, observed, str(raw.relative_to(output)), run_id)
                records.extend(snapshots)
                report.update(status="collected", events=len(events), snapshots=len(snapshots))
            else:
                report["status"] = "provider_rejected"
                # Never log response URLs/exceptions containing the API key.
                try:
                    body = response.json()
                    report["error_code"] = body.get("error_code") if isinstance(body, dict) else None
                except ValueError:
                    pass
        except (requests.RequestException, ValueError) as exc:
            report.update(status="provider_failed", error_type=type(exc).__name__)
        reports.append(report)
        if report.get("http_status") in {401, 403, 429}:
            break
    return records, reports


def normalize_saved_run(output: Path) -> dict:
    """Export a derived dataset without refetching or changing the original capture."""
    report = json.loads((output / "source_report.json").read_text(encoding="utf-8"))
    existing = [json.loads(line) for line in (output / "odds_snapshots.jsonl").read_text(encoding="utf-8").splitlines() if line]
    records = list(existing)
    for source in report["direct_sources"]:
        book = source['bookmaker']
        parsers = {'bovada': normalize_bovada, 'fortebet': normalize_fortebet, 'betika': normalize_betika, 'cloudbet': normalize_cloudbet, '1xbet': normalize_1xbet, '22bet': normalize_22bet, 'betonlineag': normalize_betonline, 'bookmaker': normalize_bookmaker,
                   'ababet': normalize_ababet, 'betpawa': normalize_betpawa, 'sportpesa':normalize_sportpesa}
        if book not in parsers or source.get("http_status") not in {200,206}:
            continue
        if any(record["bookmaker"] == book and record["collection_route"] == "direct_public_feed" for record in existing):
            continue
        body = (output / source["raw_capture_ref"]).read_text(encoding="utf-8")
        payload = body if book in {'ababet', 'bookmaker'} else json.loads(body)
        kwargs = {'source_url': source['source_url']} if book == 'fortebet' else {}
        parsed = parsers[book](payload, source["observed_at"], source["raw_capture_ref"], report["run_id"], **kwargs)
        records.extend(parsed)
        source.update(status="collected", snapshots=len(parsed))
    with (output / "odds_snapshots_complete.jsonl").open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
    report.update(normalized_at=utc_now(), snapshot_count=len(records),
                  snapshots_by_bookmaker={book: sum(record["bookmaker"] == book for record in records) for book in report["snapshots_by_bookmaker"]},
                  dataset="odds_snapshots_complete.jsonl")
    with (output / "normalization_report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=BASE_DIR.parent / "_config/bookmakers.json")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--transport", choices=['requests', 'scrapling'], default='requests')
    parser.add_argument("--provider-fallback", action="store_true")
    parser.add_argument("--provider-only", action="store_true", help="Collect mapped bookmaker feeds without repeating public-site requests")
    parser.add_argument("--normalize-run", type=Path, help="Normalize an existing capture without network requests")
    parser.add_argument("--sports", nargs="+", default=["soccer_epl", "soccer_uefa_champs_league"])
    args = parser.parse_args()
    if args.normalize_run:
        print(json.dumps(normalize_saved_run(args.normalize_run), indent=2))
        return
    if any(not sport.startswith("soccer_") or not all(c.isalnum() or c == "_" for c in sport) for sport in args.sports):
        parser.error("Only soccer provider sport keys are supported")
    targets = json.loads(args.targets.read_text(encoding="utf-8"))["sportsbooks"]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output_dir or RAW_DATA_DIR / "sportsbooks" / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw").mkdir()
    direct = []
    if not args.provider_only:
        http = None
        if args.transport == 'scrapling':
            from etl.scrapling_transport import ScraplingTransport
            http = ScraplingTransport()
        with ThreadPoolExecutor(max_workers=4) as executor:
            direct = list(executor.map(lambda book: collect_target(book, output, http=http), targets))
    records = []
    for source in direct:
        if source["bookmaker"] in {"bovada", "fortebet", "ababet", "betpawa", "sportpesa", "betika", "cloudbet", "1xbet", "22bet", "betonlineag", "bookmaker"} and source.get("http_status") in {200,206}:
            try:
                body = (output / source["raw_capture_ref"]).read_text(encoding="utf-8")
                parser = {"bovada": normalize_bovada, "fortebet": normalize_fortebet, "betika": normalize_betika, 'cloudbet': normalize_cloudbet, '1xbet': normalize_1xbet, '22bet': normalize_22bet, 'betonlineag': normalize_betonline, 'bookmaker': normalize_bookmaker, "ababet": normalize_ababet, 'betpawa':normalize_betpawa,'sportpesa':normalize_sportpesa}[source['bookmaker']]
                payload = body if source['bookmaker'] in {'ababet', 'bookmaker'} else json.loads(body)
                kwargs = {'source_url': source['source_url']} if source['bookmaker'] == 'fortebet' else {}
                parsed = parser(payload, source["observed_at"], source["raw_capture_ref"], run_id, **kwargs)
                records.extend(parsed)
                source.update(status="collected" if parsed else "no_complete_upcoming_1x2", snapshots=len(parsed))
            except (ValueError, TypeError, KeyError) as exc:
                source.update(status="parser_failed", error_type=type(exc).__name__)
    feed_records, provider = collect_provider(targets, args.sports, output, run_id) if args.provider_fallback or args.provider_only else ([], [])
    records.extend(feed_records)
    with (output / "odds_snapshots.jsonl").open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
    counts = {book["bookmaker"]: sum(record["bookmaker"] == book["bookmaker"] for record in records) for book in targets}
    report = {"run_id": run_id, "completed_at": utc_now(), "output": str(output), "transport": args.transport,
              "direct_sources": direct, "provider_requests": provider,
              "snapshot_count": len(records), "snapshots_by_bookmaker": counts,
              "database_writes": False, "active_model_changed": False}
    (output / "source_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
