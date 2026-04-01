# Gisst

**The AI research agent that lives in your chat.**

---

## I. The Name

### **Gisst**

Derived from "gist" — the essential point of something. The spelling is deliberate: ownable, searchable, impossible to confuse with another product. It becomes a verb: "Gisst that for me." "I Gisst-ed the whole regulatory landscape." "Just Gisst it."

**Domains:** Gisst.ai + Gisst.io (both available, secure both)

**Pronunciation:** Same as "gist." The double-s is visual only — it makes the brand scannable in a URL and distinct in search results.

**Also consider acquiring:** gyst.io as a redirect if available. People may drop the second S instinctively — owning the redirect eliminates lost traffic.

### Agent Naming

Default agent template is called a **Scout**. But users name and configure their own agents. A Scout is the starting point. Users might call theirs "Hal," "Friday," "PolicyBot," or whatever fits their workflow. Gisst doesn't impose naming — it enables it.

### No Branded Feature Names

Scheduled updates are scheduled updates. Knowledge bases are knowledge bases. Chat is chat. Features are self-evident; they don't need internal marketing language.

---

## II. Product Thesis

The information economy has a fragmentation problem. The tools for *finding* information, *discussing* information, and *organizing* information are three separate workflows. A researcher reads an article, switches to Slack to share it, then switches to Notion to file it. A founder scans Twitter for market signals, copies links into a group chat, and manually builds a competitive intel doc.

**Gisst eliminates the seams.**

Gisst is an AI agent that embeds directly into the communication channels people already use — WhatsApp, Telegram, Slack, Discord — and acts as a persistent research partner. It doesn't ask users to adopt a new app. It meets them where they are. It monitors topics on a schedule, answers questions with sourced depth, and accumulates everything it surfaces into a structured, evolving knowledge base that the user owns.

**The core insight:** The chat thread *is* the research session. Every question asked, every article surfaced, every follow-up clarification is a signal about what matters. Gisst captures that signal and crystallizes it into durable knowledge — exported to Notion, Obsidian, or any vault the user controls.

**The long-term bet:** Knowledge bases built through Gisst become training data. Users can fine-tune their own agent, spin up specialized child agents, or license their curated datasets. The product becomes a flywheel: use generates knowledge, knowledge improves the agent, a better agent generates better use.

---

## III. Product Principles

**1. Zero New Apps.**
Gisst never asks the user to leave their communication channel. The chat *is* the interface. If you want a dashboard later, fine — but the default experience is conversational.

**2. Sources or Silence.**
Every claim an agent makes is cited. If it can't source something, it says so. Trust is the product. There is no hallucination-tolerant mode.

**3. Knowledge Compounds.**
Every interaction should make the system smarter. A question answered today should make tomorrow's briefing more relevant. The knowledge base grows. The agent learns. Idle agents are wasted agents.

**4. User Owns the Data.**
Knowledge bases are exportable. Always. In standard formats (Markdown, JSON, CSV). The user can leave Gisst and take every byte of accumulated knowledge with them. Lock-in comes from value, not hostage data.

**5. Opinionated Defaults, Open Architecture.**
Out of the box, Gisst should work beautifully for a solo researcher tracking three topics. But the system should also support a newsroom running 40 agents across 12 channels with shared knowledge bases feeding a custom model.

---

## IV. Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Gisst PLATFORM                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              CHANNEL ADAPTER LAYER                    │   │
│  │                                                       │   │
│  │  WhatsApp · Telegram · Slack · Discord · REST API     │   │
│  │                                                       │   │
│  │  Each adapter handles auth, rate limits, formatting,  │   │
│  │  and platform-specific constraints (e.g. WhatsApp's   │   │
│  │  4096-char limit, Slack Block Kit, Telegram MD)       │   │
│  │                                                       │   │
│  │          ┌─────────────────────┐                       │   │
│  │          │   MESSAGE ROUTER    │                       │   │
│  │          │   (intent + auth)   │                       │   │
│  │          └──────────┬──────────┘                       │   │
│  └─────────────────────┼─────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐   │
│  │                 AGENT ENGINE                           │   │
│  │                                                       │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │   │
│  │  │   QUERY      │ │  RESEARCH    │ │  SYNTHESIS   │   │   │
│  │  │   UNDERSTAND │→│  ORCHESTRATE │→│  & CITATION  │   │   │
│  │  └──────────────┘ └──────┬───────┘ └──────────────┘   │   │
│  │                          │                             │   │
│  │              ┌───────────┼───────────┐                 │   │
│  │              ▼           ▼           ▼                 │   │
│  │         Web Search   News APIs   Academic APIs         │   │
│  │         (Tavily,     (NewsAPI,   (Semantic Scholar,    │   │
│  │          Brave,       GDELT,     arXiv, PubMed)        │   │
│  │          Serper)      Bing News)                       │   │
│  └───────────────────────────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐   │
│  │              KNOWLEDGE LAYER                           │   │
│  │                                                       │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │  Vector    │  │  Graph Store │  │  Export       │  │   │
│  │  │  Store     │  │  (entities,  │  │  Engine       │  │   │
│  │  │  (semantic │  │  relations,  │  │               │  │   │
│  │  │  retrieval)│  │  topics)     │  │  Notion sync  │  │   │
│  │  │            │  │              │  │  Obsidian sync│  │   │
│  │  │            │  │              │  │  JSON/MD/CSV  │  │   │
│  │  └────────────┘  └──────────────┘  └───────────────┘  │   │
│  └───────────────────────────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐   │
│  │              SCHEDULER                                 │   │
│  │                                                       │   │
│  │  Cron-based schedules (daily, weekly, custom)          │   │
│  │  Event triggers ("alert me when X happens")            │   │
│  │  Digest mode (batch updates into one message)          │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

**Channel Adapter Layer** — Abstraction over messaging platform APIs. Each adapter handles authentication, message parsing, rate limits, and platform-specific formatting. New channels are added as adapters without touching the Agent Engine. This is the key to "zero new apps" — Gisst is protocol-native to wherever the user already lives.

**Message Router** — Classifies incoming messages by intent. Is this a new research query? A follow-up? A command to schedule an update? A request to export the knowledge base? Also maps platform user IDs to Gisst accounts for auth.

**Agent Engine** — The core intelligence loop, in three stages:
- *Query Understanding* — Disambiguates the request, identifies topic boundaries, determines depth needed.
- *Research Orchestration* — Fans out to web search, news APIs (NewsAPI, GDELT, Bing News), academic sources (Semantic Scholar, arXiv), and any user-configured custom sources. Runs multiple search passes, cross-references, validates.
- *Synthesis & Citation* — Compresses findings into a coherent briefing. Every factual claim links back to a source. Formats output for the target channel.

**Knowledge Layer** — Dual-store architecture:
- *Vector Store* (embeddings of every source, every conversation turn, every knowledge base entry) for semantic retrieval.
- *Graph Store* (entities, relationships, topic hierarchies) for structural reasoning — "Show me everything connected to TSMC's Arizona fab."
- *Export Engine* — Transforms accumulated knowledge into structured outputs: Notion databases with properties and relations, Obsidian vaults with wiki-links and tags, or raw JSON/Markdown/CSV for custom pipelines.

**Scheduler** — Manages recurring briefings. Supports cron-style schedules ("every weekday at 7am"), event triggers ("whenever a new FDA approval drops in oncology"), and digest modes ("batch everything from this week into one Sunday message").

### Data Flow: A Typical Interaction

```
User (in Telegram): "What's happening with the EU AI Act enforcement?"
    │
    ▼
Channel Adapter (Telegram) → Message Router
    │
    ▼  Intent: research query
    │
Agent Engine:
  1. Query Understanding → topic: EU AI Act, scope: enforcement
  2. Research Orchestration → searches 4 sources, retrieves 12 articles
  3. Synthesis → 300-word briefing with 5 citations
    │
    ▼
Response sent to Telegram (formatted for Telegram markdown)
    │
    ▼  (simultaneously)
Knowledge Layer:
  - Embeds articles + response in Vector Store
  - Updates Graph: [EU AI Act] → [enforcement] → [specific entities]
  - Appends to knowledge base (if auto-sync → pushes to Notion)
```

### Technical Decisions

**Stateless agents.** Each agent is a stateless function triggered by an incoming message or a scheduled job. The Knowledge Layer is the only stateful component. Agents scale horizontally.

**Model-agnostic.** Frontier models (Claude, GPT-4 class) for synthesis and complex reasoning. Smaller, faster models for classification, intent routing, entity extraction. Swappable backend via abstraction layer.

**Privacy-first.** All data encrypted at rest (AES-256) and in transit (TLS 1.3). User messages processed but not stored beyond the Knowledge Layer (which the user controls). GDPR-compliant deletion: account deletion purges all data within 72 hours.

**Source ethics.** Respect robots.txt and rate limits. Cache frequently-accessed sources. Attribute all sources clearly. Provide original source links prominently — Gisst is a citation tool, not a content laundering tool.

---

## V. Design System

### Philosophy: "Invisible Until Needed"

Gisst is primarily experienced *inside other apps*. The design system isn't about a flashy UI — it's about making agent responses feel native, trustworthy, and scannable in every channel.

### Brand Identity

**Logotype:** "Gisst" in a geometric sans-serif (Inter or Satoshi family). Clean, lowercase-friendly. The double-s gives it a visual rhythm that stands out in URLs and headers. No icon needed initially — the word itself is the brand.

**Color Palette:**

| Token    | Hex       | Usage                                      |
|----------|-----------|--------------------------------------------|
| Ink      | #0F0F0F   | Primary text                               |
| Slate    | #64748B   | Secondary text, metadata                   |
| Cobalt   | #2563EB   | Primary action, links, agent identity      |
| Ember    | #F59E0B   | Alerts, breaking updates                   |
| Jade     | #10B981   | Confirmations, source verified             |
| Ghost    | #F8FAFC   | Backgrounds, cards                         |
| Bone     | #E2E8F0   | Borders, dividers                          |

**Typography:**

| Element   | Spec                      |
|-----------|---------------------------|
| Headlines | Satoshi Bold, 20–28px     |
| Body      | Inter Regular, 14–16px    |
| Metadata  | Inter Medium, 11–12px     |
| Code/Data | JetBrains Mono, 13px      |

### Message Formatting (In-Chat)

Since Gisst lives in chat, formatting must be channel-aware but conceptually consistent.

**Scheduled Update:**
```
📡 Gisst — AI Policy
Tuesday, April 1 · Morning

▸ EU AI Act: First enforcement actions expected in Q3 as
  compliance office staffs up. (Reuters, Mar 31)

▸ US Senate introduces bipartisan AI transparency bill
  requiring model cards for frontier systems. (AP, Mar 30)

▸ China's CAC publishes draft rules for AI-generated
  content labeling. (SCMP, Mar 29)

—
3 sources · 2 new entities tracked · Knowledge base updated
Reply with a number (1–3) to deep-dive.
```

**Research Response:**
```
🔍 EU AI Act Enforcement — Quick Brief

The EU AI Office has begun recruiting enforcement staff,
with ~140 positions posted across Brussels and member
states [1]. First formal investigations are expected to
target high-risk AI systems in hiring and credit scoring
[2]. Companies have until August 2026 for full compliance
on general-purpose AI provisions [3].

Sources:
[1] reuters.com/tech/eu-ai-office-hiring...
[2] politico.eu/ai-act-enforcement-priority...
[3] artificialintelligenceact.eu/timeline...

💾 Added to knowledge base: "EU AI Act" → Enforcement
```

**Event-Triggered Alert:**
```
⚡ Gisst ALERT — Breaking

OpenAI has announced GPT-5 release date: June 2026.
Your agent "AI Landscape" flagged this based on your
tracking rules.

→ 4 related articles found
→ Reply "brief" for full analysis
```

### Dashboard UI (Phase 2+)

For users who want a visual command center beyond chat.

**Layout:** Three-column on desktop. Left: agent list + status. Center: feed/conversation view. Right: knowledge base browser + graph visualization.

**Card System:** Every piece of intelligence is a card with a source badge, confidence indicator, timestamp, and action buttons (save, share, deep-dive, dismiss).

**Dark mode first.** Knowledge workers and researchers skew toward dark mode.

---

## VI. Product Roadmap

### Phase 0 — Foundation (Months 1–3)

*Goal: One agent, one channel, one knowledge base. Prove the core loop.*

- Single-channel support (Telegram — fastest API, richest formatting)
- Core agent engine with web search + 2 news APIs
- Basic scheduling (daily/weekly, fixed times)
- Manual knowledge base export (Markdown files via chat command)
- Conversation memory within a session
- Source citation on every response
- Waitlist + 100 alpha users

**Success metric:** 60% of alpha users send 3+ queries/week after week 2.

### Phase 1 — Multi-Channel + Knowledge Base Sync (Months 4–6)

*Goal: Be everywhere the user is. Make the knowledge base a living document.*

- Add WhatsApp, Slack, and Discord adapters
- Cross-channel agent identity (same agent, reachable from any channel)
- Notion integration (auto-sync knowledge base to Notion databases)
- Obsidian integration (auto-sync to Obsidian vault with wiki-links)
- Persistent memory across conversations
- Topic clustering and entity extraction in the Knowledge Layer
- User-configurable source preferences (trust tiers, blocked domains)
- Event-triggered alerts ("alert me when X happens")
- Agent configuration and naming (users customize their agent's name, personality, depth preferences)

**Success metric:** 40% of users have auto-sync enabled to Notion or Obsidian.

### Phase 2 — Intelligence & Depth (Months 7–10)

*Goal: Make agents genuinely smarter than a person doing the same research.*

- Academic source integration (Semantic Scholar, arXiv, PubMed)
- Multi-step research chains (agent follows leads across multiple searches)
- Comparative analysis ("How does Company A's approach differ from B's?")
- Graph visualization of knowledge base (viewable in web dashboard)
- Collaborative knowledge bases (shared across team members)
- Web dashboard MVP (read-only view of agents, schedules, and knowledge bases)

**Success metric:** Research depth score (source diversity, cross-referencing, analytical quality) exceeds baseline by 3x.

### Phase 3 — The Flywheel (Months 11–15)

*Goal: Knowledge bases become productive assets. Agents improve themselves.*

- Knowledge base as training data export (JSONL format for fine-tuning)
- Agent fine-tuning from knowledge base (specialize an agent using accumulated knowledge)
- Child agents (spin up a new agent pre-loaded with a knowledge base)
- Knowledge base marketplace (opt-in: users publish or sell curated knowledge bases)
- API access (build custom applications on top of Gisst agents and knowledge bases)
- Multi-agent orchestration (agents that coordinate with each other)
- Custom source connectors (user adds their own APIs, RSS feeds, databases)

**Success metric:** 20% of active users have created a child agent or exported training data.

### Phase 4 — Platform (Months 16–24)

*Goal: Gisst becomes infrastructure. Other products are built on it.*

- Self-hosted option for enterprise
- Plugin system for custom agent behaviors
- Knowledge base federation (link knowledge bases across organizations)
- Real-time collaborative research sessions (multiple users + agent in one thread)
- Agent-to-agent communication protocol
- Compliance and audit trail features for regulated industries
- White-label offering

---

## VII. User Personas

### "The Solo Researcher" — Priya
AI policy researcher at a think tank. Tracks regulatory developments across 6 jurisdictions. Currently uses 14 browser tabs, 3 newsletters, and a messy Notion database. Needs an agent watching each jurisdiction, a morning briefing, and a knowledge base that auto-builds her literature review.

### "The Founder" — Marcus
Series A startup founder in climate tech. Needs competitive intel, investor news, and market signals. Lives in Slack. Wants an agent in his team's Slack channel that anyone can query, with a shared knowledge base the whole team references.

### "The Content Creator" — Aisha
Writes a paid newsletter on AI. Needs to find stories before anyone else, understand them deeply, and have organized source material. Wants event-triggered alerts and a knowledge base she can use as her story research archive.

### "The ML Engineer" — Jun
Building domain-specific models. Needs curated, high-quality datasets on narrow topics. Wants an agent that accumulates and structures data for months, then exports a clean JSONL file for fine-tuning.

---

## VIII. Monetization

### Free — "Observer"
- 1 agent
- 1 channel
- 5 queries/day
- Weekly scheduled updates only
- Manual knowledge base export (Markdown)
- 30-day knowledge retention

### Pro — $15/month — "Analyst"
- 5 agents
- All channels
- Unlimited queries
- Custom schedules + event triggers
- Notion + Obsidian auto-sync
- Unlimited knowledge retention

### Team — $12/user/month (min 3) — "Bureau"
- 20 agents (shared pool)
- Collaborative knowledge bases
- Shared channel deployment
- Admin controls and audit log
- Priority source access

### Enterprise — Custom Pricing
- Unlimited agents
- Self-hosted option
- Custom source connectors
- Fine-tuning and child agent capabilities
- SLA and dedicated support
- Knowledge base federation
- SSO/SAML

### Flywheel Revenue (Phase 3+)
- Knowledge base marketplace transaction fee (15%)
- Training data export as premium feature
- Fine-tuning compute as usage-based billing

---

## IX. Competitive Landscape

|                           | Gisst | Feedly AI | Perplexity | ChatGPT | Artifact |
|---------------------------|-------|-----------|------------|---------|----------|
| Lives in your chat        | ✅    | ❌        | ❌         | ❌      | ❌       |
| Scheduled briefings       | ✅    | ✅        | ❌         | ❌      | ❌       |
| Builds knowledge base     | ✅    | Partial   | ❌         | ❌      | ❌       |
| Cited sources             | ✅    | ✅        | ✅         | Partial | ✅       |
| Exports to Notion/Obsidian| ✅    | ❌        | ❌         | ❌      | ❌       |
| Fine-tunable from usage   | ✅    | ❌        | ❌         | ❌      | ❌       |
| Multi-channel             | ✅    | ❌        | ❌         | ❌      | ❌       |
| User-named agents         | ✅    | ❌        | ❌         | ✅      | ❌       |

**Gisst's moat is the compound loop:** Chat → Research → Knowledge Base → Better Agent → Better Chat. No competitor connects all four.

---

## X. Key Risks & Mitigations

**Platform dependency on messaging APIs.** WhatsApp and Telegram can change API terms. *Mitigation:* Multi-channel from Phase 1. No single channel exceeds 40% of usage. API-first architecture means a new adapter takes weeks, not months.

**Source quality and misinformation.** Agents could surface bad information. *Mitigation:* Source trust tiers, cross-referencing requirements for factual claims, explicit confidence indicators. "Sources or Silence" principle.

**User data sensitivity.** Knowledge bases may contain proprietary research. *Mitigation:* Encryption, user-controlled retention, self-hosted option for enterprise, clear data processing agreements.

**LLM cost at scale.** Heavy research queries are expensive. *Mitigation:* Tiered model usage (cheap models for routing, expensive for synthesis), aggressive caching, query complexity estimation.

---

## XI. Taglines

**Primary:** "Just Gisst it."

**Alternatives:**
- "The gist of everything. Faster."
- "Research that lives where you work."
- "Your chat already knows everything. Now it actually does."
- "Send an agent. Build a knowledge base. Know more tomorrow."

---

*Gisst.ai · Gisst.io*
