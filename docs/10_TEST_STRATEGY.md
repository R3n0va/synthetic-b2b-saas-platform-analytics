# Test strategy

The automated suite contains 253 collected tests covering the repository as a governed analytical product rather than only isolated Python functions.

## Coverage areas

- configuration inheritance and scenario overrides;
- all 41 generated source tables;
- primary-key completeness and uniqueness;
- every governed foreign-key relationship;
- contract files against the Python schema registry;
- deterministic generation and dataframe fingerprints;
- financial arithmetic and MRR bridge reconciliation;
- retention, payment recovery and experiment decision outputs;
- all 40 governed metric definitions;
- all 41 catalogued business cases against implemented SQL views;
- all four experiment design specifications;
- PostgreSQL identifier and relationship helpers;
- negative corruption cases for duplicate keys and orphaned relationships;
- repository naming, runtime boundary and absence of container assets;
- repository manifest completeness and file hashes.

GitHub Actions runs linting, the complete test suite and the smoke-profile pipeline on supported Python versions.
