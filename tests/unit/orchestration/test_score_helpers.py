"""score_helpers resolver + prefix parser + NHL flag unit tests."""
from __future__ import annotations

from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.models.position import Position
from src.orchestration.score_helpers import (
    build_score_info,
    resolve_tennis_league,
    slug_country_prefix,
)


# ── NHL flag helpers ──

def _nhl_pos(direction: str = "BUY_YES", question: str = "Maple Leafs vs. Senators") -> Position:
    return Position(
        condition_id="c1",
        token_id="t1",
        direction=direction,
        entry_price=0.55,
        size_usdc=50,
        shares=90,
        current_price=0.50,
        anchor_probability=0.45,
        confidence="A",
        sport_tag="nhl",
        question=question,
        match_start_iso="2026-04-27T20:00:00Z",
    )


def _espn_nhl(
    home: str = "Toronto Maple Leafs",
    away: str = "Ottawa Senators",
    h_score: int = 2,
    a_score: int = 1,
    raw_status: dict | None = None,
) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id="nhl_e1",
        home_name=home,
        away_name=away,
        home_score=h_score,
        away_score=a_score,
        period="3rd Period",
        is_completed=False,
        is_live=True,
        last_updated="",
        linescores=[],
        raw_status=raw_status or {},
    )


class TestResolveTennisLeague:
    def test_wta_prefix_returns_wta(self):
        assert resolve_tennis_league("wta-rybakin-muchova-2026-04-19") == "wta"

    def test_atp_prefix_returns_atp(self):
        assert resolve_tennis_league("atp-rublev-fils-2026-04-19") == "atp"

    def test_empty_slug_returns_atp_default(self):
        assert resolve_tennis_league("") == "atp"

    def test_uppercase_wta_normalised(self):
        assert resolve_tennis_league("WTA-marcink-kasints-2026-04-21") == "wta"


class TestSlugCountryPrefix:
    def test_soccer_slug_returns_country_code(self):
        assert slug_country_prefix("arg-cac-pla-2026-04-20-pla") == "arg"

    def test_russian_slug(self):
        assert slug_country_prefix("rus-soc-kss-2026-04-21-kss") == "rus"

    def test_uefa_slug(self):
        assert slug_country_prefix("ucl-rma-mci-2026-05-06") == "ucl"

    def test_empty_slug_returns_empty(self):
        assert slug_country_prefix("") == ""

    def test_uppercase_normalised(self):
        assert slug_country_prefix("ARG-cac-pla") == "arg"

    def test_slug_without_dash_returns_whole_string(self):
        # Savunmacı: tek kelime — tüm string prefix olarak döner
        assert slug_country_prefix("randomstring") == "randomstring"


# ── NHL flag tests (Task 3B) ──

class TestBuildScoreInfoNHLFlags:
    """build_score_info() — is_overtime / is_shootout flag wiring via raw_status."""

    def test_nhl_regulation_play_flags_false(self) -> None:
        """3. periyot devam ederken her iki flag False olmalı."""
        raw = {
            "period": 3,
            "displayClock": "10:22",
            "type": {"state": "in", "detail": "3rd Period"},
        }
        info = build_score_info(_nhl_pos(), _espn_nhl(raw_status=raw))
        assert info["available"]
        assert info["is_overtime"] is False
        assert info["is_shootout"] is False

    def test_nhl_live_overtime_sets_is_overtime_true(self) -> None:
        """Canlı OT periyodunda is_overtime=True, is_shootout=False."""
        raw = {
            "period": 4,
            "displayClock": "3:45",
            "type": {"state": "in", "detail": "Overtime"},
        }
        info = build_score_info(_nhl_pos(), _espn_nhl(raw_status=raw))
        assert info["is_overtime"] is True
        assert info["is_shootout"] is False

    def test_nhl_live_shootout_sets_is_shootout_true(self) -> None:
        """Canlı SO periyodunda is_shootout=True, is_overtime=True (SO implies OT)."""
        raw = {
            "period": 5,
            "displayClock": "0:00",
            "type": {"state": "in", "detail": "Shootout"},
        }
        info = build_score_info(_nhl_pos(), _espn_nhl(raw_status=raw))
        assert info["is_shootout"] is True

    def test_nhl_final_ot_sets_is_overtime_true(self) -> None:
        """Final/OT sonrasında is_overtime=True."""
        raw = {
            "period": 4,
            "displayClock": "0:00",
            "type": {"state": "post", "detail": "Final/OT"},
        }
        info = build_score_info(_nhl_pos(), _espn_nhl(raw_status=raw))
        assert info["is_overtime"] is True
        assert info["is_shootout"] is False

    def test_nhl_empty_raw_status_defaults_to_false(self) -> None:
        """raw_status boş dict gelirse (non-hockey veya parse skip) flags False kalır."""
        info = build_score_info(_nhl_pos(), _espn_nhl(raw_status={}))
        assert info["available"]
        assert info["is_overtime"] is False
        assert info["is_shootout"] is False
