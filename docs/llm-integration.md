# LLM Integration Notes (Structure Only)

This document outlines how to add LLM-powered features without coupling them to core parsing and analytics.

## Current integration hooks

- API context endpoint: `GET /api/chat/<chat_id>/context`
- Message retrieval endpoint: `GET /api/chat/<chat_id>/messages`
- Additional analysis endpoints:
  - `GET /api/chat/<chat_id>/response-patterns`
  - `GET /api/chat/<chat_id>/media-links`
- Config placeholders in `config.py`:
  - `KAAJD_LLM_ENDPOINT_URL`
  - `KAAJD_LLM_MODEL`
  - `KAAJD_LLM_API_KEY`

## Suggested architecture

Keep LLM calls in a dedicated module (future `app/llm.py`) and pass only minimal, structured context.

Suggested flow:

1. Fetch context + targeted message slices via existing DB-backed helpers.
2. Build compact prompt payloads (JSON-like summaries, not full raw chat by default).
3. Call configured LLM endpoint.
4. Return generated commentary as separate API payloads.

## Planned feature patterns

### 1) Snarky commentary per chart

- Input: chart-specific stats (`response-patterns`, `media-links`, summary totals).
- Output: short roast/insight paragraph.
- Placement: dashboard cards under each chart block.

### 2) Chat Q&A

- Input: user question + filtered message retrieval (`query_messages(...)`).
- Retrieval: keyword + timeframe + participant filters before model call.
- Output: answer with references to message excerpts.

### 3) Time-windowed summaries

- Input: monthly or yearly message chunks from DB.
- Output: period summaries and change-over-time observations.

## Safety and privacy baseline

- Default to local-only processing where possible.
- Never log full prompts containing sensitive chat data in production logs.
- Allow disabling LLM integration by leaving endpoint/model config empty.

## Example env settings

```bash
KAAJD_LLM_ENDPOINT_URL=https://your-openwebui-or-llm-endpoint/v1/chat/completions
KAAJD_LLM_MODEL=your-model-name
KAAJD_LLM_API_KEY=your-api-key
```

No LLM runtime is implemented yet; this document defines the structure for future work.
