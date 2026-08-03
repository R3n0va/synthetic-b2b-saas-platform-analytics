from __future__ import annotations

import argparse
from pathlib import Path

from b2b_saas_platform_analytics.analytics import build_experiment_decisions
from b2b_saas_platform_analytics.validation import load_csv_tables


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate generated SaaS experiments.")
    parser.add_argument("--input", default="data/generated/default")
    parser.add_argument("--output", default="reports/generated/default/experiment_decisions.csv")
    args = parser.parse_args()
    result = build_experiment_decisions(load_csv_tables(args.input))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(f"Wrote {len(result)} experiment decisions to {output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
