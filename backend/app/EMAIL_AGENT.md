# Email Agent — LangGraph Overview

## What is LangGraph?

LangGraph is a framework for building stateful, multi-step LLM workflows modeled as directed graphs. Think of it as a state machine where each **node** is a Python function and **edges** describe the allowed transitions between them.

## Core Concepts

| Concept | Description |
|---|---|
| `StateGraph` | The graph object. You declare nodes and edges on it, then call `.compile()` to get a runnable. |
| **State** (`TypedDict`) | A shared dictionary passed between all nodes. Each node receives the full state and returns a *partial* dict — LangGraph merges the updates automatically. |
| **Node** | Any Python function `(state) -> dict`. Doesn't need to call an LLM — pure logic nodes are perfectly valid. |
| **Edge** | A fixed A → B transition (`add_edge`). |
| **Conditional Edge** | A routing function that returns the name of the next node based on state. Enables branching and retry loops (`add_conditional_edges`). |

## Why a Graph for Email Generation?

A single LLM call works, but has two problems for a portfolio demo:
1. Hard to test each concern in isolation.
2. A single prompt trying to translate features, pick a tone, *and* write the email tends to produce worse results than focused, chained prompts.

The graph separates concerns into discrete, testable steps:

| Node | LLM | Purpose |
|---|---|---|
| `translate_factors` | None | Converts technical SHAP feature names to plain language |
| `choose_tone` | None | Maps recommendation outcome → tone style guide |
| `generate_email` | Gemini 2.5 Flash Lite | Drafts the email using focused context |
| `validate_email` | Groq llama-3.1-8b-instant | Classifies the email as valid/invalid; triggers retry |

## Multi-Model Strategy

Different nodes intentionally use different models optimized for their task:
- **Gemini 2.5 Flash Lite** — better for creative, nuanced text generation
- **Groq llama-3.1-8b-instant** — ~200ms latency, ideal for binary classification where speed matters and creativity is irrelevant

## Graph Topology

```
START → translate_factors → choose_tone → generate_email → validate_email
                                                ↑                 ↓
                                                └── if invalid ───┘  (max 1 retry)
                                                                  ↓
                                                                 END
```

The retry is capped at 1 iteration to guarantee termination — on a second failure the email is returned as-is rather than blocking the user.

## Code Structure

| Location | Responsibility |
|---|---|
| `email_gen.py` | Graph structure: state schema, nodes, edges, routing, public entry point |
| `prompts.py` | Prompt templates: `build_generation_prompt()`, `build_validation_prompt()` |
| `feature_labels.py` | Feature name → human-readable label mapping used by `translate_factors` |
