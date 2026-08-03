from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if key == "include":
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    include = payload.get("include")
    if include:
        include_path = Path(include)
        if not include_path.is_absolute():
            project_root = path.parent.parent if path.parent.name == "config" else path.parent
            include_path = project_root / include_path
        base = load_yaml(include_path)
        return deep_merge(base, payload)
    return payload


def load_config(config_path: str | Path, scenario_path: str | Path | None = None) -> dict[str, Any]:
    config = load_yaml(config_path)
    if scenario_path:
        scenario = load_yaml(scenario_path)
        config = deep_merge(config, scenario)
    return config
