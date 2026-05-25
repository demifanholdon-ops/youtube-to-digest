"""
Unified config loading and validation.
Loads .env secrets + config.yaml preferences, validates, returns frozen Config.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when config is missing required keys or values."""
    pass


@dataclass(frozen=True)
class Channel:
    handle: str
    name: str = ""
    channel_id: str = ""


@dataclass(frozen=True)
class SmartFilterConfig:
    enabled: bool
    blocked_topics: List[str] = field(default_factory=list)
    min_article_length: int = 300


@dataclass(frozen=True)
class ContentConfig:
    max_tokens: int = 8000
    language: str = "zh"


@dataclass(frozen=True)
class Config:
    channels: List[Channel]
    frequency: str
    distributors: Dict[str, bool]
    llm_backend: str
    llm_model: str
    smart_filter: SmartFilterConfig
    content: ContentConfig


# Valid choices
VALID_FREQUENCIES = {"daily", "weekly", "monthly"}
VALID_LLM_BACKENDS = {"anthropic", "deepseek", "openai", "ollama"}
VALID_DISTRIBUTORS = {"feishu", "email", "notion", "rss"}

# Which env vars each distributor needs
DISTRIBUTOR_REQUIRED_ENV = {
    "email": ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"],
    "feishu": ["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
    "notion": ["NOTION_API_KEY", "NOTION_DATABASE_ID"],
    "rss": ["RSS_OUTPUT_PATH"],
}

# Which env var each LLM backend needs
LLM_REQUIRED_ENV = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "ollama": [],  # no key needed
}


def _find_skill_dir() -> str:
    """Find the skill root directory (parent of scripts/)."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(this_dir)


def load_config(skill_dir: Optional[str] = None) -> Config:
    """
    Load and validate config.yaml and .env.
    Returns a frozen Config. Raises ConfigError on failure.
    """
    if skill_dir is None:
        skill_dir = _find_skill_dir()

    # Load .env
    env_path = os.path.join(skill_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("[config] .env not found — please copy .env.example to .env and fill in your keys.")

    # Load config.yaml
    config_path = os.path.join(skill_dir, "config.yaml")
    if not os.path.exists(config_path):
        raise ConfigError(
            f"config.yaml not found at {config_path}. "
            f"Copy config.yaml.example to config.yaml and edit it."
        )

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError("config.yaml is empty.")

    # Parse channels
    channels = []
    raw_channels = raw.get("channels", [])
    for ch in raw_channels:
        handle = ch.get("handle", "")
        if not handle:
            continue
        channels.append(Channel(
            handle=handle,
            name=ch.get("name", handle),
            channel_id=ch.get("channel_id", ""),
        ))

    if not channels:
        raise ConfigError("No channels configured. Add at least one channel to config.yaml.")

    # Parse frequency
    frequency = raw.get("frequency", "daily")
    if frequency not in VALID_FREQUENCIES:
        raise ConfigError(f"Invalid frequency '{frequency}'. Choose: {', '.join(sorted(VALID_FREQUENCIES))}")

    # Parse distributors
    distributors = {}
    raw_dist = raw.get("distributors", {})
    for name in VALID_DISTRIBUTORS:
        distributors[name] = bool(raw_dist.get(name, False))

    if not any(distributors.values()):
        raise ConfigError("At least one distributor must be enabled. Edit config.yaml.")

    # Validate each enabled distributor has its env vars
    for name, enabled in distributors.items():
        if enabled:
            for var in DISTRIBUTOR_REQUIRED_ENV.get(name, []):
                val = os.getenv(var)
                if not val or "your_" in val.lower():
                    raise ConfigError(
                        f"Distributor '{name}' is enabled but {var} is not set in .env"
                    )

    # Parse LLM backend
    llm_backend = raw.get("llm_backend", "anthropic")
    if llm_backend not in VALID_LLM_BACKENDS:
        raise ConfigError(f"Invalid llm_backend '{llm_backend}'. Choose: {', '.join(sorted(VALID_LLM_BACKENDS))}")

    for var in LLM_REQUIRED_ENV.get(llm_backend, []):
        val = os.getenv(var)
        if not val or "your_" in val.lower():
            raise ConfigError(
                f"LLM backend '{llm_backend}' is selected but {var} is not set in .env"
            )

    llm_model = raw.get("llm_model", "claude-sonnet-4-20250514")

    # Parse smart filter
    sf_raw = raw.get("smart_filter", {})
    smart_filter = SmartFilterConfig(
        enabled=bool(sf_raw.get("enabled", False)),
        blocked_topics=[t.lower().strip() for t in sf_raw.get("blocked_topics", []) if t.strip()],
        min_article_length=int(sf_raw.get("min_article_length", 300)),
    )

    # Parse content config
    ct_raw = raw.get("content", {})
    content = ContentConfig(
        max_tokens=int(ct_raw.get("max_tokens", 8000)),
        language=ct_raw.get("language", "zh"),
    )

    config = Config(
        channels=channels,
        frequency=frequency,
        distributors=distributors,
        llm_backend=llm_backend,
        llm_model=llm_model,
        smart_filter=smart_filter,
        content=content,
    )

    print(f"[config] Loaded: {len(config.channels)} channels, {config.frequency}, "
          f"llm={config.llm_backend}/{config.llm_model}, "
          f"dist={[k for k, v in config.distributors.items() if v]}")
    return config


if __name__ == "__main__":
    try:
        cfg = load_config()
        print(f"OK: {cfg}")
    except ConfigError as e:
        print(f"Config Error: {e}")
        sys.exit(1)
