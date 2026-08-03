from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analytics import generate_reports
from .config import load_config
from .contracts import write_contracts
from .database import build_database
from .generator import generate_dataset, write_dataset
from .validation import load_csv_tables, validate_tables, validation_passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="saas-platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate source CSV tables.")
    generate.add_argument("--config", required=True)
    generate.add_argument("--scenario")
    generate.add_argument("--output", required=True)

    validate = subparsers.add_parser("validate", help="Validate generated source tables.")
    validate.add_argument("--input", required=True)
    validate.add_argument("--output")

    analyze = subparsers.add_parser("analyze", help="Generate analytical report pack.")
    analyze.add_argument("--config", required=True)
    analyze.add_argument("--scenario")
    analyze.add_argument("--input", required=True)
    analyze.add_argument("--output", required=True)

    run_all = subparsers.add_parser("run-all", help="Generate, validate and analyse a dataset.")
    run_all.add_argument("--config", required=True)
    run_all.add_argument("--scenario")
    run_all.add_argument("--data-output", required=True)
    run_all.add_argument("--report-output", required=True)

    db_build = subparsers.add_parser("db-build", help="Load generated CSV files into PostgreSQL and build analytical layers.")
    db_build.add_argument("--input", required=True)
    db_build.add_argument("--project-root", required=True)
    db_build.add_argument("--env-file")
    db_build.add_argument("--reset", action="store_true")

    contracts = subparsers.add_parser("write-contracts", help="Write YAML data contracts from the governed schema registry.")
    contracts.add_argument("--output", default="contracts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        config = load_config(args.config, args.scenario)
        dataset = generate_dataset(config)
        manifest = write_dataset(dataset, args.output)
        print(f"Generated {len(manifest['tables'])} tables and {manifest['total_rows']:,} rows.")
        return 0
    if args.command == "validate":
        results = validate_tables(load_csv_tables(args.input))
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            results.to_csv(args.output, index=False, lineterminator="\n")
        failures = results[~results["passed"]]
        print(f"Executed {len(results)} checks; {len(failures)} failed.")
        return 0 if validation_passed(results) else 1
    if args.command == "analyze":
        config = load_config(args.config, args.scenario)
        manifest = generate_reports(args.input, args.output, config)
        print(f"Generated {len(manifest['reports'])} reports.")
        return 0 if manifest["validation_passed"] else 1
    if args.command == "run-all":
        config = load_config(args.config, args.scenario)
        dataset = generate_dataset(config)
        data_manifest = write_dataset(dataset, args.data_output)
        results = validate_tables(dataset.tables)
        Path(args.report_output).mkdir(parents=True, exist_ok=True)
        results.to_csv(Path(args.report_output) / "source_validation.csv", index=False, lineterminator="\n")
        if not validation_passed(results):
            print(results[~results["passed"]].to_string(index=False))
            return 1
        report_manifest = generate_reports(args.data_output, args.report_output, config)
        print(
            f"Generated {len(data_manifest['tables'])} tables, {data_manifest['total_rows']:,} rows "
            f"and {len(report_manifest['reports'])} analytical reports."
        )
        return 0
    if args.command == "db-build":
        build_database(args.input, args.project_root, args.env_file, args.reset)
        print("PostgreSQL build completed successfully.")
        return 0
    if args.command == "write-contracts":
        write_contracts(args.output)
        print(f"Contracts written to {args.output}.")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
