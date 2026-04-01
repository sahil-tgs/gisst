# Architecture Decisions

## 2026-04-01: Agent Runtime
**Decision**: Use Claude Code CLI directly via `claude -p` instead of Anthropic API.
**Why**: User has $200/mo Claude Code plan. CLI includes WebSearch, WebFetch, file tools, and Bash built-in. No need to reimplement tools or pay separate API costs.
**Trade-off**: Process spawning is heavier than API calls, but fine for prototype scale.
**Migration path**: Swap to API via OpenRouter/LiteLLM later if needed.

## 2026-04-01: WhatsApp Integration
**Decision**: WhatsApp Cloud API (official Meta) over Baileys (unofficial).
**Why**: Baileys has real ban risk, breaks when WhatsApp updates protocol. Cloud API has instant test setup (test number + 5 contacts), production in 1-5 days.

## 2026-04-01: Web Search
**Decision**: Claude Code native WebSearch + WebFetch + Jina Reader. No extra search APIs.
**Why**: Minimize dependencies. Native tools are adequate for prototype. Jina Reader (r.jina.ai/<url>) converts pages to clean markdown for free. Add Tavily later only if search quality becomes a bottleneck.

## 2026-04-01: Knowledge Base
**Decision**: Notion API for structured knowledge storage.
**Why**: User already uses Notion. Structured databases with properties, relations, views. Good API. Export-friendly.
