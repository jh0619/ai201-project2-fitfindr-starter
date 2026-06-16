"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re
from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }

# -- query parsing ------------------------------------------------------------


def _parse_query(query: str) -> dict:
    """
    Extract a free-text description, an optional size, and an optional max_price
    from a natural-language query using regex.

    The price/size phrases are stripped out of the description so that, e.g.,
    the "30" in "under $30" can't accidentally match a listing size like "W30".
    Remaining filler words ("looking for", "a", "under") are handled by the
    tokenizer inside search_listings, so they don't need removing here.
    """
    text = query.strip()
    lowered = text.lower()
    spans = []

    # max_price: "under $30", "below 25", "less than 20", "max 40", or a bare "$30"
    max_price = None
    m = re.search(r"(?:under|below|less than|max|cheaper than|<)\s*\$?\s*(\d+(?:\.\d+)?)", lowered)
    if not m:
        m = re.search(r"\$\s*(\d+(?:\.\d+)?)", lowered)
    if m:
        max_price = float(m.group(1))
        spans.append(m.span())

    # size: prefer an explicit "size X"; otherwise catch unambiguous codes XS/XXS/XL/XXL
    size = None
    m = re.search(r"\bsize\s+([a-z0-9/]+)", lowered)
    if m:
        size = m.group(1).upper()
        spans.append(m.span())
    else:
        m = re.search(r"\b(xxs|xs|xl|xxl)\b", lowered)
        if m:
            size = m.group(1).upper()
            spans.append(m.span())

    # description: original text with the matched price/size spans removed
    description = text
    for start, end in sorted(spans, reverse=True):
        description = description[:start] + description[end:]
    description = re.sub(r"\s+", " ", description).strip(" ,.")

    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: fresh session.
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into search filters.
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # Step 3: search.
    results = search_listings(
        parsed["description"], parsed["size"], parsed["max_price"]
    )
    session["search_results"] = results

    # --- branch: no results -> set error and stop (do NOT call suggest_outfit) ---
    if not results:
        constraints = []
        if parsed["size"]:
            constraints.append(f"size {parsed['size']}")
        if parsed["max_price"] is not None:
            constraints.append(f"under ${parsed['max_price']:.0f}")
        scope = (" in " + " and ".join(constraints)) if constraints else ""
        desc = parsed["description"] or query
        session["error"] = (
            f'No listings matched "{desc}"{scope}. '
            "Try loosening the filters — e.g. drop the size or raise the budget."
        )
        return session

    # Step 4: select the top (most relevant) result.
    session["selected_item"] = results[0]

    # Step 5: suggest an outfit using the selected item + wardrobe.
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], wardrobe
    )
    if not (wardrobe or {}).get("items"):
        session["note"] = (
            "Gave generic styling — add wardrobe items for a personalized look."
        )

    # Step 6: turn the outfit into a shareable fit card.
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: done.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")
