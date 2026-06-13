# Tenis Taze Sonuç Hasadı + Bayatlık Koruması — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tenis Glicko reytinglerini her gün Polymarket çözülmüş marketlerinden toplanan taze sonuçlarla güncel tutmak; bayat veriyle model bahsini engellemek.

**Architecture:** Polymarket çözülmüş marketlerinden (kazanan/kaybeden) günlük hasat → jsonl depo → `build_tennis_ratings` bu sonuçları Glicko fit'ine ekler (servis motoruna değil). İlk çalıştırma 14 günü geri-doldurur. Reyting verisi 4 günden eskiyse model bahsi yapılmaz (bayatlık koruması).

**Tech Stack:** Python 3.12, mevcut `GammaClient`, `fit_ratings` (Glicko), `extract_teams`, `_resolve_player_name`, jsonl. Spec: `docs/superpowers/specs/2026-06-13-tennis-fresh-results-harvest-design.md`.

**ARCH_GUARD self-check (her Edit/Write öncesi):** ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok (config), ✓ utils yok, ✓ sessiz hata yok, ✓ P(YES) anchor.

---

## Dosya Yapısı

| Dosya | Katman | Sorumluluk |
|---|---|---|
| `src/domain/pricing/tennis/harvested_result.py` | Domain | `HarvestedResult` dataclass + `winner_loser_from_resolution()` saf fonksiyon |
| `src/infrastructure/data/tennis_results_store.py` | Infra/data | jsonl yaz/oku + dedupe + maç-anahtarı |
| `src/orchestration/tennis_seen_markets.py` | Orchestration | Loglardan görülen tenis (cid, question, ts) topla |
| `src/orchestration/tennis_results_harvester.py` | Orchestration | fetch→extract→resolve→surface→HarvestedResult akışı |
| `scripts/build_tennis_ratings.py` | Script | Taze sonuçları Glicko fit'ine ekle (MODIFY) |
| `src/orchestration/factory_refresh_hooks.py` | Orchestration | Günlük hasat + geri-doldurma hook (MODIFY) |
| `src/domain/analysis/enrich_outcome.py` | Domain | `MODEL_DATA_STALE` fail reason (MODIFY) |
| `src/strategy/enrichment/tennis_dispatch.py` | Strategy | Bayatlık koruması: stale → model skip (MODIFY) |
| `src/config/tennis_settings.py` + `config.yaml` | Config | `staleness_threshold_days=4`, `backfill_days=14` (MODIFY) |
| `src/orchestration/factory.py` | Orchestration | Bayatlık flag hesabı + dispatch'e geçir (MODIFY) |

---

## Task 1: HarvestedResult + kazanan çıkarımı (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/harvested_result.py`
- Test: `tests/unit/domain/pricing/tennis/test_harvested_result.py`

- [ ] **Step 1: Write the failing test**

```python
"""harvested_result — taze sonuç dataclass + kazanan çıkarımı testleri."""
from src.domain.pricing.tennis.harvested_result import (
    HarvestedResult,
    winner_loser_from_resolution,
)


def _resolved(prices: str) -> dict:
    return {"closed": True, "umaResolutionStatus": "resolved", "outcomePrices": prices}


def test_yes_side_won_returns_player_a_as_winner():
    # prices=['1','0'] → YES (ilk oyuncu) kazandı
    out = winner_loser_from_resolution(_resolved('["1","0"]'), "Alice", "Bob")
    assert out == ("Alice", "Bob")


def test_no_side_won_returns_player_b_as_winner():
    out = winner_loser_from_resolution(_resolved('["0","1"]'), "Alice", "Bob")
    assert out == ("Bob", "Alice")


def test_unresolved_market_returns_none():
    m = {"closed": False, "umaResolutionStatus": "", "outcomePrices": '["1","0"]'}
    assert winner_loser_from_resolution(m, "Alice", "Bob") is None


def test_void_5050_payout_returns_none():
    # 0.5/0.5 → iptal/void, sonuç yok
    assert winner_loser_from_resolution(_resolved('["0.5","0.5"]'), "Alice", "Bob") is None


def test_missing_player_name_returns_none():
    assert winner_loser_from_resolution(_resolved('["1","0"]'), "", "Bob") is None
    assert winner_loser_from_resolution(_resolved('["1","0"]'), "Alice", None) is None


def test_harvested_result_key_is_order_independent_on_pair():
    r = HarvestedResult(winner="Alice", loser="Bob", surface="Clay", date="20260612")
    assert r.match_key() == "20260612|Alice|Bob"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/domain/pricing/tennis/test_harvested_result.py -v`
Expected: FAIL with ImportError (module yok)

- [ ] **Step 3: Write minimal implementation**

```python
"""Taze maç sonucu — saf domain dataclass + çözülmüş market'ten kazanan çıkarımı.

Polymarket question "Tournament: A vs B" → YES=A (ilk), NO=B (ikinci).
outcomePrices=['1','0'] → A kazandı; ['0','1'] → B kazandı; ['0.5','0.5'] → void (None).
Glicko reytingi için skor gerekmez — sadece (kazanan, kaybeden, zemin, tarih).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

_VOID_PAYOUT = 0.5
_VOID_TOL = 0.01


@dataclass(frozen=True)
class HarvestedResult:
    winner: str
    loser: str
    surface: str  # "Hard" | "Clay" | "Grass" | "Unknown"
    date: str     # YYYYMMDD

    def match_key(self) -> str:
        return f"{self.date}|{self.winner}|{self.loser}"


def winner_loser_from_resolution(
    market: dict, player_a: str, player_b: str
) -> tuple[str, str] | None:
    """Çözülmüş market + oyuncu adları → (kazanan, kaybeden). Çözülmemiş/void → None.

    player_a = YES tarafı (ilk isim), player_b = NO tarafı (ikinci isim).
    """
    if not player_a or not player_b:
        return None
    if not market.get("closed") or market.get("umaResolutionStatus") != "resolved":
        return None
    prices = market.get("outcomePrices", "[]")
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            return None
    if not isinstance(prices, list) or len(prices) < 2:
        return None
    try:
        yes_payout = float(prices[0])
        no_payout = float(prices[1])
    except (ValueError, TypeError):
        return None
    if abs(yes_payout - _VOID_PAYOUT) < _VOID_TOL:
        return None  # void/iptal
    if yes_payout >= 0.99:
        return (player_a, player_b)
    if no_payout >= 0.99:
        return (player_b, player_a)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/domain/pricing/tennis/test_harvested_result.py -v`
Expected: PASS (6 test)

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/harvested_result.py tests/unit/domain/pricing/tennis/test_harvested_result.py
git commit -m "feat(tennis): HarvestedResult + cozulmus market kazanan cikarimi (domain, TDD)"
```

---

## Task 2: Sonuç deposu (Infra/data)

**Files:**
- Create: `src/infrastructure/data/tennis_results_store.py`
- Test: `tests/unit/infrastructure/data/test_tennis_results_store.py`

- [ ] **Step 1: Write the failing test**

```python
"""tennis_results_store — taze sonuç jsonl yaz/oku/dedupe testleri."""
from src.domain.pricing.tennis.harvested_result import HarvestedResult
from src.infrastructure.data.tennis_results_store import (
    append_results,
    harvested_keys,
    load_results,
)


def _r(w, l, d="20260612", s="Clay"):
    return HarvestedResult(winner=w, loser=l, surface=s, date=d)


def test_append_then_load_roundtrip(tmp_path):
    p = tmp_path / "res.jsonl"
    append_results([_r("Alice", "Bob"), _r("Carol", "Dave")], p)
    out = load_results(p)
    assert len(out) == 2
    assert out[0].winner == "Alice" and out[0].surface == "Clay"


def test_append_dedupes_same_match_key(tmp_path):
    p = tmp_path / "res.jsonl"
    append_results([_r("Alice", "Bob")], p)
    append_results([_r("Alice", "Bob"), _r("Eve", "Frank")], p)
    out = load_results(p)
    assert len(out) == 2  # Alice/Bob tekrar yazılmadı


def test_harvested_keys_returns_existing_match_keys(tmp_path):
    p = tmp_path / "res.jsonl"
    append_results([_r("Alice", "Bob", d="20260610")], p)
    keys = harvested_keys(p)
    assert "20260610|Alice|Bob" in keys


def test_load_missing_file_returns_empty(tmp_path):
    assert load_results(tmp_path / "yok.jsonl") == []


def test_load_skips_corrupt_line(tmp_path):
    p = tmp_path / "res.jsonl"
    p.write_text('{"winner":"A","loser":"B","surface":"Clay","date":"20260612"}\nBOZUK\n', encoding="utf-8")
    out = load_results(p)
    assert len(out) == 1 and out[0].winner == "A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/infrastructure/data/test_tennis_results_store.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

```python
"""Taze tenis sonuçları jsonl deposu — append-only + maç-anahtarı dedupe.

Infrastructure: dosya I/O sınırda; domain HarvestedResult döner. Bozuk satır
atlanır + log (ARCH_GUARD Kural 12).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.domain.pricing.tennis.harvested_result import HarvestedResult

logger = logging.getLogger(__name__)


def load_results(path: Path) -> list[HarvestedResult]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[HarvestedResult] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            out.append(HarvestedResult(
                winner=d["winner"], loser=d["loser"],
                surface=d.get("surface", "Unknown"), date=d["date"],
            ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("tennis_results_store: bozuk satır atlandı: %s", e)
    return out


def harvested_keys(path: Path) -> set[str]:
    return {r.match_key() for r in load_results(path)}


def append_results(results: list[HarvestedResult], path: Path) -> int:
    """Yeni (dedupe edilmiş) sonuçları ekle. Eklenen satır sayısını döner."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = harvested_keys(p)
    added = 0
    with open(p, "a", encoding="utf-8") as f:
        for r in results:
            if r.match_key() in existing:
                continue
            existing.add(r.match_key())
            f.write(json.dumps({
                "winner": r.winner, "loser": r.loser,
                "surface": r.surface, "date": r.date,
            }, ensure_ascii=False) + "\n")
            added += 1
    return added
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/infrastructure/data/test_tennis_results_store.py -v`
Expected: PASS (5 test)

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/data/tennis_results_store.py tests/unit/infrastructure/data/test_tennis_results_store.py
git commit -m "feat(tennis): taze sonuc jsonl deposu + dedupe (infra, TDD)"
```

---

## Task 3: Görülen tenis marketleri toplayıcı (Orchestration)

**Files:**
- Create: `src/orchestration/tennis_seen_markets.py`
- Test: `tests/unit/orchestration/test_tennis_seen_markets.py`

Görülen tenis maçları append-only `logs/runtime/skipped_trades.jsonl` + `logs/audit/trade_events.jsonl`'den toplanır (14 günlük geçmiş retain edilir). Her kayıt: condition_id, question, sport_tag, timestamp.

- [ ] **Step 1: Write the failing test**

```python
"""tennis_seen_markets — loglardan görülen tenis (cid, question) toplama."""
import json

from src.orchestration.tennis_seen_markets import collect_seen_tennis_markets


def _write(p, rows):
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_collects_tennis_dedupes_by_condition_id(tmp_path):
    skip = tmp_path / "skipped.jsonl"
    trades = tmp_path / "trades.jsonl"
    _write(skip, [
        {"condition_id": "0xa", "question": "Lyon: A vs B", "sport_tag": "tennis", "timestamp": "2026-06-12T10:00:00+00:00"},
        {"condition_id": "0xb", "question": "NBA X vs Y", "sport_tag": "nba", "timestamp": "2026-06-12T10:00:00+00:00"},
    ])
    _write(trades, [
        {"kind": "entry", "condition_id": "0xa", "question": "Lyon: A vs B", "sport_tag": "tennis", "entry_timestamp": "2026-06-12T09:00:00+00:00"},
        {"kind": "entry", "condition_id": "0xc", "question": "Modena: C vs D", "sport_tag": "tennis", "entry_timestamp": "2026-06-12T11:00:00+00:00"},
    ])
    out = collect_seen_tennis_markets([skip, trades])
    cids = {m["condition_id"] for m in out}
    assert cids == {"0xa", "0xc"}  # nba elendi, 0xa dedupe edildi


def test_missing_files_return_empty(tmp_path):
    assert collect_seen_tennis_markets([tmp_path / "yok.jsonl"]) == []


def test_since_cutoff_filters_old_markets(tmp_path):
    skip = tmp_path / "skipped.jsonl"
    _write(skip, [
        {"condition_id": "0xold", "question": "Lyon: A vs B", "sport_tag": "tennis", "timestamp": "2026-05-20T10:00:00+00:00"},
        {"condition_id": "0xnew", "question": "Modena: C vs D", "sport_tag": "tennis", "timestamp": "2026-06-12T10:00:00+00:00"},
    ])
    out = collect_seen_tennis_markets([skip], since_yyyymmdd="20260601")
    cids = {m["condition_id"] for m in out}
    assert cids == {"0xnew"}  # 05-20 backfill penceresi dışı, elendi
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/orchestration/test_tennis_seen_markets.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

```python
"""Loglardan görülen tenis marketlerini topla (hasat girdisi).

Append-only skip + trade loglarından tenis condition_id + question + timestamp
toplar, condition_id ile dedupe eder. ITF/Challenger dahil tam değerlendirme evreni.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_TENNIS_TAGS = frozenset({"tennis", "atp", "wta"})


def collect_seen_tennis_markets(
    log_paths: list[Path], since_yyyymmdd: str | None = None
) -> list[dict]:
    """[{condition_id, question, ts}] — tenis, condition_id ile dedupe.

    since_yyyymmdd verilirse ts'i bu tarihten eski kayıtlar elenir (backfill penceresi).
    """
    by_cid: dict[str, dict] = {}
    for path in log_paths:
        p = Path(path)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (d.get("sport_tag") or "").lower() not in _TENNIS_TAGS:
                continue
            cid = d.get("condition_id")
            q = d.get("question")
            if not cid or not q:
                continue
            ts = d.get("timestamp") or d.get("entry_timestamp") or ""
            if since_yyyymmdd and ts:
                ts_ymd = ts[:10].replace("-", "")
                if ts_ymd and ts_ymd < since_yyyymmdd:
                    continue
            if cid not in by_cid:
                by_cid[cid] = {"condition_id": cid, "question": q, "ts": ts}
    return list(by_cid.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/orchestration/test_tennis_seen_markets.py -v`
Expected: PASS (2 test)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/tennis_seen_markets.py tests/unit/orchestration/test_tennis_seen_markets.py
git commit -m "feat(tennis): gorulen tenis marketleri toplayici (orch, TDD)"
```

---

## Task 4: Sonuç hasatçısı (Orchestration)

**Files:**
- Create: `src/orchestration/tennis_results_harvester.py`
- Test: `tests/unit/orchestration/test_tennis_results_harvester.py`

Akış: görülen market → gamma'dan çözülmüş market → kazanan tarafı oku → isimleri Sackmann'a çöz → zemini turnuva adından bul → HarvestedResult. Zaten hasat edilmiş anahtarlar atlanır.

- [ ] **Step 1: Write the failing test**

```python
"""tennis_results_harvester — fetch→extract→resolve→surface akış testleri."""
from src.orchestration.tennis_results_harvester import harvest_results


class _FakeGamma:
    def __init__(self, by_cid):
        self._by_cid = by_cid
    def fetch_closed_market_by_condition(self, cid):
        return self._by_cid.get(cid)


def _resolved(prices):
    return {"closed": True, "umaResolutionStatus": "resolved", "outcomePrices": prices}


def test_harvests_resolved_match_with_resolved_names_and_surface():
    seen = [{"condition_id": "0xa", "question": "Lyon: Galan vs Trungelliti", "ts": "2026-06-11T18:00:00+00:00"}]
    gamma = _FakeGamma({"0xa": _resolved('["1","0"]')})  # YES (Galan) kazandı
    ratings = {"Daniel Elahi Galan": object(), "Marco Trungelliti": object()}
    surface_map = {"lyon": "Clay"}

    def resolve_name(name):
        for full in ratings:
            if name.split()[-1].lower() in full.lower():
                return full
        return None

    out = harvest_results(
        seen, gamma, resolve_name=resolve_name, surface_map=surface_map,
        already_keys=set(), today_yyyymmdd="20260613",
    )
    assert len(out) == 1
    assert out[0].winner == "Daniel Elahi Galan"
    assert out[0].loser == "Marco Trungelliti"
    assert out[0].surface == "Clay"


def test_skips_unresolved_market():
    seen = [{"condition_id": "0xa", "question": "Lyon: A vs B", "ts": "2026-06-11T18:00:00+00:00"}]
    gamma = _FakeGamma({"0xa": {"closed": False}})
    out = harvest_results(seen, gamma, resolve_name=lambda n: n, surface_map={},
                          already_keys=set(), today_yyyymmdd="20260613")
    assert out == []


def test_skips_unresolvable_name():
    seen = [{"condition_id": "0xa", "question": "Lyon: Ghost vs Phantom", "ts": "2026-06-11T18:00:00+00:00"}]
    gamma = _FakeGamma({"0xa": _resolved('["1","0"]')})
    out = harvest_results(seen, gamma, resolve_name=lambda n: None, surface_map={},
                          already_keys=set(), today_yyyymmdd="20260613")
    assert out == []


def test_skips_already_harvested_key():
    seen = [{"condition_id": "0xa", "question": "Lyon: Galan vs Trungelliti", "ts": "2026-06-11T18:00:00+00:00"}]
    gamma = _FakeGamma({"0xa": _resolved('["1","0"]')})
    # already_keys, sonuç anahtarını içeriyorsa gamma'ya bile gidilmez/atlanır
    out = harvest_results(
        seen, gamma, resolve_name=lambda n: n.split()[-1], surface_map={"lyon": "Clay"},
        already_keys={"20260613|Galan|Trungelliti"}, today_yyyymmdd="20260613",
    )
    assert out == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/orchestration/test_tennis_results_harvester.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

```python
"""Polymarket çözülmüş marketlerinden taze tenis sonucu hasadı (Orchestration).

Katmanları koordine eder: gamma (infra) + extract_teams/_resolve (strategy) +
winner_loser_from_resolution (domain) + surface_map (infra). Saf değil — I/O
gamma çağrısı yapar; ama gamma DI ile verilir (test fake).
"""
from __future__ import annotations

import logging
from typing import Callable

from src.domain.pricing.tennis.harvested_result import (
    HarvestedResult,
    winner_loser_from_resolution,
)
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.tennis_dispatch import _extract_location, _match_surface

logger = logging.getLogger(__name__)


def harvest_results(
    seen_markets: list[dict],
    gamma_client,
    resolve_name: Callable[[str], str | None],
    surface_map: dict[str, str],
    already_keys: set[str],
    today_yyyymmdd: str,
    max_fetches: int = 400,
) -> list[HarvestedResult]:
    """Görülen tenis marketlerinden çözülenlerin sonucunu topla.

    resolve_name: Polymarket adı → Sackmann adı (çözülemez → None).
    today_yyyymmdd: sonuç tarihi (çözüm günü; sıralama + dedupe için).
    max_fetches: gamma çağrı tavanı (rate-limit nezaketi).
    """
    out: list[HarvestedResult] = []
    fetches = 0
    for m in seen_markets:
        if fetches >= max_fetches:
            logger.info("Harvest fetch tavanı (%d) — kalan atlandı", max_fetches)
            break
        question = m.get("question") or ""
        a_raw, b_raw = extract_teams(question)
        if not a_raw or not b_raw:
            continue
        win_a, win_b = resolve_name(a_raw), resolve_name(b_raw)
        if not win_a or not win_b:
            continue
        # Çözüm-öncesi dedupe denemesi (her iki yön de mümkün; key kazananla kurulur,
        # gamma'dan önce bilemeyiz → gamma sonrası key kontrolü). Burada gamma çağrısı:
        market = gamma_client.fetch_closed_market_by_condition(m.get("condition_id"))
        fetches += 1
        pair = winner_loser_from_resolution(market or {}, win_a, win_b)
        if pair is None:
            continue
        winner, loser = pair
        key = f"{today_yyyymmdd}|{winner}|{loser}"
        if key in already_keys:
            continue
        loc = _extract_location(question)
        surface = (_match_surface(loc, surface_map) if loc else None) or "Unknown"
        already_keys.add(key)
        out.append(HarvestedResult(winner=winner, loser=loser, surface=surface, date=today_yyyymmdd))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/orchestration/test_tennis_results_harvester.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/tennis_results_harvester.py tests/unit/orchestration/test_tennis_results_harvester.py
git commit -m "feat(tennis): polymarket sonuc hasatcisi (orch, TDD)"
```

---

## Task 5: Reyting birleştirme (Build script)

**Files:**
- Modify: `scripts/build_tennis_ratings.py`
- Test: `tests/integration/test_build_tennis_ratings.py` (yeni test ekle)

`build_ratings`'e `recent_results: list[HarvestedResult] | None` parametresi ekle. Taze çiftler fit_ratings'e (genel + zemin) eklenir; serve_stats'a DOKUNULMAZ.

- [ ] **Step 1: Write the failing test** (mevcut test dosyasının sonuna ekle)

```python
def test_recent_results_merged_into_ratings_not_serve(tmp_path):
    """Taze sonuç Glicko reytingini değiştirir, servis istatistiğine girmez."""
    from scripts.build_tennis_ratings import build_ratings
    from src.domain.pricing.tennis.harvested_result import HarvestedResult
    import json

    csv_path = tmp_path / "atp_matches_2026.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    out = tmp_path / "ratings.json"

    # Bob taze sonuçta Alice'i yener (CSV'de Alice kazanıyordu)
    recent = [HarvestedResult(winner="Bob", loser="Alice", surface="Hard", date="20260612")]
    build_ratings(tmp_path, out, recent_results=recent)

    data = json.loads(out.read_text(encoding="utf-8"))
    # Taze galibiyetle Bob'un mu'su CSV-only halinden YUKSEK olmalı
    assert data["Bob"]["rating"]["mu"] > 1340  # CSV-only ~1337 idi
    # Servis: Bob taze sonuçta serve verisi yok → serve_by_surface boş/değişmemiş
    assert "serve" not in data["Bob"] or data["Bob"].get("serve") in (None, {}, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_build_tennis_ratings.py::test_recent_results_merged_into_ratings_not_serve -v`
Expected: FAIL (recent_results parametresi yok → TypeError)

- [ ] **Step 3: Modify `build_ratings` signature + merge**

`scripts/build_tennis_ratings.py` içinde imzayı ve fit çağrılarını değiştir:

```python
def build_ratings(
    cache_dir: Path,
    output_path: Path,
    surface_output_path: Path | None = None,
    recent_results: list | None = None,  # list[HarvestedResult]
) -> None:
```

`all_matches.sort(...)` satırından SONRA, fit çağrılarını şu şekilde değiştir:

```python
    recent = recent_results or []
    # Taze (kazanan, kaybeden) çiftleri — Sackmann'dan SONRA (daha yeni, kronoloji korunur).
    overall_pairs = [(m.winner_name, m.loser_name) for m in all_matches] + [
        (r.winner, r.loser) for r in recent
    ]
    serve_stats = aggregate_serve_stats(all_matches)  # taze sonuç serve'e GIRMEZ
    ratings = fit_ratings(overall_pairs)
```

Ve `by_surface` bloğunu şu şekilde değiştir:

```python
    by_surface = {
        surf: fit_ratings(
            [(m.winner_name, m.loser_name) for m in all_matches if m.surface == surf]
            + [(r.winner, r.loser) for r in recent if r.surface == surf]
        )
        for surf in _VALID_SURFACES
    }
```

`main()`'i de taze sonuçları yükleyecek şekilde güncelle:

```python
def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from src.infrastructure.data.tennis_results_store import load_results
    recent = load_results(Path("data/tennis_recent_results.jsonl"))
    if recent:
        logger.info("Taze sonuç birleştiriliyor: %d maç", len(recent))
    build_ratings(_DEFAULT_CACHE_DIR, _DEFAULT_OUTPUT, recent_results=recent)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_build_tennis_ratings.py -v`
Expected: PASS (mevcut + yeni test)

- [ ] **Step 5: Commit**

```bash
git add scripts/build_tennis_ratings.py tests/integration/test_build_tennis_ratings.py
git commit -m "feat(tennis): build_ratings taze sonuclari Glicko fit'ine ekler, serve'e dokunmaz (TDD)"
```

---

## Task 6: Günlük hasat + geri-doldurma hook (Orchestration)

**Files:**
- Modify: `src/orchestration/factory_refresh_hooks.py`
- Test: `tests/unit/orchestration/test_harvest_hook.py`

`maybe_harvest_and_rebuild(...)` fonksiyonu: görülen marketleri topla → hasat et → depoya yaz → reytingleri yeniden kur. Bağımlılıklar DI ile (test edilebilir).

- [ ] **Step 1: Write the failing test**

```python
"""harvest hook — toplama→hasat→depo→rebuild orkestrasyon testi."""
from src.orchestration.factory_refresh_hooks import maybe_harvest_and_rebuild


def test_harvest_writes_results_and_calls_rebuild(tmp_path, monkeypatch):
    store = tmp_path / "recent.jsonl"
    rebuilt = {"called": False}

    def fake_collect(paths):
        return [{"condition_id": "0xa", "question": "Lyon: Galan vs Trungelliti", "ts": "2026-06-11T18:00:00+00:00"}]

    def fake_harvest(seen, gamma, resolve_name, surface_map, already_keys, today_yyyymmdd, **kw):
        from src.domain.pricing.tennis.harvested_result import HarvestedResult
        return [HarvestedResult(winner="Daniel Elahi Galan", loser="Marco Trungelliti", surface="Clay", date=today_yyyymmdd)]

    def fake_rebuild():
        rebuilt["called"] = True

    maybe_harvest_and_rebuild(
        gamma_client=object(), resolve_name=lambda n: n, surface_map={},
        store_path=store, log_paths=[], today_yyyymmdd="20260613",
        collect_fn=fake_collect, harvest_fn=fake_harvest, rebuild_fn=fake_rebuild,
    )
    from src.infrastructure.data.tennis_results_store import load_results
    assert len(load_results(store)) == 1
    assert rebuilt["called"] is True


def test_harvest_no_new_results_skips_rebuild(tmp_path):
    store = tmp_path / "recent.jsonl"
    rebuilt = {"called": False}
    maybe_harvest_and_rebuild(
        gamma_client=object(), resolve_name=lambda n: n, surface_map={},
        store_path=store, log_paths=[], today_yyyymmdd="20260613",
        collect_fn=lambda paths: [], harvest_fn=lambda *a, **k: [],
        rebuild_fn=lambda: rebuilt.__setitem__("called", True),
    )
    assert rebuilt["called"] is False  # yeni sonuç yok → boşuna rebuild yok
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/orchestration/test_harvest_hook.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Add `maybe_harvest_and_rebuild` to `factory_refresh_hooks.py`**

```python
def maybe_harvest_and_rebuild(
    *,
    gamma_client,
    resolve_name,
    surface_map: dict,
    store_path: Path,
    log_paths: list[Path],
    today_yyyymmdd: str,
    since_yyyymmdd: str | None = None,
    collect_fn=None,
    harvest_fn=None,
    rebuild_fn=None,
) -> int:
    """Taze sonuç hasadı → depo → reyting rebuild. Eklenen sonuç sayısını döner.

    collect/harvest/rebuild DI ile (test). Default'lar gerçek implementasyonlar.
    since_yyyymmdd: backfill penceresi (bu tarihten eski market elenir).
    Yeni sonuç yoksa rebuild atlanır (boşuna iş yok).
    """
    from src.infrastructure.data.tennis_results_store import (
        append_results,
        harvested_keys,
    )
    from src.orchestration.tennis_results_harvester import harvest_results
    from src.orchestration.tennis_seen_markets import collect_seen_tennis_markets

    collect = collect_fn or collect_seen_tennis_markets
    harvest = harvest_fn or harvest_results

    seen = collect(log_paths, since_yyyymmdd=since_yyyymmdd) if collect_fn is None else collect(log_paths)
    if not seen:
        return 0
    results = harvest(
        seen, gamma_client, resolve_name=resolve_name, surface_map=surface_map,
        already_keys=harvested_keys(store_path), today_yyyymmdd=today_yyyymmdd,
    )
    added = append_results(results, store_path)
    if added > 0 and rebuild_fn is not None:
        rebuild_fn()
    elif added > 0:
        from scripts.build_tennis_ratings import main as rebuild_main
        rebuild_main()
    logger.info("Tenis taze hasat: %d yeni sonuç eklendi", added)
    return added
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/orchestration/test_harvest_hook.py -v`
Expected: PASS (2 test)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/factory_refresh_hooks.py tests/unit/orchestration/test_harvest_hook.py
git commit -m "feat(tennis): gunluk hasat+rebuild hook (orch, TDD)"
```

---

## Task 7: MODEL_DATA_STALE fail reason + bayatlık hesabı (Domain)

**Files:**
- Modify: `src/domain/analysis/enrich_outcome.py`
- Create: `src/domain/pricing/tennis/data_freshness.py`
- Test: `tests/unit/domain/pricing/tennis/test_data_freshness.py`, `tests/unit/domain/analysis/test_enrich_outcome.py` (mevcut listeye ekle)

- [ ] **Step 1: Write the failing test**

```python
"""data_freshness — reyting verisi yaşı → bayat mı saf kararı."""
from src.domain.pricing.tennis.data_freshness import is_ratings_stale


def test_fresh_when_newest_within_threshold():
    assert is_ratings_stale(newest_yyyymmdd="20260612", today_yyyymmdd="20260613", threshold_days=4) is False


def test_stale_when_newest_older_than_threshold():
    assert is_ratings_stale(newest_yyyymmdd="20260525", today_yyyymmdd="20260613", threshold_days=4) is True


def test_stale_when_no_data():
    assert is_ratings_stale(newest_yyyymmdd=None, today_yyyymmdd="20260613", threshold_days=4) is True


def test_boundary_exactly_threshold_is_fresh():
    # 4 gün fark, eşik 4 → bayat DEĞİL (<=)
    assert is_ratings_stale(newest_yyyymmdd="20260609", today_yyyymmdd="20260613", threshold_days=4) is False
```

Mevcut `test_enrich_outcome.py::test_enrich_fail_reason_values_match_spec` expected set'ine `"model_data_stale"` ekle.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/domain/pricing/tennis/test_data_freshness.py tests/unit/domain/analysis/test_enrich_outcome.py -v`
Expected: FAIL (ImportError + set mismatch)

- [ ] **Step 3: Implement**

`src/domain/pricing/tennis/data_freshness.py`:

```python
"""Reyting veri tazeliği — saf karar (bayat mı?).

newest/today YYYYMMDD string. I/O yok; çağıran tarihleri verir.
"""
from __future__ import annotations

from datetime import date


def _parse(yyyymmdd: str) -> date:
    return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))


def is_ratings_stale(
    newest_yyyymmdd: str | None, today_yyyymmdd: str, threshold_days: int
) -> bool:
    """En yeni maç bugünden threshold_days'ten ESKİYSE bayat. Veri yoksa bayat."""
    if not newest_yyyymmdd:
        return True
    age = (_parse(today_yyyymmdd) - _parse(newest_yyyymmdd)).days
    return age > threshold_days
```

`src/domain/analysis/enrich_outcome.py` enum'una ekle:

```python
    # 2026-06-13: bayat reyting verisi → model bahsi yapma (taze hasat hook ile çözülür).
    MODEL_DATA_STALE = "model_data_stale"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/domain/pricing/tennis/test_data_freshness.py tests/unit/domain/analysis/test_enrich_outcome.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/data_freshness.py src/domain/analysis/enrich_outcome.py tests/unit/domain/pricing/tennis/test_data_freshness.py tests/unit/domain/analysis/test_enrich_outcome.py
git commit -m "feat(tennis): MODEL_DATA_STALE + bayatlik saf karari (domain, TDD)"
```

---

## Task 8: Bayatlık koruması dispatch'te (Strategy)

**Files:**
- Modify: `src/strategy/enrichment/tennis_dispatch.py`
- Test: `tests/integration/test_tennis_dispatch.py` (yeni test ekle)

`enrich_with_tennis_dispatch`'e `model_data_stale: bool = False` parametresi ekle. Stale ise model fiyatlama yolunda (BM-first fail sonrası + alt marketler) `MODEL_DATA_STALE` döner; bahisçi yolu etkilenmez.

- [ ] **Step 1: Write the failing test** (test_tennis_dispatch.py'ye ekle)

```python
def test_stale_data_blocks_model_pricing_but_not_bookmaker():
    """Bayat veri → model fiyatlamaz; bahisçi verisi varsa o döner."""
    from src.domain.analysis.enrich_outcome import EnrichFailReason
    m = _market("Lyon: Alice vs Bob")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    # BM yok + stale → MODEL_DATA_STALE
    res = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Clay"), model_data_stale=True,
    )
    assert res.probability is None
    assert res.fail_reason == EnrichFailReason.MODEL_DATA_STALE
    # BM VAR + stale → bahisçi döner (stale bahisçiyi etkilemez)
    res2 = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Clay"), model_data_stale=True,
    )
    assert res2.probability is not None
    assert res2.probability.source == "bookmaker"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_tennis_dispatch.py::test_stale_data_blocks_model_pricing_but_not_bookmaker -v`
Expected: FAIL (model_data_stale parametresi yok)

- [ ] **Step 3: Implement**

`enrich_with_tennis_dispatch` imzasına ekle: `model_data_stale: bool = False`.

Model akışına geçişten ÖNCE (BM-first `if is_moneyline: bm_result...` bloğundan sonra, `if not ratings:` satırından ÖNCE) ekle:

```python
    # 2026-06-13 (bayatlık koruması): reyting verisi eskiyse model fiyatlamaz.
    # BM-first yukarıda zaten döndü; buraya gelen = model gerekiyor → stale ise skip.
    if model_data_stale:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.MODEL_DATA_STALE)
```

`tennis_dispatch_surface.py`'deki `make_surface_aware_dispatch` enrich imzasına da `model_data_stale: bool = False` ekle ve `_main_dispatch(...)` çağrısına `model_data_stale=model_data_stale` geçir (Task 8 kapsamında bu dosya da MODIFY).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_tennis_dispatch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/strategy/enrichment/tennis_dispatch.py src/strategy/enrichment/tennis_dispatch_surface.py tests/integration/test_tennis_dispatch.py
git commit -m "feat(tennis): bayatlik korumasi dispatch'te - stale->model skip (strategy, TDD)"
```

---

## Task 9: Config + factory wiring (Config + Orchestration)

**Files:**
- Modify: `src/config/tennis_settings.py`, `config.yaml`
- Modify: `src/orchestration/factory.py`, `src/orchestration/factory_refresh_hooks.py`
- Test: `tests/unit/config/test_settings.py` (repo config parse testi)

- [ ] **Step 1: Write the failing test** (test_settings.py'ye ekle)

```python
def test_tennis_freshness_config_defaults() -> None:
    from src.config.tennis_settings import TennisConfig
    c = TennisConfig()
    assert c.staleness_threshold_days == 4
    assert c.backfill_days == 14
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/config/test_settings.py::test_tennis_freshness_config_defaults -v`
Expected: FAIL (alanlar yok)

- [ ] **Step 3: Implement config + wiring**

`src/config/tennis_settings.py` TennisConfig'e ekle:

```python
    # 2026-06-13: taze sonuç hasadı + bayatlık koruması (spec 2026-06-13).
    staleness_threshold_days: int = 4   # reyting > bu gün eski → model bahsi yok
    backfill_days: int = 14             # ilk hasat penceresi
```

`config.yaml` tennis: bölümüne ekle:

```yaml
  # 2026-06-13: taze sonuç hasadı. Reyting verisi bu günden eskiyse model bahsi
  # yapılmaz (bayatlık koruması); ilk hasat son backfill_days gününü tarar.
  staleness_threshold_days: 4
  backfill_days: 14
```

`factory.py`: **Yerleşim — `tennis_active = ...` satırından (mevcut ~160) SONRA, `_tennis_dispatched` closure tanımlarından (mevcut ~186) ÖNCE.** factory'deki gamma değişkeni `gamma` (line 68). Rebuild HEM düz HEM yüzey reyting dosyasını değiştirir → ikisi de yeniden yüklenmeli.

```python
    # 2026-06-13: taze sonuç hasadı (startup blocking — Sackmann gibi) + bayatlık flag.
    from datetime import datetime, timedelta, timezone

    from src.domain.pricing.tennis.data_freshness import is_ratings_stale
    from src.infrastructure.data.tennis_results_store import load_results
    from src.orchestration.factory_refresh_hooks import maybe_harvest_and_rebuild
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name

    _now = datetime.now(timezone.utc)
    _today = _now.strftime("%Y%m%d")
    _since = (_now - timedelta(days=cfg.tennis.backfill_days)).strftime("%Y%m%d")
    if tennis_active:
        try:
            added = maybe_harvest_and_rebuild(
                gamma_client=gamma,
                resolve_name=lambda n: _resolve_player_name(n, tennis_ratings),
                surface_map=tennis_surface_map,
                store_path=Path("data/tennis_recent_results.jsonl"),
                log_paths=[
                    Path("logs/runtime/skipped_trades.jsonl"),
                    Path("logs/audit/trade_events.jsonl"),
                ],
                today_yyyymmdd=_today,
                since_yyyymmdd=_since,
            )
            if added > 0:
                # rebuild HEM düz HEM yüzey reytingini değiştirdi → ikisini de tazele
                tennis_ratings = load_tennis_ratings(Path("data/tennis_ratings.json"))
                if tennis_surface_ratings is not None:
                    tennis_surface_ratings = load_all_surfaces(
                        _surface_ratings_path, cfg.tennis.surface_phi_fallback,
                    )
        except Exception as exc:  # noqa: BLE001 — hasat best-effort, bot çökmez
            logger.warning("Tenis taze hasat başarısız: %s", exc)
    _recent = load_results(Path("data/tennis_recent_results.jsonl"))
    _newest = max((r.date for r in _recent), default=None)
    _model_stale = is_ratings_stale(_newest, _today, cfg.tennis.staleness_threshold_days)
    if _model_stale:
        logger.warning("Tenis reyting verisi BAYAT (en yeni=%s) — model bahsi kapalı", _newest)
```

NOT: `load_all_surfaces` ve `_surface_ratings_path` mevcut factory scope'unda (line 133-135) zaten var; import tekrarına gerek yok eğer fonksiyon başında import edildiyse — değilse `from src.infrastructure.data.tennis_surface_ratings_store import load_all_surfaces` ekle.

Dispatch closure'larına `model_data_stale=_model_stale` geçir (her iki `_tennis_dispatched` tanımına — surface-aware ve flat).

- [ ] **Step 4: Run full suite**

Run: `python -m pytest -q`
Expected: PASS (tümü; ~2080+ test)

- [ ] **Step 5: Commit**

```bash
git add src/config/tennis_settings.py config.yaml src/orchestration/factory.py tests/unit/config/test_settings.py
git commit -m "feat(tennis): config + factory wiring - startup hasat + bayatlik flag (TDD)"
```

---

## Bütünleşik doğrulama (tüm task'lar sonrası)

- [ ] `python -m pytest -q` → tümü yeşil
- [ ] `python -m scripts.build_tennis_ratings` → çalışır (taze sonuç dosyası boşken de)
- [ ] Manuel duman testi: küçük bir sahte `data/tennis_recent_results.jsonl` ile build → ilgili oyuncunun reytingi değişir
- [ ] DECISIONS.md'ye SPEC kaydı ekle (taze hasat + bayatlık koruması)
- [ ] Kullanıcıya reload/reboot sor (CLAUDE.md kuralı — izinsiz yapma)
