from __future__ import annotations

import argparse
from pathlib import Path

from _runtime import PROJECT_ROOT, fail, run_in_venv


def _resolve_input_path(explicit_input: str | None) -> Path:
    if explicit_input:
        candidate = (PROJECT_ROOT / explicit_input).resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Input directory does not exist: {candidate}")
        return candidate

    candidates = [
        PROJECT_ROOT / "data" / "generated" / "default",
        PROJECT_ROOT / "data" / "generated" / "sample",
    ]
    for candidate in candidates:
        if (candidate / "manifest.json").exists():
            return candidate

    raise FileNotFoundError(
        "No generated dataset was found. Run 'py scripts/run_sample.py' "
        "or 'py scripts/run_default.py' first."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the local PostgreSQL analytical model."
    )
    parser.add_argument(
        "--input",
        help=(
            "Generated source directory. When omitted, the script uses "
            "data/generated/default and then data/generated/sample."
        ),
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Keep existing project schemas instead of rebuilding them.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return fail(
            ".env is missing. Copy .env.example to .env and enter local PostgreSQL credentials."
        )

    try:
        input_path = _resolve_input_path(args.input)
        relative_input = input_path.relative_to(PROJECT_ROOT)
        print(f"Using generated dataset: {relative_input}")
        command = [
            "-m",
            "b2b_saas_platform_analytics.cli",
            "db-build",
            "--env-file",
            ".env",
            "--input",
            str(relative_input),
            "--project-root",
            ".",
        ]
        if not args.no_reset:
            command.append("--reset")
        return run_in_venv(command)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
