from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.build_repository_manifest import manifest_paths

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml", ".sql", ".txt", ".json"}


def governed_files() -> list[Path]:
    manifest = json.loads((ROOT / "repository_manifest.json").read_text(encoding="utf-8"))
    return manifest_paths(ROOT, manifest)


def repository_text() -> str:
    chunks = []
    for path in governed_files():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name in {"repository_manifest.json", "test_repository_consistency.py"}:
            continue
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_repository_uses_governed_project_name():
    setup_text = (ROOT / "setup.py").read_text(encoding="utf-8")
    requirements_text = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "Synthetic B2B SaaS Platform Analytics" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "synthetic-b2b-saas-platform-analytics" in setup_text
    assert "tabulate>=0.9.0" in setup_text
    assert "tabulate>=0.9.0" in requirements_text


def test_obsolete_project_names_are_absent():
    text = repository_text()
    assert "Synthetic B2B SaaS Analytics Platform Platform" not in text
    assert "synthetic-b2b-saas-analytics-platform" not in text
    assert "saas_analytics" not in text
    assert "saas-analytics" not in text


def test_no_container_or_platform_wrapper_assets_are_committed():
    names = [path.name.lower() for path in governed_files()]
    assert "dockerfile" not in names
    assert not any(name.startswith("docker-compose") for name in names)
    assert not any(name.endswith((".bat", ".cmd", ".ps1", ".sh")) for name in names)


def test_sql_quality_registry_contains_fifty_controls():
    sql = (ROOT / "sql/05_quality/01_control_results.sql").read_text(encoding="utf-8")
    control_ids = re.findall(r"SELECT\s+'(Q\d{3})'", sql, flags=re.IGNORECASE)
    assert len(control_ids) == 50
    assert len(set(control_ids)) == 50
