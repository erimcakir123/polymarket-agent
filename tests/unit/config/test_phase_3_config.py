"""Phase 3: config.yaml final state — tennis active, exclude_combos, paper default."""
import yaml


def _cfg() -> dict:
    return yaml.safe_load(open("config.yaml", encoding="utf-8")) or {}


def test_mode_is_paper() -> None:
    assert _cfg().get("mode") == "paper"


def test_whitelist_contains_basket_and_tennis() -> None:
    tags = set(_cfg()["scanner"]["allowed_sport_tags"])
    # SPEC-EUROBASKET-001 (2026-06-02): liga_acb whitelist'e eklendi
    expected = {"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl",
                "tennis", "atp", "wta", "liga_acb"}
    assert tags == expected


def test_exclude_combos_contains_tennis_set_totals() -> None:
    combos = _cfg()["edge"]["exclude_combos"]
    tour_market = {(c["tour"], c["market_type"]) for c in combos}
    assert ("atp", "tennis_set_totals") in tour_market
    assert ("wta", "tennis_set_totals") in tour_market


def test_exclude_combos_contains_tennis_first_set_winner() -> None:
    combos = _cfg()["edge"]["exclude_combos"]
    tour_market = {(c["tour"], c["market_type"]) for c in combos}
    assert ("atp", "tennis_first_set_winner") in tour_market
    assert ("wta", "tennis_first_set_winner") in tour_market


def test_edge_config_parses_exclude_combos() -> None:
    from src.config.settings import load_config
    cfg = load_config()
    assert len(cfg.edge.exclude_combos) == 8
