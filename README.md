# youtube-to-digest

> AI-curated articles from your favorite YouTube channels, delivered your way.

**youtube-to-digest** transforms your YouTube subscriptions into a personalized AI-powered magazine. Pick your core channels, choose your AI backend and schedule, and receive polished, magazine-style article digests through Feishu, email, Notion, or RSS.

## What Problem Does This Solve?

You follow great YouTube channels but don't have time to watch every video. Transcripts exist but are messy, repetitive, and unpleasant to read. Manually checking multiple channels and deciding what's worth your time is a daily friction.

**youtube-to-digest** automates the entire pipeline: discovery → curation → transformation → delivery. It picks one video per cycle from your core channels (round-robin), extracts and cleans the transcript, rewrites it into a polished article using AI, and delivers it where you already work — Feishu, Notion, email, or RSS.

## Key Features

- **Round-Robin Curation** — Set your core channels (e.g., 6 favorites). The system picks one per cycle in strict rotation so every channel gets equal coverage. No repeats.

- **Multi-LLM Backend** — Choose your AI engine: Anthropic Claude (best quality), DeepSeek (lowest cost, ~1/20th of Claude), OpenAI GPT-4o, or Ollama (free, local). One backend handles everything.

- **Multi-Platform Delivery** — Articles go where you do. Enable one or more:
  - **Feishu (飞书)** — Full article as a Feishu Doc + message card notification with TL;DR preview
  - **Email + EPUB** — HTML email with EPUB ebook attachment for Kindle/Apple Books
  - **Notion** — Appends to a Notion database for your knowledge base
  - **RSS** — Standard RSS 2.0 XML feed for any RSS reader

- **Smart Content Filtering** — Optional AI pre-scan: generates a TL;DR summary, classifies topics, and can skip blocked topics (e.g., "gaming", "drama") before full processing.

- **Flexible Scheduling** — Daily, weekly, or monthly. Runs via macOS launchd. Idempotent: won't double-process if triggered twice in the same cycle.

- **Privacy-First** — All API keys in `.env` (gitignored). Config in `config.yaml` (gitignored). Zero hardcoded secrets. Safe for public GitHub repos.

## Quick Start

### 1. Installation

```bash
git clone https://github.com/YOUR_USERNAME/youtube-to-digest.git
cd youtube-to-digest
pip install -r requirements.txt
```

### 2. Run the Setup Wizard

```bash
python3 scripts/init_wizard.py
```

The wizard will ask you 6 questions:
1. Which YouTube channels? (enter @handles)
2. How often? (daily / weekly / monthly)
3. Where to deliver? (Feishu / Email / Notion / RSS)
4. Which AI backend? (Anthropic / DeepSeek / OpenAI / Ollama)
5. Enable smart filtering? (Y/N)
6. Confirm and write config

### 3. Configure API Keys

Edit `.env` and fill in the API keys for your chosen services:

```bash
# Required for all setups:
YOUTUBE_API_KEY=...        # https://console.cloud.google.com → YouTube Data API v3
SUPADATA_API_KEY=...       # https://supadata.ai

# Choose ONE LLM backend:
DEEPSEEK_API_KEY=...       # https://platform.deepseek.com (cheapest)
# or ANTHROPIC_API_KEY=...  # https://console.anthropic.com
# or OPENAI_API_KEY=...     # https://platform.openai.com

# Fill in for your chosen distributors:
FEISHU_APP_ID=...          # https://open.feishu.cn
GMAIL_ADDRESS=...          # Gmail + App Password
NOTION_API_KEY=...         # https://www.notion.so/my-integrations
```

### 4. Test the Pipeline

```bash
python3 scripts/pipeline_orchestrator.py --run-once
```

### 5. Install Auto-Schedule (macOS)

```bash
python3 scripts/install_launchd.py --install --frequency daily
```

## Architecture

```
config.yaml ──→ Config Loader ──→ Pipeline Orchestrator
.env                                  │
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                    Rotation     Content      Article
                     Engine      Filter       Generator
                          │           │           │
                          ▼           ▼           ▼
                    YouTube ──→ Transcript ──→ LLM Backend
                    Fetcher     Fetcher        (4 options)
                                                    │
                          ┌─────────────────────────┘
                          ▼
                    Distributors (1-4 enabled)
                    ├── Feishu (Doc + message card)
                    ├── Email + EPUB
                    ├── Notion
                    └── RSS
```

### Pipeline Stages

1. **Rotation Engine** — Picks the next channel in round-robin order, finds the newest unprocessed video
2. **YouTube Fetcher** — Fetches video metadata via YouTube Data API v3, filters out Shorts
3. **Transcript Fetcher** — Extracts the transcript via Supadata API (with retry logic)
4. **Content Filter** (optional) — Lightweight AI pass: TL;DR summary, topic tags, blocklist check
5. **Article Generator** — The chosen AI backend rewrites the transcript into a magazine-style article in Markdown
6. **Distributors** — Each enabled distributor delivers the article to its platform

## FAQ

### What makes this different？

- **Curation-first, not batch**: Picks one video per cycle via round-robin rotation across your core channels — a daily highlight, not a firehose
- **Deliver where you already work**: Feishu Docs, Notion databases, RSS feeds, or email+EPUB — not locked into a single format
- **Your AI, your budget**: Switch between Anthropic Claude (best quality), DeepSeek (~1/20th cost), OpenAI, or free local Ollama — one line of config
- **Smarter filtering**: Optional pre-scan generates TL;DR summaries and topic tags, with a blocklist to skip content you don't want
- **Zero-config onboarding**: 6-step interactive wizard — no editing Python files or writing YAML by hand

### Does the AI call go through my Claude Code?

No. The Python code calls AI APIs directly. If you select DeepSeek, it calls `api.deepseek.com`. If you select Anthropic, it calls `api.anthropic.com`. These are completely independent from whatever backend Claude Code uses.

### Are my API keys safe?

Yes. `.env` and `config.yaml` are both in `.gitignore`. The source code contains zero hardcoded keys or addresses. `.env.example` and `config.yaml.example` are safe to commit — they only contain placeholders.

### What gets cleaned up after 90 days?

Only the **video ID dedup records** in `data/processed_video_ids`. This keeps the tracking file small by removing IDs of old videos that will never be re-encountered. Your generated articles, Feishu docs, EPUBs, and archive files are never automatically deleted.

## License

MIT
