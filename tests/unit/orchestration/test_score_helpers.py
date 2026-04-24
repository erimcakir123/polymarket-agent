"""score_helpers resolver + prefix parser unit tests."""
from __future__ import annotations

from src.orchestration.score_helpers import (
    resolve_tennis_league,
    slug_country_prefix,
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
