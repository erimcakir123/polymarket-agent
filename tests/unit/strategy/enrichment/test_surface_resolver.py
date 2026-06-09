"""SurfaceResolver birim testleri — PLAN-Z30 G4."""
from src.models.market import MarketData
from src.strategy.enrichment.surface_resolver import SurfaceResolver


def _mkt(q, event_id="e1"):
    return MarketData(condition_id="c", question=q, slug="s", yes_token_id="y", no_token_id="n",
                      yes_price=0.5, no_price=0.5, liquidity=1, volume_24h=1,
                      end_date_iso="2026-06-10", event_id=event_id)


class _Wiki:
    def __init__(self, ret): self.ret = ret; self.calls = 0
    def resolve_surface(self, name): self.calls += 1; return self.ret


def test_resolve_from_map_no_wiki():
    w = _Wiki("Hard")
    r = SurfaceResolver({"ilkley": "Grass"}, wiki=w, now_iso="2026-06-09T00:00:00")
    assert r.resolve(_mkt("Ilkley: A vs B")) == "Grass"
    assert w.calls == 0


def test_via_wiki_calls_save_fn():
    saved = []
    r = SurfaceResolver({}, wiki=_Wiki("Grass"), overrides={}, save_fn=lambda ov: saved.append(dict(ov)), now_iso="2026-06-09T00:00:00")
    r.resolve(_mkt("HSBC Championships: A vs B"))
    assert saved and saved[-1]["hsbc championships"]["surface"] == "Grass"


def test_resolve_wiki_fallback_and_cache():
    w = _Wiki("Grass")
    r = SurfaceResolver({}, wiki=w, overrides={}, now_iso="2026-06-09T00:00:00")
    assert r.resolve(_mkt("HSBC Championships: A vs B")) == "Grass"
    assert r.resolve(_mkt("HSBC Championships: C vs D")) == "Grass"
    assert w.calls == 1  # ikinci sefer cache


def test_resolve_unknown_recorded():
    r = SurfaceResolver({}, wiki=_Wiki(None), overrides={}, now_iso="2026-06-09T00:00:00")
    assert r.resolve(_mkt("Obscure Cup: A vs B")) is None
    assert "obscure cup" in r.unresolved


def test_resolve_set_handicap_uses_event():
    r = SurfaceResolver({"stuttgart": "Grass"}, wiki=_Wiki(None), now_iso="2026-06-09T00:00:00")
    r.set_event_tournaments({"e9": "Stuttgart"})
    assert r.resolve(_mkt("Set Handicap: Zverev (-1.5) vs Cobolli", event_id="e9")) == "Grass"


def test_resolve_unknown_rechecked_after_ttl():
    w = _Wiki("Clay")
    overrides = {"late cup": {"surface": "UNKNOWN", "checked_at": "2026-06-01T00:00:00"}}
    r = SurfaceResolver({}, wiki=w, overrides=overrides, ttl_days=3, now_iso="2026-06-09T00:00:00")
    assert r.resolve(_mkt("Late Cup: A vs B")) == "Clay"
    assert w.calls == 1


def test_resolve_unknown_not_rechecked_within_ttl():
    w = _Wiki("Clay")
    overrides = {"late cup": {"surface": "UNKNOWN", "checked_at": "2026-06-08T00:00:00"}}
    r = SurfaceResolver({}, wiki=w, overrides=overrides, ttl_days=3, now_iso="2026-06-09T00:00:00")
    assert r.resolve(_mkt("Late Cup: A vs B")) is None
    assert w.calls == 0  # TTL dolmadı → Wiki YOK


def test_set_handicap_no_event_link_no_garbage_wiki():
    w = _Wiki(None)
    r = SurfaceResolver({}, wiki=w, overrides={}, now_iso="2026-06-09T00:00:00")
    m = _mkt("Set Handicap: Zverev (-1.5) vs Cobolli", event_id="eX")  # eX not in event map
    assert r.resolve(m) is None
    assert w.calls == 0                      # NO garbage wiki query
    assert "set handicap" not in r.unresolved  # no meaningless alert
