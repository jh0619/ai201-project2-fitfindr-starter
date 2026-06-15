"""
tests/test_tools.py

Run from the repo root with:  pytest tests/

The two LLM-backed tools (suggest_outfit, create_fit_card) are tested with a
fake Groq client via monkeypatch, so these tests are fast, deterministic, and
need no network or API key. search_listings runs against the real dataset.
"""

import os
import sys
import tools
from tools import search_listings, suggest_outfit, create_fit_card

# Make the repo root importable regardless of where pytest is launched from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


SAMPLE_ITEM = {
    "id": "lst_006",
    "title": "Graphic Tee — 2003 Tour Bootleg Style",
    "category": "tops",
    "style_tags": ["graphic tee", "vintage", "grunge"],
    "colors": ["black"],
    "price": 24.00,
    "platform": "depop",
}


# -- Fake Groq client so LLM tools don't hit the network ----------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content

    def create(self, **kwargs):
        return _FakeCompletion(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content):
        self.chat = _FakeChat(content)


def _patch_llm(monkeypatch, content):
    monkeypatch.setattr(tools, "_get_groq_client", lambda: _FakeClient(content))


# -- search_listings ----------------------------------------------------------

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Failure mode: no listings match -> empty list, no exception.
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("vintage", size="M", max_price=None)
    # Every returned item's size string should contain "m" (case-insensitive).
    assert all("m" in item["size"].lower() for item in results)


def test_search_results_are_ranked():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    scores = [item["relevance_score"] for item in results]
    assert scores == sorted(scores, reverse=True)


# -- suggest_outfit -----------------------------------------------------------

def test_suggest_outfit_with_wardrobe(monkeypatch):
    _patch_llm(monkeypatch, "Pair it with your baggy jeans and white sneakers.")
    wardrobe = {"items": [
        {"id": "w_001", "name": "Baggy jeans", "category": "bottoms",
         "style_tags": ["denim", "baggy"]},
        {"id": "w_007", "name": "Chunky white sneakers", "category": "shoes",
         "style_tags": ["chunky"]},
    ]}
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    # Failure mode: empty wardrobe -> still returns a non-empty string, no crash.
    _patch_llm(monkeypatch, "Generally, pair this with denim and clean sneakers.")
    result = suggest_outfit(SAMPLE_ITEM, {"items": []})
    assert isinstance(result, str)
    assert result.strip() != ""


def test_suggest_outfit_api_error_fallback(monkeypatch):
    # If the LLM call raises, the tool must return a usable string, not crash.
    def _boom():
        raise RuntimeError("network down")
    monkeypatch.setattr(tools, "_get_groq_client", _boom)
    result = suggest_outfit(SAMPLE_ITEM, {"items": []})
    assert isinstance(result, str)
    assert result.strip() != ""


# -- create_fit_card ----------------------------------------------------------

def test_fit_card_normal(monkeypatch):
    _patch_llm(monkeypatch, "thrifted this tee off depop for $24, obsessed.")
    result = create_fit_card("Pair with baggy jeans + sneakers", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_fit_card_empty_outfit():
    # Failure mode: missing/empty outfit -> descriptive message, no exception.
    result = create_fit_card("", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""
    assert "suggest_outfit" in result  # points the user at the fix


def test_fit_card_whitespace_outfit():
    result = create_fit_card("   ", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""
