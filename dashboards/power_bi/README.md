# Power BI implementation pack

This directory contains a build-ready semantic-model specification. A binary `.pbix` file is intentionally not committed because it is machine- and version-dependent.

Files:

- `model_spec.md` — fact tables, dimensions, grains and relationships;
- `measures.dax` — governed measures aligned with the Python and PostgreSQL definitions;
- `pages.md` — eight report pages, filters, visuals and decision use cases;
- `theme.json` — neutral portfolio theme;
- `validation_checklist.md` — reconciliation between Power BI, PostgreSQL and Python outputs.

Recommended source is PostgreSQL analytical views after running `py scripts/build_postgresql.py`. The included CSV reports may be used for an initial mock-up.
