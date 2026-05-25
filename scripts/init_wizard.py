#!/usr/bin/env python3
"""
Interactive setup wizard for youtube-digest.
Guides the user through 6 steps to configure their digest.
"""

import os
import sys
import yaml


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║                                              ║
║         youtube-to-digest setup              ║
║   AI-curated articles from your favorite     ║
║   YouTube channels, delivered your way.      ║
║                                              ║
╚══════════════════════════════════════════════╝
""")


def step_channels():
    """Step 1: Get core channels from user."""
    print("\n━━━ Step 1: Core Channels ━━━")
    print("List the YouTube @handles you want in your digest.")
    print("One per line. Press Enter twice when done.")
    print()
    print("Example:")
    print("  @Fireship")
    print("  @3Blue1Brown")
    print("  @Veritasium")
    print()

    channels = []
    while True:
        line = input("  > ").strip()
        if not line:
            if channels:
                break
            else:
                print("  Please enter at least one channel.")
                continue
        if not line.startswith("@"):
            line = "@" + line
        channels.append({"handle": line})

    print(f"\n  ✓ {len(channels)} channel(s) added.\n")
    return channels


def step_frequency():
    """Step 2: Choose frequency."""
    print("\n━━━ Step 2: Frequency ━━━")
    print("How often should the digest run?")
    print("  [1] Daily   — one article every day")
    print("  [2] Weekly  — one article every week")
    print("  [3] Monthly — one article every month")

    while True:
        choice = input("  Choose [1/2/3]: ").strip()
        if choice == "1":
            return "daily"
        elif choice == "2":
            return "weekly"
        elif choice == "3":
            return "monthly"
        print("  Please enter 1, 2, or 3.")


def step_distributors():
    """Step 3: Choose distribution channels."""
    print("\n━━━ Step 3: Distribution Channels ━━━")
    print("How should articles be delivered? Pick one or more:")
    print("  [1] Feishu (飞书)       — Feishu Doc + message card")
    print("  [2] Email + EPUB        — email with EPUB ebook attachment")
    print("  [3] Notion               — append to Notion database")
    print("  [4] RSS                  — RSS XML feed")

    while True:
        choices = input("  Choose (e.g., 1,2 or 1): ").strip()
        if not choices:
            print("  Please select at least one.")
            continue
        nums = [c.strip() for c in choices.split(",")]
        dist = {"feishu": False, "email": False, "notion": False, "rss": False}
        dist_map = {"1": "feishu", "2": "email", "3": "notion", "4": "rss"}
        valid = True
        for n in nums:
            if n in dist_map:
                dist[dist_map[n]] = True
            else:
                print(f"  '{n}' is not a valid choice.")
                valid = False
                break
        if valid and any(dist.values()):
            return dist
        print("  Please enter valid numbers (e.g., 1,2).")


def step_llm():
    """Step 4: Choose LLM backend."""
    print("\n━━━ Step 4: AI Backend ━━━")
    print("Which AI model should write the articles?")
    print("  [1] Anthropic Claude   — best magazine-style writing (api.anthropic.com)")
    print("  [2] DeepSeek            — very low cost, good quality (api.deepseek.com)")
    print("  [3] OpenAI (GPT-4o)     — solid all-rounder (api.openai.com)")
    print("  [4] Ollama              — free, runs locally on your machine")

    while True:
        choice = input("  Choose [1/2/3/4]: ").strip()
        if choice == "1":
            return "anthropic", "claude-sonnet-4-20250514"
        elif choice == "2":
            return "deepseek", "deepseek-chat"
        elif choice == "3":
            return "openai", "gpt-4o"
        elif choice == "4":
            model = input("  Ollama model name [llama3.1:8b]: ").strip()
            return "ollama", model or "llama3.1:8b"
        print("  Please enter 1, 2, 3, or 4.")


def step_filter():
    """Step 5: Smart filtering."""
    print("\n━━━ Step 5: Smart Filtering ━━━")
    print("Enable smart content filtering?")
    print("This runs a quick AI check before full article generation to:")
    print("  - Generate a TL;DR summary")
    print("  - Classify topic tags")
    print("  - Optionally skip blocked topics")

    while True:
        choice = input("  Enable? [Y/n]: ").strip().lower()
        if choice in ("y", "yes", ""):
            blocked = input("  Blocked topics (comma-separated, e.g., gaming,drama): ").strip()
            topics = [t.strip().lower() for t in blocked.split(",") if t.strip()]
            return {"enabled": True, "blocked_topics": topics}
        elif choice in ("n", "no"):
            return {"enabled": False, "blocked_topics": []}
        print("  Please enter Y or N.")


def step_summary(channels, frequency, distributors, llm_backend, llm_model, filter_config):
    """Step 6: Show summary and generate config files."""
    print("\n━━━ Step 6: Configuration Summary ━━━\n")
    print(f"  Channels:    {', '.join(ch['handle'] for ch in channels)}")
    print(f"  Frequency:   {frequency}")
    print(f"  Distributors: {[k for k, v in distributors.items() if v]}")
    print(f"  AI Backend:  {llm_backend} ({llm_model})")
    if filter_config["enabled"]:
        print(f"  Filter:      ON (blocked: {', '.join(filter_config['blocked_topics'])})")
    else:
        print(f"  Filter:      OFF")
    print()

    while True:
        choice = input("  Write config files? [Y/n]: ").strip().lower()
        if choice in ("y", "yes", ""):
            write_configs(channels, frequency, distributors, llm_backend, llm_model, filter_config)
            return
        elif choice in ("n", "no"):
            print("  Aborted. No files written.")
            sys.exit(0)
        print("  Please enter Y or N.")


def write_configs(channels, frequency, distributors, llm_backend, llm_model, filter_config):
    """Write config.yaml and .env.example → .env."""
    config = {
        "channels": channels,
        "frequency": frequency,
        "distributors": distributors,
        "llm_backend": llm_backend,
        "llm_model": llm_model,
        "smart_filter": filter_config,
        "content": {"max_tokens": 8000, "language": "zh"},
    }

    config_path = os.path.join(SKILL_DIR, "config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Set restrictive permissions
    os.chmod(config_path, 0o600)

    print(f"\n  ✓ config.yaml written to {config_path}")
    print(f"\n  Next steps:")
    print(f"  1. Edit {os.path.join(SKILL_DIR, '.env')} and fill in your API keys")
    print(f"     (copy from .env.example if you haven't already)")
    print(f"  2. Install dependencies:")
    print(f"       pip install -r {os.path.join(SKILL_DIR, 'requirements.txt')}")
    print(f"  3. Test the pipeline:")
    print(f"       python {os.path.join(SKILL_DIR, 'scripts', 'pipeline_orchestrator.py')} --run-once")
    print(f"  4. Install auto-schedule:")
    print(f"       python {os.path.join(SKILL_DIR, 'scripts', 'install_launchd.py')} --install")
    print()


def run_wizard():
    print_banner()
    channels = step_channels()
    frequency = step_frequency()
    distributors = step_distributors()
    llm_backend, llm_model = step_llm()
    filter_config = step_filter()
    step_summary(channels, frequency, distributors, llm_backend, llm_model, filter_config)


if __name__ == "__main__":
    run_wizard()
