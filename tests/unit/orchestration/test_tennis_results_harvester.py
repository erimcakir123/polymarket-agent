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
    assert out[0].condition_id == "0xa"


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


def test_skips_already_harvested_condition_id_without_fetching():
    fetched = {"count": 0}
    class _CountingGamma:
        def fetch_closed_market_by_condition(self, _cid):
            fetched["count"] += 1
            return _resolved('["1","0"]')
    seen = [{"condition_id": "0xa", "question": "Lyon: Galan vs Trungelliti", "ts": "2026-06-11T18:00:00+00:00"}]
    out = harvest_results(
        seen, _CountingGamma(), resolve_name=lambda n: n.split()[-1], surface_map={"lyon": "Clay"},
        already_keys={"0xa"}, today_yyyymmdd="20260613",
    )
    assert out == []
    assert fetched["count"] == 0  # zaten hasat → gamma'ya hic gidilmedi
