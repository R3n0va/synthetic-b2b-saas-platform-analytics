from __future__ import annotations

import json
from pathlib import Path

from scripts.build_repository_manifest import (
    build_manifest,
    git_tracked_files,
    is_excluded,
    manifest_paths,
)

ROOT = Path(__file__).resolve().parents[1]


def committed_manifest() -> dict[str, object]:
    return json.loads((ROOT / "repository_manifest.json").read_text(encoding="utf-8"))


def test_repository_manifest_entries_match_current_files():
    """Verify governed files without treating unrelated local files as repository content."""
    committed = committed_manifest()
    actual = build_manifest(ROOT, manifest_paths(ROOT, committed))
    assert committed == actual


def test_repository_manifest_covers_git_tracked_files_when_git_is_available():
    """CI catches tracked files omitted from the manifest; ZIP runs ignore local leftovers."""
    tracked = git_tracked_files(ROOT)
    if tracked is None:
        assert not (ROOT / ".git").exists()
        return

    committed = committed_manifest()
    committed_paths = {record["path"] for record in committed["files"]}
    tracked_paths = {path.relative_to(ROOT).as_posix() for path in tracked}
    assert committed_paths == tracked_paths


def test_repository_manifest_has_unique_paths():
    records = committed_manifest()["files"]
    paths = [entry["path"] for entry in records]
    assert len(paths) == len(set(paths))


def test_repository_manifest_excludes_runtime_caches():
    records = committed_manifest()["files"]
    paths = [entry["path"] for entry in records]
    assert not any("__pycache__" in path or ".pytest_cache" in path for path in paths)


def test_repository_manifest_excludes_local_environment_and_runtime_outputs(tmp_path):
    (tmp_path / ".venv" / "Scripts").mkdir(parents=True)
    (tmp_path / ".venv" / "Scripts" / "activate.bat").write_text("ignored", encoding="utf-8")
    (tmp_path / "data_generator" / "src" / "package.egg-info").mkdir(parents=True)
    (tmp_path / "data_generator" / "src" / "package.egg-info" / "PKG-INFO").write_text("ignored", encoding="utf-8")
    (tmp_path / "data" / "generated" / "sample").mkdir(parents=True)
    (tmp_path / "data" / "generated" / "sample" / "runtime.csv").write_text("ignored", encoding="utf-8")
    (tmp_path / "reports" / "generated" / "sample").mkdir(parents=True)
    (tmp_path / "reports" / "generated" / "sample" / "runtime.md").write_text("ignored", encoding="utf-8")
    (tmp_path / ".coverage").write_text("ignored", encoding="utf-8")
    (tmp_path / ".env").write_text("ignored", encoding="utf-8")
    (tmp_path / "README.md").write_text("included", encoding="utf-8")

    manifest = build_manifest(tmp_path)
    assert [entry["path"] for entry in manifest["files"]] == ["README.md"]


def test_repository_manifest_exclusion_rules_cover_local_files():
    for relative in (
        Path(".env"),
        Path(".venv/Scripts/activate.bat"),
        Path("data/generated/sample/runtime.csv"),
        Path("reports/generated/sample/runtime.md"),
        Path("package.egg-info/PKG-INFO"),
    ):
        assert is_excluded(relative)
