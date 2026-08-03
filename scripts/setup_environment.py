from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = PROJECT_ROOT / ".venv"


def environment_python() -> Path:
    if sys.platform.startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.", file=sys.stderr)
        return 1

    if not VENV_DIR.exists():
        print(f"Creating virtual environment: {VENV_DIR}")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    python_executable = environment_python()
    command = [
        str(python_executable),
        "-m",
        "pip",
        "install",
        "-e",
        ".[dev]",
    ]
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        print("Dependency installation failed.", file=sys.stderr)
        print("Check the internet connection and rerun the same command.", file=sys.stderr)
        return exc.returncode

    print("Environment is ready.")
    print(f"Interpreter: {python_executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
