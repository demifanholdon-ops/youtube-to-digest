---
name: youtube-to-digest
description: |
  YouTube channel curation pipeline. Fetches latest videos from your selected
  channels on a schedule, generates AI-powered magazine-style article digests,
  and distributes to Feishu (飞书), Notion, Email/EPUB, or RSS. Supports Anthropic,
  DeepSeek, OpenAI, and Ollama backends. Includes smart content filtering.
version: "1.0.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, WebFetch
---

# YouTube to Digest

> AI-curated articles from your favorite YouTube channels, delivered your way.

## When to Use

Activate this skill when the user says:
- "Set up youtube-to-digest" / "Setup youtube digest"
- "Create a YouTube digest" / "Curate my YouTube channels"
- "I want daily AI summaries of my favorite YouTube channels"
- "Turn my YouTube subscriptions into a newsletter"
- "/youtube-to-digest"

## What It Does

Picks one video per cycle from your core YouTube channels (round-robin),
extracts the transcript, transforms it into a polished magazine-style article
using your chosen AI backend, and delivers it through your chosen channels.

## Setup Flow

Guide the user through the initialization wizard:

```bash
python3 SKILL_DIR/scripts/init_wizard.py
```

The wizard asks 6 questions:

### Step 1: Core Channels
"Which YouTube channels do you want in your digest?"
User enters @handles, one per line. The wizard will later resolve these
to channel IDs automatically at runtime.

### Step 2: Frequency
- [1] Daily — one article every day
- [2] Weekly — one article every week
- [3] Monthly — one article every month

### Step 3: Distribution Channels (multi-select)
- [1] Feishu (飞书) — Feishu Doc + message card notification
- [2] Email + EPUB — email with EPUB ebook attachment
- [3] Notion — append to Notion database
- [4] RSS — generate RSS XML feed

### Step 4: AI Backend
- [1] Anthropic Claude — best magazine-style (api.anthropic.com)
- [2] DeepSeek — ~1/20th the cost, good quality (api.deepseek.com)
- [3] OpenAI GPT-4o — solid all-rounder (api.openai.com)
- [4] Ollama — free, runs locally on your machine

### Step 5: Smart Filtering
- Enable/disable. If enabled, each video gets a quick AI pass for:
  - TL;DR summary + topic tags
  - Blocked topic filter (skip e.g., "gaming", "drama")

### Step 6: Configuration
- Generates `config.yaml` (preferences) and prompts user to edit `.env` (API keys)
- `.env` is gitignored — safe for public repos

## Key Design Decisions

### Round-Robin Rotation

Channels are processed in strict rotation order. With 6 channels at daily
frequency: Channel A on Day 1, Channel B on Day 2, ..., Channel A again on Day 7.
If a channel has no new video, it's skipped and rotation moves to the next
channel. Each video is processed at most once.

### LLM Backend Independence

The skill's Python code calls AI APIs directly — it does NOT go through
Claude Code's configured backend. Choosing "DeepSeek" means the code calls
`api.deepseek.com`. Choosing "Anthropic" means `api.anthropic.com`. Two
completely separate API calls.

### Privacy & Security

- ALL secrets in `.env` (gitignored, never committed)
- `config.yaml` contains only preferences (gitignored for safety)
- `.env.example` and `config.yaml.example` committed with placeholders
- Source code has zero hardcoded keys, secrets, or addresses
- Safe for public GitHub repositories

## Commands

| Command | Description |
|---------|-------------|
| `python3 scripts/pipeline_orchestrator.py --run-once` | Run one pipeline cycle |
| `python3 scripts/pipeline_orchestrator.py --status` | Show rotation state |
| `python3 scripts/pipeline_orchestrator.py --run-once --channel @Handle` | Bypass rotation |
| `python3 scripts/init_wizard.py` | Re-run setup wizard |
| `python3 scripts/install_launchd.py --install --frequency daily` | Install auto-schedule |
| `python3 scripts/install_launchd.py --uninstall` | Remove schedule |
| `python3 scripts/install_launchd.py --show` | Show current schedule |

## Requirements

- Python 3.8+
- YouTube Data API key (free from Google Cloud Console)
- Supadata API key (for transcripts)
- API key for your chosen LLM backend
- API keys for your chosen distribution channels

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
                    ├── Feishu (doc + card)
                    ├── Email + EPUB
                    ├── Notion
                    └── RSS
```

## File Locations

- Config: `config.yaml` and `.env` in skill root
- Runtime data: `data/` (rotation state, processed video IDs, archive)
- Prompts: `references/prompts.md`
- Logs: `data/pipeline.log` and `data/pipeline_error.log`

## Known Limitations

- YouTube API has a daily quota of 10,000 units. Each channel check uses ~100 units.
  With 10 channels at daily frequency, that's 1,000 units/day — well within quota.
- Supadata API may rate-limit. The transcript fetcher retries with exponential backoff.
- For the Feishu distributor: the user needs to create a Feishu app and bot first
  at https://open.feishu.cn. The wizard provides guidance.
- Ollama backend requires a running local Ollama server (`ollama serve`).
