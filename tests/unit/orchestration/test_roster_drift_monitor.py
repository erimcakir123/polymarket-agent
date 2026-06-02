"""RosterDriftMonitor: lig içi takım drift + yeni lig keşfi tespiti."""
from __future__ import annotations

from unittest.mock import Mock

from src.orchestration.roster_drift_monitor import (
    DriftAlert,
    RosterDriftMonitor,
)


def _make_monitor(gamma_mock: Mock, league_dicts: dict | None = None) -> RosterDriftMonitor:
    return RosterDriftMonitor(
        gamma_client=gamma_mock,
        league_dicts=league_dicts if league_dicts is not None else {
            "bkligend": {"rea": "RM", "bar": "FCB"},
        },
    )


# ── A) Roster drift (lig içi takım listesi) ──

def test_missing_alias_triggers_warning() -> None:
    """Polymarket'te yeni alias var ama dict'te yok → warning."""
    gamma = Mock()
    gamma.fetch_teams_by_league_code.return_value = [
        {"alias": "Real Madrid", "abbreviation": "rea", "name": "Real Madrid"},
        {"alias": "Barcelona", "abbreviation": "bar", "name": "Barcelona"},
        {"alias": "Yeni Promosyon Kulubu", "abbreviation": "xyz", "name": "Yeni Promosyon Kulubu"},
    ]
    gamma.fetch_sports_metadata.return_value = []  # /sports boş

    monitor = _make_monitor(gamma)
    alerts = monitor.check_roster_drift()

    warning = [a for a in alerts if a.severity == "warning"]
    assert len(warning) == 1
    assert "ROSTER_DRIFT_bkligend" in warning[0].category
    assert "xyz" in warning[0].message
    assert "Yeni Promosyon Kulubu" in warning[0].message


def test_no_drift_no_alerts() -> None:
    """Polymarket alias'ları dict ile birebir → alert YOK."""
    gamma = Mock()
    gamma.fetch_teams_by_league_code.return_value = [
        {"alias": "Real Madrid", "abbreviation": "rea", "name": "Real Madrid"},
        {"alias": "Barcelona", "abbreviation": "bar", "name": "Barcelona"},
    ]
    monitor = _make_monitor(gamma)
    alerts = monitor.check_roster_drift()

    drift = [a for a in alerts if "ROSTER_DRIFT" in a.category]
    assert drift == []


def test_obsolete_slug_no_alert_intentional() -> None:
    """OBSOLETE check kasten KALDIRILDI — resolver dict çoklu name variant
    ile zenginleştirildi (alias+isim), Polymarket sadece kanonik abbr döner
    → obsolete diff her zaman büyük olur, anlamlı sinyal değil."""
    gamma = Mock()
    gamma.fetch_teams_by_league_code.return_value = [
        {"alias": "Real Madrid", "abbreviation": "rea", "name": "Real Madrid"},
        # "bar" yok artık (relegation simülasyonu)
    ]
    monitor = _make_monitor(gamma)
    alerts = monitor.check_roster_drift()
    obsolete = [a for a in alerts if "OBSOLETE" in a.category]
    assert obsolete == []  # KASITLI — obsolete check yok


def test_api_fetch_fail_skips_league_silently() -> None:
    """Gamma /teams API fail → o lig skip, exception fırlamaz."""
    gamma = Mock()
    gamma.fetch_teams_by_league_code.side_effect = ConnectionError("API down")
    monitor = _make_monitor(gamma)
    alerts = monitor.check_roster_drift()
    assert alerts == []  # fail tolere edildi


# ── B) Yeni lig keşfi (sport endpoint diff) ──

def test_new_league_detected(monkeypatch) -> None:
    """Polymarket'te bizim _SLUG_PREFIX_SPORT'ta olmayan basket lig → info."""
    gamma = Mock()
    gamma.fetch_sports_metadata.return_value = [
        {"sport": "bkligend", "resolution": "https://www.acb.com/"},  # bizde var
        {"sport": "bkfr1", "resolution": "https://lnb.fr/"},          # bizde YOK
        {"sport": "bkgr1", "resolution": "https://hellenic.gr/"},     # bizde YOK
        {"sport": "nba", "resolution": "https://nba.com/"},           # bk* değil, gormezden
    ]
    import src.infrastructure.apis.gamma_client as gc
    monkeypatch.setattr(gc, "_SLUG_PREFIX_SPORT", {"bkligend": "liga_acb"})

    monitor = _make_monitor(gamma)
    alerts = monitor.check_new_leagues()

    assert len(alerts) == 1
    a = alerts[0]
    assert a.severity == "info"
    assert a.category == "NEW_LEAGUE_DETECTED"
    assert "bkfr1" in a.message
    assert "lnb.fr" in a.message  # resolution URL
    assert "bkgr1" in a.message


def test_no_new_leagues_no_alert(monkeypatch) -> None:
    """Tüm bk* sport code'ları biliniyor → alert YOK."""
    gamma = Mock()
    gamma.fetch_sports_metadata.return_value = [
        {"sport": "bkligend", "resolution": "https://www.acb.com/"},
    ]
    import src.infrastructure.apis.gamma_client as gc
    monkeypatch.setattr(gc, "_SLUG_PREFIX_SPORT", {"bkligend": "liga_acb"})

    monitor = _make_monitor(gamma)
    alerts = monitor.check_new_leagues()
    assert alerts == []


def test_sports_api_fail_returns_empty() -> None:
    """/sports API fail → exception yutmadan boş döner, log yapar."""
    gamma = Mock()
    gamma.fetch_sports_metadata.side_effect = ConnectionError("API down")
    monitor = _make_monitor(gamma)
    alerts = monitor.check_new_leagues()
    assert alerts == []


# ── check_all integration ──

def test_check_all_combines_both_layers(monkeypatch) -> None:
    """check_all roster_drift + new_leagues birleşik alert listesi döner."""
    gamma = Mock()
    gamma.fetch_teams_by_league_code.return_value = [
        {"alias": "Yeni Takim", "abbreviation": "yeni_slug", "name": "Yeni Takim"},
    ]
    gamma.fetch_sports_metadata.return_value = [
        {"sport": "bkligend", "resolution": "https://acb.com/"},
        {"sport": "bk_yeni", "resolution": "https://yeni.com/"},
    ]
    import src.infrastructure.apis.gamma_client as gc
    monkeypatch.setattr(gc, "_SLUG_PREFIX_SPORT", {"bkligend": "liga_acb"})

    monitor = _make_monitor(gamma)
    alerts = monitor.check_all()
    cats = {a.category for a in alerts}
    assert "ROSTER_DRIFT_bkligend" in cats
    assert "NEW_LEAGUE_DETECTED" in cats


# ── DriftAlert dataclass davranışı ──

def test_drift_alert_frozen_dataclass() -> None:
    """DriftAlert frozen — mutation yasak (immutable identity)."""
    a = DriftAlert(severity="warning", category="X", message="m")
    try:
        a.severity = "info"  # type: ignore[misc]
        raise AssertionError("frozen dataclass mutation izin verdi")
    except Exception:
        pass  # FrozenInstanceError beklenir
