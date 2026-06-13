"""harvest hook — toplama->hasat->depo->rebuild orkestrasyon testi."""
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
