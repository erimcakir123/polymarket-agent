"""Avrupa basket scraper'lar — edge case + silent fail davranışı.

Production'da silent fail tehlikeli — özellikle:
  - React-rendered sayfa (BeautifulSoup statik HTML'de game div bulamaz)
  - CSS selector değişti (siyah kutu site evrim)
  - Cloudflare/anti-bot karşılığında HTML başka şey (login/captcha)
  - Encoding yanlış (Türkçe ş/ç bozulur → name mapping fail)

Bu testler MEVCUT davranışı belgeler — hangileri silent fail yapıyor görmek
için. SCRAPER_ZERO_PARSED_DATA gibi yeni koruma eklenirse bu testler değişir.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import requests

from src.infrastructure.data.basketball.acb_scraper import AcbScraper
from src.infrastructure.data.basketball.base_scraper import EuropeanBasketScraper
from src.infrastructure.data.basketball.bsl_scraper import BslScraper
from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.lega_scraper import LegaScraper
from src.infrastructure.data.basketball.vtb_scraper import VtbScraper


SCRAPERS = [AcbScraper, BslScraper, LegaScraper, VtbScraper]


def _health(tmp_path: Path) -> HealthTracker:
    return HealthTracker(tmp_path / "h.json")


# ── 1. React-rendered sayfa: HTML var ama game/team CSS selector hit yok ──

@pytest.mark.parametrize("scraper_cls", SCRAPERS)
def test_react_rendered_page_triggers_zero_parsed_data_fail(
    tmp_path: Path, scraper_cls: type[EuropeanBasketScraper],
) -> None:
    """ZERO_PARSED_DATA koruması: React shell → teams=[] + games=[] → fail.

    Silent success eski davranıştı; 2026-06-03'te base_scraper.refresh()'e
    "hem teams hem games boş → fail" koruması eklendi. Bu test korumanın
    devrede olduğunu doğrular.
    """
    react_shell = (
        '<html><head><title>App</title></head>'
        '<body><div id="root"></div><script src="bundle.js"></script></body></html>'
    )
    health = _health(tmp_path)
    sc = scraper_cls(
        health=health,
        http_get=lambda url: react_shell,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ZERO_PARSED_DATA" in (result.error or "")
    assert health.consecutive_fails(scraper_cls.SOURCE) == 1


# ── 2. HTTP error path (Cloudflare 403 / 500 / timeout) ──

@pytest.mark.parametrize("scraper_cls", SCRAPERS)
def test_cloudflare_403_records_failure(
    tmp_path: Path, scraper_cls: type[EuropeanBasketScraper],
) -> None:
    """Anti-bot 403 → HTTPError → retry x3 → record_failure."""
    def cloudflare_block(url: str) -> str:
        r = requests.Response()
        r.status_code = 403
        raise requests.HTTPError("403 Forbidden", response=r)

    health = _health(tmp_path)
    sc = scraper_cls(
        health=health, http_get=cloudflare_block, sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "HTTPError" in (result.error or "")
    assert health.consecutive_fails(scraper_cls.SOURCE) == 1


@pytest.mark.parametrize("scraper_cls", SCRAPERS)
def test_timeout_records_failure(
    tmp_path: Path, scraper_cls: type[EuropeanBasketScraper],
) -> None:
    """ConnectionError/Timeout → retry x3 → record_failure."""
    def timeout(url: str) -> str:
        raise requests.Timeout("Read timed out")

    health = _health(tmp_path)
    sc = scraper_cls(
        health=health, http_get=timeout, sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "Timeout" in (result.error or "")


# ── 3. Bilinmeyen takım (yeni promosyon, dict eksik) ──

def test_acb_unknown_team_silently_skipped(tmp_path: Path) -> None:
    """ZAYIFLIK BELGELEME: Bilinmeyen takım row sessizce skip — log YOK.

    Yeni takım promosyonu olursa (örn ACB'ye yeni terfi eden kulüp),
    resolver dict'i güncellenene kadar bu satırlar görülmez.
    Fixture eurobasket pattern (acb_scraper.py 2026-06-03 revize sonrası).
    """
    html = """
    <html><body><table>
      <tr>
        <td class="GamesDate">Jun.3:</td>
        <td class="GamesTeam TextAlignRight">Yeni Promosyon Kulubu</td>
        <td class="GamesResult TextAlignCenter">90-85</td>
        <td class="GamesTeam TextAlignLeft">Real Mad.</td>
      </tr>
      <tr>
        <td class="GamesDate">Jun.3:</td>
        <td class="GamesTeam TextAlignRight">Valencia</td>
        <td class="GamesResult TextAlignCenter">88-80</td>
        <td class="GamesTeam TextAlignLeft">Barca</td>
      </tr>
    </table></body></html>
    """
    health = _health(tmp_path)
    sc = AcbScraper(health=health, http_get=lambda url: html, sleep_fn=lambda s: None)
    result = sc.refresh("2025-26")
    assert result.ok is True
    # SADECE bilinen Valencia/Barca maçı parse edildi
    assert len(result.games) == 1
    assert result.games[0].home_team == "VAL"
    # Yeni takım sessizce dropped — log yok, alert yok


# ── 4. Encoding: Türkçe ş/ç/ğ + Cyrillic ──

def test_bsl_turkish_chars_parse_correctly(tmp_path: Path) -> None:
    """Beşiktaş/Bahçeşehir Türkçe karakter doğru parse — utf-8 default."""
    html = """
    <html><body>
      <div class="game-row">
        <a>Beşiktaş</a>
        <span>[85-80]</span>
        <a>Bahçeşehir</a>
        <span>3 Haziran 2026</span>
      </div>
    </body></html>
    """
    health = _health(tmp_path)
    sc = BslScraper(health=health, http_get=lambda url: html, sleep_fn=lambda s: None)
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert len(result.games) == 1
    g = result.games[0]
    assert g.home_team == "BES" and g.away_team == "BAH"


# ── 5. Malformed: score var ama takım eksik / takım var score eksik ──

def test_acb_score_without_teams_triggers_zero_parsed_data(tmp_path: Path) -> None:
    """Score var ama takım linki yok → row skip → teams=[]+games=[] → fail.

    Exception fırlamadı (row sessizce dropped) ama agregat ZERO_PARSED_DATA
    koruması yakaladı. Bu doğru: tek row patternde tüm row'lar bozuksa site
    yapısı değişmiş demektir.
    """
    html = """
    <html><body>
      <div class="partido">
        <span class="resultado">85 - 78</span>
        <span class="fecha">1 de junio de 2026</span>
      </div>
    </body></html>
    """
    health = _health(tmp_path)
    sc = AcbScraper(health=health, http_get=lambda url: html, sleep_fn=lambda s: None)
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ZERO_PARSED_DATA" in (result.error or "")


def test_acb_teams_without_score_skipped(tmp_path: Path) -> None:
    """Takım var ama score yok (TBD/upcoming "----") → row skip, teams kalır.

    Eurobasket henüz oynanmamış maç için "----" döner. _parse_one_game None
    döner ama _parse_teams takım hücrelerinden takımları alır → teams dolu
    kalır → ZERO_PARSED_DATA tetiklenmez (teams>0). Bu beklenen davranış.
    """
    html = """
    <html><body><table>
      <tr>
        <td class="GamesDate">Jun.10:</td>
        <td class="GamesTeam TextAlignRight">Real Mad.</td>
        <td class="GamesResult TextAlignCenter">----</td>
        <td class="GamesTeam TextAlignLeft">Barca</td>
      </tr>
    </table></body></html>
    """
    health = _health(tmp_path)
    sc = AcbScraper(health=health, http_get=lambda url: html, sleep_fn=lambda s: None)
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.games == ()  # henüz oynanmamış → skip
    assert "RM" in result.teams  # takım sayfada var ama oyun yok


# ── 6. Aynı takım kendisine karşı (data corruption) ──

def test_acb_team_vs_itself_skipped(tmp_path: Path) -> None:
    """ZAYIFLIK: Aynı takım iki kez → home==away durumunda kabul edilir mi?

    Mevcut acb parser: home_abbr != away_abbr şartı VAR → skip ✓
    """
    html = """
    <html><body><table>
      <tr>
        <td class="GamesDate">Jun.1:</td>
        <td class="GamesTeam TextAlignRight">Real Mad.</td>
        <td class="GamesResult TextAlignCenter">85-78</td>
        <td class="GamesTeam TextAlignLeft">Real Mad.</td>
      </tr>
    </table></body></html>
    """
    health = _health(tmp_path)
    sc = AcbScraper(health=health, http_get=lambda url: html, sleep_fn=lambda s: None)
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.games == ()  # home==away skip


# ── 7. Empty HTTP response ──

@pytest.mark.parametrize("scraper_cls", SCRAPERS)
def test_empty_response_triggers_zero_parsed_data_fail(
    tmp_path: Path, scraper_cls: type[EuropeanBasketScraper],
) -> None:
    """ZERO_PARSED_DATA: HTTP boş string → teams=[] + games=[] → fail."""
    health = _health(tmp_path)
    sc = scraper_cls(
        health=health, http_get=lambda url: "", sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ZERO_PARSED_DATA" in (result.error or "")
    assert health.consecutive_fails(scraper_cls.SOURCE) == 1
