"""Configuration loaders for parser modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


@lru_cache(maxsize=1)
def load_edinet_config() -> Dict[str, Any]:
    """Load EDINET parser configuration from YAML."""
    config_path = Path(__file__).with_name("edinet.yaml")
    with config_path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f)
    return data


__all__ = ["load_edinet_config"]


