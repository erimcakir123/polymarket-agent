"""Chess match data -- Lichess + Chess.com dual source with Polymarket awareness.

Produces ESPN-compatible context strings with:
  - Last 10 decisive (non-draw) rated games per player -> [W]/[L] tokens
  - Recent form including draw count: "3W-9D-3L"
  - Explicit DRAW RATE line per player
  - Last 5 H2H games (deduplicated across both sources)
  - Polymarket sibling DRAW market price
  - Chess-specific AI warning about draw risk

Draws at elite chess level are 50-65% of classical games -- critical for
"Will X win?" markets which resolve NO on draws. This module makes the draw
risk explicit to the AI instead of burying it.

Thread-safe singleton with 1.1s serial rate limit and 6-hour stats cache.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz

from src.config import load_config
from src.chess_username_resolver import get_resolver
from src.tennis_tml import _parse_players_from_question  # helper reuse

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("logs/chess_cache")

_CHESSCOM_BASE = "https://api.chess.com/pub"
_LICHESS_BASE = "https://lichess.org/api"
_GAMMA_BASE = "https://gamma-api.polymarket.com"
_UA = "PolymarketAgent/1.0"


@dataclass
class ChessGame:
    date: str          # YYYY-MM-DD
    opponent: str
    won: Optional[bool]  # None = draw
    event: str
    speed: str         # classical/rapid/blitz/bullet
    source: str        # lichess/chesscom
    game_id: str       # for H2H dedup


@dataclass
class PlayerStats:
    real_name: str
    lichess_rapid: Optional[int]
    lichess_blitz: Optional[int]
    lichess_classical: Optional[int]
    chesscom_rapid: Optional[int]
    chesscom_blitz: Optional[int]
    games: list[ChessGame]  # merged from both sources, sorted desc by date
    fetched_at: float


class ChessDataClient:
    """Lichess + Chess.com merged data client with draw awareness."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cfg = load_config().chess
        self._stats_cache: dict[str, PlayerStats] = {}
        self._last_request_at: float = 0.0

    def _throttle(self) -> None:
        now = time.time()
        delta = now - self._last_request_at
        if delta < self._cfg.rate_limit_seconds:
            time.sleep(self._cfg.rate_limit_seconds - delta)
        self._last_request_at = time.time()

    # ── Public API ─────────────────────────────────────────────────

    def format_context(self, question: str, slug: str) -> Optional[str]:
        """Build chess context with [W]/[L] tokens + draw awareness.

        Returns None if:
          - Chess disabled in config
          - Could not extract both player names
          - Neither player has resolvable data
        """
        if not self._cfg.enabled:
            return None

        player_a, player_b = self._extract_players(question, slug)
        if not player_a or not player_b:
            logger.debug("Chess: could not parse players from %s", (slug or "")[:40])
            return None

        stats_a = self._get_player_stats(player_a)
        stats_b = self._get_player_stats(player_b)
        if not stats_a and not stats_b:
            return None

        parts: list[str] = ["=== CHESS DATA (Lichess + Chess.com) ==="]

        for label, name, stats in [
            ("PLAYER A", player_a, stats_a),
            ("PLAYER B", player_b, stats_b),
        ]:
            parts.append("")
            if not stats:
                parts.append(f"{label}: {name} -- no data available")
                continue
            parts.append(f"{label}: {name}")
            ratings = self._format_ratings(stats)
            if ratings:
                parts.append(f"  Ratings: {ratings}")

            recent = stats.games[:15]  # last 15 for form + draw rate calc
            wins = sum(1 for g in recent if g.won is True)
            losses = sum(1 for g in recent if g.won is False)
            draws = sum(1 for g in recent if g.won is None)
            total = wins + losses + draws
            draw_rate = (draws / total * 100) if total > 0 else 0
            parts.append(
                f"  Recent form ({total} games): {wins}W-{draws}D-{losses}L"
            )
            parts.append(f"  DRAW RATE: {draw_rate:.0f}%")

            # Last N decisive games -> [W]/[L] tokens
            decisive = [g for g in stats.games if g.won is not None][
                : self._cfg.max_games_per_player
            ]
            if decisive:
                parts.append(f"  Recent decisive ({len(decisive)} games):")
                for g in decisive:
                    result = "W" if g.won else "L"
                    parts.append(
                        f"    [{result}] vs {g.opponent} "
                        f"({g.speed}, {g.event}, {g.date})"
                    )

        # H2H section
        h2h = self._extract_h2h(
            stats_a.games if stats_a else [],
            stats_b.games if stats_b else [],
            player_a, player_b,
        )
        if h2h:
            a_wins = sum(1 for _, a_won in h2h if a_won is True)
            b_wins = sum(1 for _, a_won in h2h if a_won is False)
            h2h_draws = sum(1 for _, a_won in h2h if a_won is None)
            parts.append("")
            parts.append(
                f"H2H: {player_a} {a_wins}-{b_wins} {player_b} "
                f"({h2h_draws} draws)"
            )
            for g, a_won in h2h:
                if a_won is None:
                    continue  # draws excluded from token list
                opp_label = player_b if a_won else player_a
                result = "W" if a_won else "L"
                parts.append(
                    f"    [{result}] vs {opp_label} "
                    f"({g.speed}, {g.event}, {g.date})"
                )

        # Polymarket sibling prices (including draw)
        if self._cfg.fetch_polymarket_draw_price:
            poly_block = self._fetch_polymarket_prices(slug)
            if poly_block:
                parts.append("")
                parts.append(poly_block)

        # Chess draw warning (always present)
        parts.append("")
        parts.append(
            "=== CHESS DRAW WARNING ===\n"
            "At elite chess level, 50-65% of classical games and 30-40% of blitz "
            "games end in DRAWS. Polymarket 'Will X win?' markets resolve NO on "
            "draws. Discount P(YES) by each player's historical draw rate and the "
            "Polymarket draw market price before estimating edge. A 'favorite' "
            "at market price 55% may have true win probability near 30% due to "
            "draw mass. Favor NO when both players have high draw rates and the "
            "Polymarket draw market price is elevated."
        )
        return "\n".join(parts)

    # ── Player name extraction ─────────────────────────────────────

    def _extract_players(
        self, question: str, slug: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract player names from Polymarket event structure.

        Strategy 1: fetch market -> events[0].title -> regex parse
          Event title format: 'Player A vs. Player B - Tournament (Round N)'
        Strategy 2: parse question text
        """
        # Strategy 1: fetch event title (most reliable)
        try:
            self._throttle()
            resp = requests.get(
                f"{_GAMMA_BASE}/markets",
                params={"slug": slug},
                timeout=10,
            )
            if resp.status_code == 200:
                markets = resp.json()
                if markets and isinstance(markets, list):
                    events = markets[0].get("events") or []
                    if events:
                        event_title = events[0].get("title", "") or ""
                        m = re.match(r"(.+?)\s+vs\.?\s+(.+?)\s+-", event_title)
                        if m:
                            return m.group(1).strip(), m.group(2).strip()
        except Exception as exc:
            logger.debug("Chess event fetch failed for %s: %s", (slug or "")[:40], exc)

        # Strategy 2: fallback to question parsing
        return _parse_players_from_question(question)

    # ── Stats fetching ─────────────────────────────────────────────

    def _get_player_stats(self, real_name: str) -> Optional[PlayerStats]:
        """Fetch and cache player stats from both sources."""
        cache_key = real_name.lower().strip()
        cached = self._stats_cache.get(cache_key)
        if cached:
            age_hours = (time.time() - cached.fetched_at) / 3600
            if age_hours < self._cfg.stats_cache_hours:
                return cached

        resolver = get_resolver()
        resolved = resolver.resolve(real_name)
        if not resolved:
            logger.info("Chess: unresolved player %s", real_name)
            return None

        with self._lock:
            lichess_data = None
            chesscom_data = None
            if resolved.lichess and self._cfg.lichess_enabled:
                lichess_data = self._fetch_lichess(resolved.lichess)
            if resolved.chesscom and self._cfg.chesscom_enabled:
                chesscom_data = self._fetch_chesscom(resolved.chesscom)

            games: list[ChessGame] = []
            if lichess_data:
                games.extend(lichess_data.get("games") or [])
            if chesscom_data:
                games.extend(chesscom_data.get("games") or [])

            # Dedup by game_id, sort desc by date
            seen_ids: set[str] = set()
            unique: list[ChessGame] = []
            for g in games:
                gid = g.game_id or f"{g.source}-{g.date}-{g.opponent}"
                if gid in seen_ids:
                    continue
                seen_ids.add(gid)
                unique.append(g)
            unique.sort(key=lambda x: x.date, reverse=True)

            stats = PlayerStats(
                real_name=real_name,
                lichess_rapid=(lichess_data or {}).get("rapid"),
                lichess_blitz=(lichess_data or {}).get("blitz"),
                lichess_classical=(lichess_data or {}).get("classical"),
                chesscom_rapid=(chesscom_data or {}).get("rapid"),
                chesscom_blitz=(chesscom_data or {}).get("blitz"),
                games=unique,
                fetched_at=time.time(),
            )
            self._stats_cache[cache_key] = stats
            return stats

    # ── Lichess fetchers ───────────────────────────────────────────

    def _fetch_lichess(self, username: str) -> Optional[dict]:
        try:
            self._throttle()
            resp = requests.get(
                f"{_LICHESS_BASE}/user/{username}",
                headers={"User-Agent": _UA},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("disabled"):
                return None
            perfs = data.get("perfs") or {}
            rapid = (perfs.get("rapid") or {}).get("rating")
            blitz = (perfs.get("blitz") or {}).get("rating")
            classical = (perfs.get("classical") or {}).get("rating")

            games = self._fetch_lichess_games(username, max_games=20)
            return {
                "rapid": rapid, "blitz": blitz, "classical": classical,
                "games": games,
            }
        except Exception as exc:
            logger.debug("Lichess fetch failed for %s: %s", username, exc)
            return None

    def _fetch_lichess_games(self, username: str, max_games: int = 20) -> list[ChessGame]:
        """Fetch recent rated games from Lichess (NDJSON stream)."""
        games: list[ChessGame] = []
        try:
            self._throttle()
            resp = requests.get(
                f"{_LICHESS_BASE}/games/user/{username}",
                params={
                    "max": max_games,
                    "rated": "true",
                    "perfType": "blitz,rapid,classical",
                    "pgnInJson": "false",
                },
                headers={
                    "User-Agent": _UA,
                    "Accept": "application/x-ndjson",
                },
                timeout=20,
            )
            if resp.status_code != 200:
                return []
            for line in resp.text.splitlines():
                if not line.strip():
                    continue
                try:
                    g = json.loads(line)
                except json.JSONDecodeError:
                    continue
                players = g.get("players") or {}
                white_user = ((players.get("white") or {}).get("user") or {})
                black_user = ((players.get("black") or {}).get("user") or {})
                white = white_user.get("name") or ""
                black = black_user.get("name") or ""
                winner = g.get("winner")  # "white" | "black" | None (draw)
                created_at = g.get("createdAt", 0)
                date_str = ""
                if created_at:
                    try:
                        date_str = datetime.fromtimestamp(
                            created_at / 1000, tz=timezone.utc,
                        ).strftime("%Y-%m-%d")
                    except (ValueError, OSError):
                        date_str = ""

                if white.lower() == username.lower():
                    opp = black
                    won = (winner == "white") if winner else None
                elif black.lower() == username.lower():
                    opp = white
                    won = (winner == "black") if winner else None
                else:
                    continue

                games.append(ChessGame(
                    date=date_str,
                    opponent=opp or "?",
                    won=won,
                    event="Lichess",
                    speed=g.get("speed", "?"),
                    source="lichess",
                    game_id=g.get("id", "") or "",
                ))
        except Exception as exc:
            logger.debug("Lichess games fetch failed for %s: %s", username, exc)
        return games

    # ── Chess.com fetchers ─────────────────────────────────────────

    def _fetch_chesscom(self, username: str) -> Optional[dict]:
        try:
            self._throttle()
            resp = requests.get(
                f"{_CHESSCOM_BASE}/player/{username}/stats",
                headers={"User-Agent": _UA},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            rapid = ((data.get("chess_rapid") or {}).get("last") or {}).get("rating")
            blitz = ((data.get("chess_blitz") or {}).get("last") or {}).get("rating")

            games = self._fetch_chesscom_games(username, max_games=20)
            return {"rapid": rapid, "blitz": blitz, "games": games}
        except Exception as exc:
            logger.debug("Chess.com fetch failed for %s: %s", username, exc)
            return None

    def _fetch_chesscom_games(self, username: str, max_games: int = 20) -> list[ChessGame]:
        """Fetch current month + previous month games from Chess.com archive."""
        games: list[ChessGame] = []
        now = datetime.now(timezone.utc)
        months_to_try = [(now.year, now.month)]
        if now.month == 1:
            months_to_try.append((now.year - 1, 12))
        else:
            months_to_try.append((now.year, now.month - 1))

        draw_codes = {
            "agreed", "repetition", "stalemate",
            "timevsinsufficient", "insufficient", "50move",
        }

        for year, month in months_to_try:
            if len(games) >= max_games:
                break
            try:
                self._throttle()
                resp = requests.get(
                    f"{_CHESSCOM_BASE}/player/{username}/games/{year}/{month:02d}",
                    headers={"User-Agent": _UA},
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue
                month_games = resp.json().get("games", [])
                # Most recent first
                for g in reversed(month_games):
                    if len(games) >= max_games:
                        break
                    white = g.get("white") or {}
                    black = g.get("black") or {}
                    white_user = (white.get("username") or "").lower()
                    black_user = (black.get("username") or "").lower()
                    if username.lower() == white_user:
                        me_result = white.get("result")
                        opp = black.get("username") or ""
                    elif username.lower() == black_user:
                        me_result = black.get("result")
                        opp = white.get("username") or ""
                    else:
                        continue

                    # Only rated games
                    if not g.get("rated", True):
                        continue

                    if me_result == "win":
                        won: Optional[bool] = True
                    elif me_result in draw_codes:
                        won = None
                    else:
                        won = False

                    end_time = g.get("end_time", 0)
                    date_str = ""
                    if end_time:
                        try:
                            date_str = datetime.fromtimestamp(
                                end_time, tz=timezone.utc,
                            ).strftime("%Y-%m-%d")
                        except (ValueError, OSError):
                            date_str = ""

                    games.append(ChessGame(
                        date=date_str,
                        opponent=opp or "?",
                        won=won,
                        event="Chess.com",
                        speed=g.get("time_class", "?"),
                        source="chesscom",
                        game_id=g.get("url", "") or f"cc-{end_time}",
                    ))
            except Exception as exc:
                logger.debug("Chess.com games fetch failed for %s: %s", username, exc)
                continue
        return games

    # ── H2H extraction ─────────────────────────────────────────────

    def _extract_h2h(
        self,
        games_a: list[ChessGame],
        games_b: list[ChessGame],
        player_a: str,
        player_b: str,
    ) -> list[tuple[ChessGame, Optional[bool]]]:
        """Find games between A and B across both players' archives.

        Returns [(game, a_won), ...] sorted most recent first, deduplicated
        by game_id.
        """
        h2h: list[tuple[ChessGame, Optional[bool]]] = []
        seen: set[str] = set()

        # From A's games where opponent matches B
        for g in games_a:
            if _fuzzy_name_match(g.opponent, player_b):
                gid = g.game_id or f"a-{g.date}-{g.opponent}"
                if gid in seen:
                    continue
                seen.add(gid)
                h2h.append((g, g.won))

        # From B's games where opponent matches A (inverted, dedup)
        for g in games_b:
            if _fuzzy_name_match(g.opponent, player_a):
                gid = g.game_id or f"b-{g.date}-{g.opponent}"
                if gid in seen:
                    continue
                seen.add(gid)
                a_won = None if g.won is None else (not g.won)
                h2h.append((g, a_won))

        h2h.sort(key=lambda x: x[0].date, reverse=True)
        return h2h[: self._cfg.max_h2h_games]

    # ── Polymarket sibling market fetcher ──────────────────────────

    def _fetch_polymarket_prices(self, slug: str) -> Optional[str]:
        """Fetch all 3 markets (Player A / Player B / Draw) for this chess event.

        Returns formatted block like:
            === POLYMARKET PRICES (this event) ===
              Anish Giri: YES 42¢
              Hikaru Nakamura: YES 33¢
              Draw (Anish Giri vs. Hikaru Nakamura): YES 25¢
        """
        try:
            self._throttle()
            resp = requests.get(
                f"{_GAMMA_BASE}/markets",
                params={"slug": slug},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            markets = resp.json()
            if not markets or not isinstance(markets, list):
                return None
            events = markets[0].get("events") or []
            if not events:
                return None
            event_slug = events[0].get("slug", "") or ""
            if not event_slug:
                return None

            # Fetch all markets for this event
            self._throttle()
            ev_resp = requests.get(
                f"{_GAMMA_BASE}/events",
                params={"slug": event_slug},
                timeout=10,
            )
            if ev_resp.status_code != 200:
                return None
            ev_data = ev_resp.json()
            if not ev_data or not isinstance(ev_data, list):
                return None
            all_markets = ev_data[0].get("markets") or []
            if len(all_markets) < 2:
                return None

            lines = ["=== POLYMARKET PRICES (this event) ==="]
            for mk in all_markets:
                label = mk.get("groupItemTitle") or mk.get("question", "")
                prices_raw = mk.get("outcomePrices", "[]")
                try:
                    prices = json.loads(prices_raw)
                    yes_price = float(prices[0]) if prices else 0.0
                except (json.JSONDecodeError, IndexError, ValueError, TypeError):
                    continue
                lines.append(f"  {label}: YES {yes_price*100:.0f}\u00a2")
            if len(lines) <= 1:
                return None
            return "\n".join(lines)
        except Exception as exc:
            logger.debug("Polymarket prices fetch failed for %s: %s",
                         (slug or "")[:40], exc)
            return None

    @staticmethod
    def _format_ratings(stats: PlayerStats) -> str:
        parts = []
        if stats.lichess_rapid or stats.lichess_blitz or stats.lichess_classical:
            bits = []
            if stats.lichess_classical:
                bits.append(f"classical {stats.lichess_classical}")
            if stats.lichess_rapid:
                bits.append(f"rapid {stats.lichess_rapid}")
            if stats.lichess_blitz:
                bits.append(f"blitz {stats.lichess_blitz}")
            if bits:
                parts.append("Lichess: " + " | ".join(bits))
        if stats.chesscom_rapid or stats.chesscom_blitz:
            bits = []
            if stats.chesscom_rapid:
                bits.append(f"rapid {stats.chesscom_rapid}")
            if stats.chesscom_blitz:
                bits.append(f"blitz {stats.chesscom_blitz}")
            if bits:
                parts.append("Chess.com: " + " | ".join(bits))
        return " | ".join(parts)


# ── Module-level helpers ───────────────────────────────────────────────────

def _fuzzy_name_match(name_a: str, name_b: str) -> bool:
    """Return True if the two names plausibly refer to the same person."""
    na = (name_a or "").lower().strip()
    nb = (name_b or "").lower().strip()
    if not na or not nb:
        return False
    # Quick substring match (handles short usernames vs full names)
    if na in nb or nb in na:
        return True
    return fuzz.WRatio(na, nb) >= 80


# ── Singleton ──────────────────────────────────────────────────────

_singleton: Optional[ChessDataClient] = None
_singleton_lock = threading.Lock()


def get_chess_data() -> ChessDataClient:
    """Return the shared ChessDataClient singleton (thread-safe)."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ChessDataClient()
    return _singleton
