from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "Synthetic B2B SaaS Platform Analytics"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "htmlcov",
}
EXCLUDED_FILES = {
    "repository_manifest.json",
    ".coverage",
    ".env",
    ".DS_Store",
    "Thumbs.db",
}
EXCLUDED_PREFIXES = {
    ("data", "generated"),
    ("reports", "generated"),
}


def is_excluded(relative: Path) -> bool:
    """Return True for local, generated, cached, or self-referential files."""
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in relative.parts):
        return True
    if relative.name in EXCLUDED_FILES or relative.name.startswith(".coverage."):
        return True
    if any(relative.parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIXES):
        return True
    return relative.suffix == ".pyc"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files(root: Path) -> list[Path]:
    """Scan a source tree for files eligible for a newly built manifest."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if is_excluded(relative):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def git_tracked_files(root: Path) -> list[Path] | None:
    """Return governed Git-tracked files when the repository metadata is available.

    ZIP distributions do not contain .git. In that case local verification uses the
    committed manifest itself and deliberately ignores unrelated files left by a
    previous extraction or created by the user.
    """
    if not (root / ".git").exists():
        return None

    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None

    paths: list[Path] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8"))
        if is_excluded(relative):
            continue
        path = root / relative
        if path.is_file():
            paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(root).as_posix())


def manifest_paths(root: Path, manifest: dict[str, object]) -> list[Path]:
    """Resolve only the files explicitly governed by a committed manifest."""
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("Manifest field 'files' must be a list.")

    paths: list[Path] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ValueError("Every manifest record must contain a string 'path'.")
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe manifest path: {relative}")
        paths.append(root / relative)
    return paths


def build_manifest(root: Path = PROJECT_ROOT, files: Iterable[Path] | None = None) -> dict[str, object]:
    """Build a deterministic manifest from the supplied or discovered files."""
    selected = list(files) if files is not None else included_files(root)
    selected = sorted(selected, key=lambda item: item.relative_to(root).as_posix())

    records: list[dict[str, object]] = []
    total_bytes = 0
    for path in selected:
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total_bytes += size
        records.append({"path": relative, "bytes": size, "sha256": file_digest(path)})

    return {
        "project_name": PROJECT_NAME,
        "file_count": len(records),
        "total_bytes": total_bytes,
        "files": records,
    }


def main() -> int:
    # In a real Git checkout, use tracked files so untracked local artifacts cannot
    # enter the published manifest. In a ZIP source tree, scan the clean tree.
    selected = git_tracked_files(PROJECT_ROOT)
    manifest = build_manifest(PROJECT_ROOT, selected)
    output = PROJECT_ROOT / "repository_manifest.json"
    output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote {manifest['file_count']} file records to {output.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
