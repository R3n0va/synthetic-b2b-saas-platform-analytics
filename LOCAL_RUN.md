# Local run

## Prerequisites

- Windows 10 or 11;
- Python 3.14 installed with the `py` launcher;
- PostgreSQL installed locally only when the SQL model is required;
- Power BI Desktop only when building the dashboard.

No Docker, Docker Compose, WSL or other container runtime is required.

## 1. Create the Python environment

```console
py -3.14 scripts/setup_environment.py
```

This creates `.venv` and installs the project package and test dependencies.

## 2. Verify the representative sample

```console
py scripts/run_sample.py
py scripts/run_tests.py
```

## 3. Generate the full portfolio-size dataset

```console
py scripts/run_default.py
```

Generated source data is written to `data/generated/default`. Analytical reports are written to `reports/generated/default`.

## 4. Build PostgreSQL layers

Copy `.env.example` to `.env` and enter the local PostgreSQL credentials:

```console
copy .env.example .env
notepad .env
```

Then run:

```console
py scripts/build_postgresql.py
```

The script automatically uses `data/generated/default` when available and otherwise uses `data/generated/sample`. An explicit source can be selected with `--input`:

```console
py scripts/build_postgresql.py --input data/generated/sample
```

If `PGDATABASE` does not exist, the loader connects through `PGMAINTENANCEDB` and creates it automatically. The configured role therefore needs `CREATEDB` permission only for the first build. Existing databases are never dropped; `--reset` rebuilds only the project schemas inside the selected database.

## Direct module execution

The Python entry scripts are convenience entry points. Every operation can also be called through the package CLI:

```console
.venv\Scripts\python.exe -m b2b_saas_platform_analytics.cli --help
```
