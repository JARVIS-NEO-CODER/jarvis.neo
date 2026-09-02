from core.web_search import WebSearchProvider, SearchResult


def test_search_result_serialization():
    result = SearchResult("Titre", "https://example.com", "Résumé")
    assert result.as_dict() == {"title": "Titre", "url": "https://example.com", "snippet": "Résumé"}


def test_search_parser_accepts_real_result_markup(monkeypatch):
    html = '''<div class="result"><a class="result__a" href="https://example.com">Example</a><div class="result__snippet">Un résultat de test</div></div>'''

    class Response:
        def __init__(self):
            self.headers = self
        def get_content_charset(self):
            return "utf-8"
        def read(self, _limit):
            return html.encode()
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("core.web_search.urlopen", lambda *args, **kwargs: Response())
    results = WebSearchProvider(timeout=2).search("test", limit=1)
    assert results[0].title == "Example"
    assert results[0].url == "https://example.com"
    assert "test" in results[0].snippet
