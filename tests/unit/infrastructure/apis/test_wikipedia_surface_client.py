from src.infrastructure.apis.wikipedia_surface_client import WikipediaSurfaceClient


class _Resp:
    def __init__(self, status, payload): self.status_code = status; self._p = payload
    def json(self): return self._p


def test_resolve_surface_parses_grass():
    # query "Birmingham" → hit title "2026 Birmingham Open" shares token "birmingham" ✓
    search = {"query": {"search": [{"title": "2026 Birmingham Open"}]}}
    page = {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {
        "*": "{{Infobox tennis tournament\n| surface = [[Grass court|Grass]] / outdoors\n}}"
    }}}]}}}}

    def fake_get(url, params=None, headers=None, timeout=None):
        return _Resp(200, search if params.get("list") == "search" else page)

    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Birmingham") == "Grass"


def test_resolve_surface_no_article_returns_none():
    assert WikipediaSurfaceClient(
        http_get=lambda *a, **k: _Resp(200, {"query": {"search": []}})
    ).resolve_surface("XYZ") is None


def test_resolve_surface_no_surface_field_returns_none():
    # query "Birmingham" → hit "Birmingham Open" shares token "birmingham" ✓ → but no surface field
    def fake_get(url, params=None, headers=None, timeout=None):
        if params.get("list") == "search":
            return _Resp(200, {"query": {"search": [{"title": "Birmingham Open"}]}})
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": "no infobox"}}}]}}}})

    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Birmingham") is None


def test_resolve_surface_http_error_returns_none():
    def boom(*a, **k): raise Exception("timeout")
    assert WikipediaSurfaceClient(http_get=boom).resolve_surface("X") is None


def test_resolve_surface_sends_user_agent():
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen["headers"] = headers
        if params.get("list") == "search":
            return _Resp(200, {"query": {"search": [{"title": "HSBC Championships"}]}})
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": "| surface = [[Grass court|Grass]]"}}}]}}}})

    WikipediaSurfaceClient(http_get=fake_get).resolve_surface("HSBC Championships")
    assert "User-Agent" in (seen["headers"] or {})


def test_search_skips_wrong_city_hit():
    # "Lyon" arama: 'Open Sud de France' (paylaşılan kelime yok) atlanır, 'ATP Lyon Open' seçilir
    def fake_get(url, params=None, headers=None, timeout=None):
        p = params or {}
        if p.get("list") == "search":
            return _Resp(200, {"query": {"search": [
                {"title": "Open Sud de France"}, {"title": "ATP Lyon Open"}]}})
        title = p.get("titles")
        wt = "| surface = [[Clay court|Clay]]" if title == "ATP Lyon Open" else "no surface"
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": wt}}}]}}}})
    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Lyon") == "Clay"


def test_resolve_surface_falls_through_to_second_candidate():
    # First hit shares token but has no surface; second hit has surface → returns second
    pages = {
        "Birmingham Classic (tennis)": "no surface here",
        "2026 Birmingham Open": "| surface = [[Grass court|Grass]]",
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        p = params or {}
        if p.get("list") == "search":
            return _Resp(200, {"query": {"search": [
                {"title": "Birmingham Classic (tennis)"},
                {"title": "2026 Birmingham Open"},
            ]}})
        title = p.get("titles", "")
        wt = pages.get(title, "no surface")
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": wt}}}]}}}})

    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Birmingham") == "Grass"


def test_search_all_filtered_returns_none():
    # All hits share no token with query → _search_titles returns [] → resolve_surface returns None
    def fake_get(url, params=None, headers=None, timeout=None):
        p = params or {}
        if p.get("list") == "search":
            return _Resp(200, {"query": {"search": [
                {"title": "Open Sud de France"},
                {"title": "List of tennis tournaments"},
            ]}})
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": "| surface = Clay"}}}]}}}})

    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Lyon") is None


def test_resolve_surface_all_candidates_agree():
    def fake_get(url, params=None, headers=None, timeout=None):
        if (params or {}).get("list") == "search":
            return _Resp(200, {"query": {"search": [{"title": "2026 Birmingham Open"}, {"title": "Birmingham Classic"}]}})
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": "| surface = [[Grass court|Grass]]"}}}]}}}})
    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Birmingham") == "Grass"


def test_resolve_surface_candidates_disagree_returns_none():
    pages = {"Stuttgart Open": "| surface = [[Grass court|Grass]]",
             "Porsche Tennis Grand Prix Stuttgart": "| surface = [[Clay court|Clay]]"}
    def fake_get(url, params=None, headers=None, timeout=None):
        if (params or {}).get("list") == "search":
            return _Resp(200, {"query": {"search": [{"title": "Stuttgart Open"}, {"title": "Porsche Tennis Grand Prix Stuttgart"}]}})
        title = (params or {}).get("titles")
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": pages.get(title, "no surface")}}}]}}}})
    # iki Stuttgart turnuvası farklı zemin → belirsiz → None (skip+alert)
    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Stuttgart") is None
