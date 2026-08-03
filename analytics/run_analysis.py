from __future__ import annotations

import argparse
from pathlib import Path

from b2b_saas_platform_analytics.analytics import generate_reports
from b2b_saas_platform_analytics.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the governed analytical report pack.")
    parser.add_argument("--config", default="config/profiles/portfolio.yaml")
    parser.add_argument("--scenario", default="config/scenarios/baseline.yaml")
    parser.add_argument("--input", default="data/generated/default")
    parser.add_argument("--output", default="reports/generated/default")
    args = parser.parse_args()
    config = load_config(args.config, args.scenario)
    manifest = generate_reports(Path(args.input), Path(args.output), config)
    print(f"Generated {len(manifest['reports'])} reports.")
    return 0 if manifest["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
