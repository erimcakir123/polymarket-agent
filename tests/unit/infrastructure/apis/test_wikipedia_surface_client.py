from src.infrastructure.apis.wikipedia_surface_client import WikipediaSurfaceClient


class _Resp:
    def __init__(self, status, payload): self.status_code = status; self._p = payload
    def json(self): return self._p


def test_resolve_surface_parses_grass():
    search = {"query": {"search": [{"title": "Queen's Club Championships"}]}}
    page = {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {
        "*": "{{Infobox tennis tournament\n| surface = [[Grass court|Grass]] / outdoors\n}}"
    }}}]}}}}

    def fake_get(url, params=None, headers=None, timeout=None):
        return _Resp(200, search if params.get("list") == "search" else page)

    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("HSBC Championships") == "Grass"


def test_resolve_surface_no_article_returns_none():
    assert WikipediaSurfaceClient(
        http_get=lambda *a, **k: _Resp(200, {"query": {"search": []}})
    ).resolve_surface("XYZ") is None


def test_resolve_surface_no_surface_field_returns_none():
    def fake_get(url, params=None, headers=None, timeout=None):
        if params.get("list") == "search":
            return _Resp(200, {"query": {"search": [{"title": "Foo"}]}})
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": "no infobox"}}}]}}}})

    assert WikipediaSurfaceClient(http_get=fake_get).resolve_surface("Foo") is None


def test_resolve_surface_http_error_returns_none():
    def boom(*a, **k): raise Exception("timeout")
    assert WikipediaSurfaceClient(http_get=boom).resolve_surface("X") is None


def test_resolve_surface_sends_user_agent():
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen["headers"] = headers
        if params.get("list") == "search":
            return _Resp(200, {"query": {"search": [{"title": "Queen's Club Championships"}]}})
        return _Resp(200, {"query": {"pages": {"1": {"revisions": [{"slots": {"main": {"*": "| surface = [[Grass court|Grass]]"}}}]}}}})

    WikipediaSurfaceClient(http_get=fake_get).resolve_surface("HSBC Championships")
    assert "User-Agent" in (seen["headers"] or {})
