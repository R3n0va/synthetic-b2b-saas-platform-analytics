# Verification evidence

The representative profile is generated from `config/profiles/smoke.yaml` with the baseline scenario and fixed seed `20260803`.

## Verified commands

```console
py -3.14 scripts/setup_environment.py
py scripts/run_sample.py
py scripts/run_tests.py
```

Equivalent direct Python commands:

```console
.venv\Scripts\python.exe -m b2b_saas_platform_analytics.cli run-all --config config/profiles/smoke.yaml --scenario config/scenarios/baseline.yaml --data-output data/generated/sample --report-output reports/generated/sample
.venv\Scripts\python.exe -m pytest -q
```

## Verified results

- 41 generated source tables;
- 56,791 generated rows;
- 531 Python quality checks;
- zero Python quality failures;
- 13 generated analytical reports;
- 253 passing automated tests;
- four latest-month accounts classified as renewal risk;
- reconciled monthly MRR bridge.

## Evidence files

- `data/samples/manifest.json` — generated table counts and fingerprints;
- `data/samples/effective_config.json` — effective merged profile and scenario;
- `reports/samples/source_validation.csv` — source-level controls;
- `reports/samples/report_manifest.json` — analytical output manifest;
- `reports/samples/executive_summary.json` — executive KPI snapshot;
- `reports/samples/mrr_bridge.csv` — recurring-revenue reconciliation;
- `reports/samples/experiment_decisions.csv` — experiment outcomes and decisions;
- `repository_manifest.json` — repository file inventory and SHA-256 hashes.

## PostgreSQL boundary

The PostgreSQL build requires a local server and is intentionally verified separately on the target computer. The loader creates the project schemas, applies primary and foreign keys, creates indexes, executes the SQL model and 50 controls, and records success or failure in `metadata.pipeline_runs`. This archive does not claim a PostgreSQL execution that was not performed in the current environment.

The committed evidence files are intentionally not overwritten by the routine sample command. Runtime verification output is written under the ignored `generated/sample` directories.
