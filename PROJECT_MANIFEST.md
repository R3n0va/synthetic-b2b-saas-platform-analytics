# Project manifest

## Local execution

- `scripts/setup_environment.py` — creates the local Python virtual environment and installs dependencies.
- `scripts/run_sample.py` — regenerates, validates and analyses the representative sample.
- `scripts/run_tests.py` — executes the automated test suite and compile check.
- `scripts/run_default.py` — creates the default portfolio-size dataset and report pack.
- `scripts/build_postgresql.py` — builds the local PostgreSQL analytical model.

All execution entry points are Python files. Business transformations remain in Python and SQL. The repository contains no BAT, PowerShell, shell or container launch scripts.

## Implemented assets

- 41 governed source tables and YAML contracts;
- deterministic Python generator and CLI;
- 531 source and business-rule validations in the verified sample;
- PostgreSQL landing, core, marts, analytics and quality layers;
- 40 governed metric definitions;
- 41 catalogued business cases;
- 4 controlled experiment specifications and analysis;
- 13 generated analytical reports;
- 253 automated tests;
- 3 review notebooks;
- Power BI semantic-model, DAX, page, theme and validation pack.

## Technology boundary

The repository runs locally with Python, PostgreSQL and optional Power BI Desktop. It contains no Dockerfile, Compose file, container image or container runtime dependency.
