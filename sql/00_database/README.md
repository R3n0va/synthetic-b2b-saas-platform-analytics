# Database bootstrap

The Python loader reads the target database from `PGDATABASE`. When the database does not exist, it connects through `PGMAINTENANCEDB` with autocommit enabled and creates the target database using UTF-8 encoding. The configured role needs `CREATEDB` permission only for that first operation.

Existing databases are never dropped. The project build owns only the `metadata`, `landing`, `core`, `mart`, `analytics` and `quality` schemas inside the selected database. A reset drops and recreates those project schemas while leaving the PostgreSQL installation and unrelated databases unchanged.
