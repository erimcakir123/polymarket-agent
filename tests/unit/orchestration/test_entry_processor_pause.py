from unittest.mock import MagicMock

from src.domain.control.trading_control import TradingControl
from src.orchestration.entry_processor import EntryProcessor


def _deps(paused: bool):
    deps = MagicMock()
    deps.state.trading_control = TradingControl(paused=paused)
    deps.state.config.mode.value = "paper"
    return deps


def test_paused_skips_scan():
    deps = _deps(paused=True)
    EntryProcessor(deps).run_heavy()
    deps.scanner.scan.assert_not_called()


def test_not_paused_runs_scan():
    # paused=False → pause kapısı geçilir, scan'e ulaşılır. Heavy cycle'ın
    # devamı (gate/clip/execute) MagicMock ile koşmaz — bu testin konusu DEĞİL;
    # tek doğrulanan: pause kapısı bloke etmiyor (scan çağrıldı).
    deps = _deps(paused=False)
    deps.scanner.scan.return_value = []
    deps.mlb_submarket_engine = None
    try:
        EntryProcessor(deps).run_heavy()
    except Exception:  # noqa: BLE001 — downstream MagicMock detayı testin kapsamı dışı
        pass
    deps.scanner.scan.assert_called_once()
