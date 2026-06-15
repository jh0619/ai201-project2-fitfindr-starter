# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

**What it returns:**

<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**

<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `new_item` (dict): ...
- `wardrobe` (dict): ...

**What it returns:**

<!-- Describe the return value -->

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `outfit` (...): ...

**What it returns:**

<!-- Describe the return value -->

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**

<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool            | Failure mode                          | Agent response |
| --------------- | ------------------------------------- | -------------- |
| search_listings | No results match the query            |                |
| suggest_outfit  | Wardrobe is empty                     |                |
| create_fit_card | Outfit input is missing or incomplete |                |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

FitFindr is triggered by a single natural-language user query that describes an item they want and (optionally) what they already own or wear. The agent calls search_listings first; if it returns at least one match, the top result and the user's wardrobe are passed to suggest_outfit, and that outfit plus the new item are passed to create_fit_card to produce a shareable caption. If search_listings returns no matches, the agent tells the user what didn't match (e.g., size or price too restrictive) and stops — it does not call suggest_outfit or create_fit_card with empty or missing input.

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**

<!-- What does the agent do first? Which tool is called? With what input? -->

The agent calls search_listings(description="vintage graphic tee", size=None, max_price=30.0). Against the dataset this matches three listings whose style_tags include both "vintage" and "graphic tee": lst_002 ("Y2K Baby Tee — Butterfly Print", $18), lst_006 ("Graphic Tee — 2003 Tour Bootleg Style", $24, good, Depop), and lst_033 ("Vintage Band Tee — Faded Grey", $19, fair, Depop). The agent picks lst_006 as the top result — it's an exact title/tag match and in "good" condition.

**Step 2:**

<!-- What happens next? What was returned from step 1? What tool is called now? -->

The agent calls suggest_outfit(new_item=<lst_006>, wardrobe=<example_wardrobe>). Because the user said they "mostly wear baggy jeans and chunky sneakers," the tool matches this against w_001 ("Baggy straight-leg jeans, dark wash") and w_007 ("Chunky white sneakers") in the example wardrobe, and optionally layers in w_006 ("Vintage black denim jacket") for a complete look. It returns an outfit object combining the new tee with these wardrobe items plus a one-line styling note (e.g., "tuck the front slightly and let the jacket hang open for an easy 90s grunge layer").

**Step 3:**

<!-- Continue until the full interaction is complete -->

The agent calls create_fit_card(outfit=<result from step 2>, new_item=<lst_006>), which generates a short, Instagram-caption-style description referencing the price, platform, and styling — different each time based on the specific item/outfit passed in.

**Final output to user:**

<!-- What does the user actually see at the end? -->

The user sees the matched listing (title, price, condition, platform), the suggested outfit pairing with their existing wardrobe items, and the generated fit card caption — e.g., something like: "thrifted this bootleg-style graphic tee off depop for $24 and it's basically made for my baggy jeans + white sneaks 🖤 effortless 90s vibes."
