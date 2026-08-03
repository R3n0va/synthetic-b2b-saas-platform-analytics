# Reproducibility

The generator uses a deterministic NumPy random generator. The seed is stored in the effective configuration written beside each generated dataset.

Every generated dataset contains:

- `manifest.json` with row counts, columns and dataframe fingerprints;
- `effective_config.json` with merged configuration and scenario values;
- one CSV per governed source table.

Re-running the same configuration and seed produces the same table contents and fingerprints. Changing a scenario modifies behaviour while preserving the schema and analytical pipeline.
