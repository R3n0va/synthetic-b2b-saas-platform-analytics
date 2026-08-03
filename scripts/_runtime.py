from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = PROJECT_ROOT / ".venv"


def venv_python() -> Path:
    """Return the project virtual-environment interpreter."""
    if os.name == "nt":
        path = VENV_DIR / "Scripts" / "python.exe"
    else:
        path = VENV_DIR / "bin" / "python"
    if not path.exists():
        raise RuntimeError(
            "Project environment is missing. Run: py -3.14 scripts/setup_environment.py"
        )
    return path


def run_in_venv(args: Sequence[str]) -> int:
    """Run a command with the project interpreter from the repository root."""
    command = [str(venv_python()), *args]
    environment = os.environ.copy()
    source_path = str(PROJECT_ROOT / "data_generator" / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not existing_pythonpath else os.pathsep.join([source_path, existing_pythonpath])
    )
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=False)
    return completed.returncode


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1
