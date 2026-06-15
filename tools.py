"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

# Very small stopword set so generic words in a query don't inflate scores.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to",
    "my", "i", "im", "under", "looking", "want", "wear", "wears", "some",
    "that", "this", "it", "is", "are", "something",
}

# ── Groq client ───────────────────────────────────────────────────────────────


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords and 1-char tokens."""
    tokens = [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


def _score_listing(item: dict, query_tokens: list[str]) -> float:
    """
    Score a listing by keyword overlap with the query.
    style_tags are weighted highest, then title/category, then colors/description.
    """
    style_tags = " ".join(item.get("style_tags", [])).lower()
    title = item.get("title", "").lower()
    category = item.get("category", "").lower()
    colors = " ".join(item.get("colors", [])).lower()
    desc = item.get("description", "").lower()

    score = 0.0
    for tok in query_tokens:
        if tok in style_tags:
            score += 3.0
        if tok in title:
            score += 2.0
        if tok in category:
            score += 2.0
        if tok in colors:
            score += 1.5
        if tok in desc:
            score += 1.0
    return score

# ── Tool 1: search_listings ───────────────────────────────────────────────────


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    # Replace this with your implementation
    listings = load_listings()
    query_tokens = _tokenize(description or "")

    results = []
    for item in listings:
        # Price filter (inclusive).
        if max_price is not None and item["price"] > max_price:
            continue
        # Size filter — case-insensitive substring, e.g. "M" matches "S/M".
        if size is not None and size.lower() not in item["size"].lower():
            continue
        # Relevance score; drop anything with no keyword overlap.
        score = _score_listing(item, query_tokens)
        if score > 0:
            scored = dict(item)
            scored["relevance_score"] = score
            results.append(scored)

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────
def _format_item(item: dict) -> str:
    return (
        f"{item.get('title', 'item')} "
        f"(category: {item.get('category', '?')}; "
        f"colors: {', '.join(item.get('colors', [])) or 'n/a'}; "
        f"style: {', '.join(item.get('style_tags', [])) or 'n/a'})"
    )


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Replace this with your implementation
    items = (wardrobe or {}).get("items", [])

    if not items:
        # Empty-wardrobe path: general styling ideas, no specific pieces.
        prompt = (
            f"A shopper is considering this secondhand item:\n"
            f"- {_format_item(new_item)}\n\n"
            "They have NOT shared their wardrobe yet. Suggest general ways to "
            "style this piece: what kinds of items (categories, colors, styles) "
            "pair well with it, and what overall vibe it suits. Keep it under "
            "100 words and make clear these are general ideas since you don't "
            "know their closet yet."
        )
    else:
        # Normal path: pair the new item with specific named wardrobe pieces.
        wardrobe_lines = "\n".join(
            f"- {it.get('name', 'item')} "
            f"(category: {it.get('category', '?')}; "
            f"style: {', '.join(it.get('style_tags', [])) or 'n/a'})"
            for it in items
        )
        prompt = (
            f"New secondhand item the shopper might buy:\n"
            f"- {_format_item(new_item)}\n\n"
            f"The shopper's existing wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that pair the NEW item with specific, "
            "named pieces from their wardrobe above. Name the exact wardrobe "
            "pieces you use and add one practical styling tip per outfit "
            "(tuck, cuff, layer, etc.). Do NOT invent items they don't own. "
            "Keep it under 130 words."
        )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are FitFindr, a thrift-savvy "
                 "personal stylist. Be specific, practical, and concise."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as e:
        # Never crash the agent on an API failure — return a usable fallback.
        return (
            f"Couldn't reach the styling model ({e}). As a fallback: pair the "
            f"{new_item.get('title', 'item')} with simple basics in complementary "
            f"colors and let it be the focal piece."
        )

    # LLM returned empty content — deterministic fallback.
    return (
        f"Style the {new_item.get('title', 'item')} as the focal piece with "
        "neutral basics and shoes that match its overall vibe."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    if not outfit or not outfit.strip():
        return (
            "No outfit suggestion was provided, so there's nothing to caption "
            "yet — run suggest_outfit first, then create a fit card."
        )

    title = new_item.get("title", "this piece")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a resale app")

    prompt = (
        f"Item: {title}\n"
        f"Price: ${price}\n"
        f"Platform: {platform}\n"
        f"Outfit: {outfit}\n\n"
        "Write a 2-4 sentence caption for an Instagram/TikTok OOTD post about "
        "thrifting this item and styling it as described above. It should feel "
        "casual and authentic (like a real outfit post, NOT a product "
        "description). Mention the item, its price, and the platform naturally, "
        "once each. Capture the specific vibe of the outfit. At most one or two "
        "hashtags or emoji. Vary the wording."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You write short, authentic OOTD "
                 "social captions with personality. Never sound like an ad."},
                {"role": "user", "content": prompt},
            ],
            temperature=1.1,  # higher temp so captions vary across runs
            max_tokens=160,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception:
        pass  # fall through to deterministic fallback below

    # Fallback caption so the agent always returns something shareable.
    return f"thrifted this {title} off {platform} for ${price} and styled it up — obsessed ✨"
