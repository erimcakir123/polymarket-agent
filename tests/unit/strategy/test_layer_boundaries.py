"""ARCH_GUARD Kural 1 — strategy katmanı infrastructure import etmemeli.

Strategy işi: domain kurallarını birleştirip karar üretmek. Dosya I/O, API,
WS, dashboard logger → hepsi infrastructure işi. Strategy orchestration'dan
veri alır, veri döner; infra'yı doğrudan çağırmaz.

TDD §12 Başarı Kriterleri: "gate.py skipped_trade_logger çağırmıyor" — bu
testle statik olarak korunur.
"""
from __future__ import annotations

from pathlib import Path

_STRATEGY_ROOT = Path(__file__).resolve().parents[3] / "src" / "strategy"

_FORBIDDEN = (
    "from src.infrastructure",
    "import src.infrastructure",
)


def test_strategy_modules_do_not_import_infrastructure() -> None:
    offenders: list[str] = []
    for py in _STRATEGY_ROOT.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        source = py.read_text(encoding="utf-8")
        for pattern in _FORBIDDEN:
            if pattern in source:
                offenders.append(f"{py.relative_to(_STRATEGY_ROOT)}: {pattern}")
    assert offenders == [], (
        "Strategy katmanı infrastructure import ediyor (ARCH_GUARD Kural 1 ihlali):\n  "
        + "\n  ".join(offenders)
    )


def test_strategy_root_directory_exists() -> None:
    """Sanity: test path doğru resolve ediliyor."""
    assert _STRATEGY_ROOT.is_dir(), f"Not a directory: {_STRATEGY_ROOT}"
