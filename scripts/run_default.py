from __future__ import annotations

from _runtime import fail, run_in_venv


def main() -> int:
    try:
        return run_in_venv(
            [
                "-m",
                "b2b_saas_platform_analytics.cli",
                "run-all",
                "--config",
                "config/profiles/portfolio.yaml",
                "--scenario",
                "config/scenarios/baseline.yaml",
                "--data-output",
                "data/generated/default",
                "--report-output",
                "reports/generated/default",
            ]
        )
    except RuntimeError as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
