# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:

```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:

```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Tools

The agent orchestrates three tools, all defined in `tools.py`.

### `search_listings(description, size, max_price) -> list[dict]`

**Purpose:** Find listings matching a free-text style query, ranked by relevance.
**Inputs:**

- `description` (`str`) — free-text query, e.g. `"vintage graphic tee"`. Tokenized and matched against each listing's `title`, `description`, `style_tags`, `category`, and `colors`.
- `size` (`str | None`) — optional size filter; case-insensitive substring (`"M"` matches `"S/M"`). `None` skips the filter.
- `max_price` (`float | None`) — optional inclusive price ceiling. `None` skips the filter.

**Output:** a `list[dict]` of full listing dicts, each with an added `relevance_score` (`float`), sorted highest-score first. Returns `[]` when nothing matches (never raises).

### `suggest_outfit(new_item, wardrobe) -> str`

**Purpose:** Pair the found item with the user's wardrobe and describe how to wear it.
**Inputs:**

- `new_item` (`dict`) — a single listing dict (the top search result).
- `wardrobe` (`dict`) — `{"items": [...]}` in the wardrobe schema format.

**Output:** a non-empty `str` with 1–2 outfit suggestions. With a populated wardrobe it names specific pieces the user owns plus a styling tip; with an empty wardrobe it returns general styling advice instead. Uses Groq `llama-3.3-70b-versatile`.

### `create_fit_card(outfit, new_item) -> str`

**Purpose:** Turn the outfit into a short, casual OOTD caption worth sharing.
**Inputs:**

- `outfit` (`str`) — the suggestion string returned by `suggest_outfit`.
- `new_item` (`dict`) — the selected listing, so the caption can reference price/platform.

**Output:** a `str` caption (1–2 sentences). Runs at `temperature=1.1` so captions vary across runs for the same item.

---

## Planning Loop

The loop lives in `run_agent(query, wardrobe)` in `agent.py`. It is **not** a fixed three-call sequence — what it calls next depends on what the previous tool returned.

1. **Parse the query.** `_parse_query()` uses regex to pull a `max_price` (e.g. "under $30"), an optional `size` ("size M", or codes like "XXS"), and a `description` (the query with the price/size phrases stripped out so a price like "$30" can't accidentally match a size like "W30"). Result is stored in `session["parsed"]`.

2. **Search.** Call `search_listings(description, size, max_price)`; store the list in `session["search_results"]`.

3. **The key decision — branch on the result:**
   - **If the list is empty:** the agent sets `session["error"]` to a message that names which filters were too tight and what to loosen, then **returns immediately**. It does **not** call `suggest_outfit` or `create_fit_card` with empty input.
   - **If there are matches:** it selects the top (most relevant) listing into `session["selected_item"]` and proceeds.

4. **Suggest an outfit** using the selected item and wardrobe. If the wardrobe is empty, it additionally sets `session["note"]` to flag that the styling is generic.

5. **Create the fit card** from the outfit suggestion and selected item.

6. **Return the session.**

So the agent makes two real decisions: whether to continue past the search at all, and whether to flag the outfit advice as generic. The downstream tools only run when the upstream step produced something usable.

---

## State Management

A single session dict (created by \_new_session()) is the source of truth for one interaction and is passed by reference through the loop. Each step reads what it needs and writes its result back, so the user never re-enters anything.

| Key                                   | Set by   | Read by                         |
| ------------------------------------- | -------- | ------------------------------- |
| query                                 | init     | parser                          |
| parsed (description, size, max_price) | step 1   | search_listings                 |
| search_results (list[dict])           | step 2   | branch / display                |
| selected_item (dict)                  | step 3   | suggest_outfit, create_fit_card |
| wardrobe (dict)                       | init     | suggest_outfit                  |
| outfit_suggestion (str)               | step 4   | create_fit_card, UI             |
| note (str or None)                    | step 4   | UI                              |
| fit_card (str)                        | step 5   | UI                              |
| error (str or None)                   | any step | controls early return + UI      |

selected_item is the pivot: set once from the search results, then reused by both downstream tools — that's the visible "state passing" (search → suggest → card), with no re-prompting in between.

---

## Error Handling

Each tool owns its failure mode and degrades to something useful instead of crashing.

| Tool            | Failure mode                | Agent response                                                                                                                                                                                                               |
| --------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| search_listings | No results match the query  | Returns []. The planning loop sets session["error"] naming the offending filters and suggesting a loosening, then stops before the LLM tools.                                                                                |
| suggest_outfit  | Wardrobe is empty           | Returns general styling advice (based on the item's own style tags) rather than ""; the loop sets a note so the UI tells the user it can personalize once a wardrobe is added. (LLM errors also fall back to a safe string.) |
| create_fit_card | Missing/empty outfit string | Returns a descriptive message string telling the user to run suggest_outfit first; never raises. LLM errors fall back to a templated caption.                                                                                |

**Concrete example — empty wardrobe.** Triggering the empty-wardrobe case directly:

```bash
python -c "
from tools import search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe
item = search_listings('vintage graphic tee', None, 50)[0]
print(suggest_outfit(item, get_empty_wardrobe()))
"
```

Returns a non-empty paragraph of general advice instead of crashing:

```
This graphic tee suits a grunge or streetwear vibe. It may pair well with
distressed denim, black jackets, and sneakers. Neutral colors like gray,
white, or beige could complement the black tee...
```

**Concrete example — empty fit-card input.** Passing an empty `outfit` string:

```bash
python -c "
from tools import search_listings, create_fit_card
item = search_listings('vintage graphic tee', None, 50)[0]
print(create_fit_card('', item))
"
```

Returns a descriptive message string (not an exception):

```
No outfit suggestion was provided, so there's nothing to caption yet —
run suggest_outfit first, then create a fit card.
```

---

## Testing

tests/test_tools.py covers each tool plus every failure mode. The two LLM-backed tools are tested with a fake Groq client (via monkeypatch), so the suite is fast, deterministic, and needs no network or API key. conftest.py in the repo root puts the project on the import path so pytest tests/ works from anywhere.

```bash
pytest tests/        # all tests pass
```

---

## Spec Reflection

A few places where the implementation diverged from the original `planning.md`:

- **`suggest_outfit` return type.** Planning.md first specified a structured `dict` (`pieces`, `styling_note`, `complete`). The starter stub's signature was `-> str`, so the implementation returns a plain string and I updated planning.md to match. In hindsight a string is the simpler contract here, since `create_fit_card` only needs prose to summarize.
- **Session key names.** Planning.md used `filters` / `all_results` / `outfit`; the `agent.py` stub used `parsed` / `search_results` / `outfit_suggestion`. I aligned to the stub's names so the code matches the provided scaffolding.
- **Query parsing is regex-based.** It reliably handles standard phrasings ("size M", "under $30") but a very colloquial query ("something cheap-ish") may not yield a price. Known limitation; an LLM-based parser would be more robust and is a reasonable next step.

---

## AI Usage

I used Claude as a coding assistant, one component at a time, always giving it a specific spec section and verifying the output before trusting it.

**Instance 1 — `search_listings`.** I gave Claude the Tool 1 block from `planning.md` (parameter names/types, the `relevance_score` return shape, and the "return `[]` on no match" failure mode) and asked it to implement the function using `load_listings()` from the data loader. It produced a version that filters by price and size, scores each listing by weighted keyword overlap (style_tags highest), drops zero-score items, and sorts by score. **What I changed:** I verified it filtered by all three params, treated `size`/`max_price` as optional when `None`, and returned `[]` rather than raising — then tested three queries ("vintage graphic tee", an over-tight query, a price-only query) and confirmed ranking put the exact title match first.

**Instance 2 — the planning loop (`run_agent`).** I gave Claude the Planning Loop, State Management, and Architecture (Mermaid) sections together and asked it to wire the three already-tested tools through the session dict. It produced the branch-on-search-result logic. **What I overrode:** Claude initially followed planning.md's session key names, but I had it switch to the stub's actual keys (`search_results`, `outfit_suggestion`, etc.). I then verified the early-return-on-empty-results behavior with a "tripwire" — replacing `suggest_outfit` with a function that flags if it's called — and confirmed `selected_item` flows unchanged into both downstream tools.
