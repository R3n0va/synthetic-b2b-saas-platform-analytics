from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .schema import TABLE_SCHEMAS, postgres_type

_REFERENCE_PATTERN = re.compile(r"^(?P<table>[a-zA-Z_][a-zA-Z0-9_]*)\((?P<columns>[^)]+)\)$")


def quote(identifier: str) -> str:
    """Quote a PostgreSQL identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def _safe_object_name(prefix: str, *parts: str) -> str:
    raw = "_".join([prefix, *parts])
    if len(raw) <= 60:
        return raw
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{raw[:49]}_{digest}"


def _parse_reference(reference: str) -> tuple[str, list[str]]:
    match = _REFERENCE_PATTERN.fullmatch(reference.strip())
    if not match:
        raise ValueError(f"Unsupported foreign-key reference: {reference}")
    columns = [column.strip() for column in match.group("columns").split(",")]
    return match.group("table"), columns


def _connection_kwargs(env_file: str | Path | None = None) -> dict[str, Any]:
    if env_file:
        load_dotenv(env_file, override=True)
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "synthetic_b2b_saas"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
    }


def _maintenance_connection_kwargs(connection_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return connection settings for a database that is expected to exist."""
    maintenance = dict(connection_kwargs)
    maintenance["dbname"] = os.getenv("PGMAINTENANCEDB", "postgres")
    return maintenance


def _ensure_target_database(psycopg: Any, connection_kwargs: dict[str, Any]) -> bool:
    """Create the configured target database when it does not already exist.

    Database creation must run outside a transaction. The configured PostgreSQL
    role therefore needs CREATEDB permission only when the target database is
    absent. Existing databases are never recreated or dropped.
    """
    target_database = str(connection_kwargs["dbname"])
    maintenance_kwargs = _maintenance_connection_kwargs(connection_kwargs)

    try:
        with psycopg.connect(**maintenance_kwargs, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s;",
                    (target_database,),
                )
                if cursor.fetchone() is not None:
                    return False
                cursor.execute(
                    f"CREATE DATABASE {quote(target_database)} "
                    "WITH ENCODING 'UTF8' TEMPLATE template0;"
                )
                return True
    except Exception as exc:
        maintenance_database = maintenance_kwargs["dbname"]
        raise RuntimeError(
            f"Unable to verify or create PostgreSQL database '{target_database}' "
            f"through maintenance database '{maintenance_database}'. Ensure the "
            "configured role can connect to PostgreSQL and has CREATEDB permission, "
            "or create the target database manually."
        ) from exc


def _cast_expression(column: str, logical_type: str) -> str:
    raw = f"BTRIM({quote(column)})"
    source = f"NULLIF({raw}, '')"
    if logical_type == "string":
        return source
    if logical_type == "integer":
        # pandas serialises nullable integer columns as values such as ``0.0``
        # when the in-memory dtype is float because of missing values. Accept
        # only integer-equivalent decimal text and still fail on genuine
        # fractional values rather than silently rounding them.
        whole_number = r"^[+-]?[0-9]+([.]0+)?$"
        return (
            f"CASE WHEN {source} IS NULL THEN NULL "
            f"WHEN {raw} ~ '{whole_number}' THEN ({raw})::numeric::bigint "
            f"ELSE ({raw})::bigint END"
        )
    return f"{source}::{postgres_type(logical_type)}"


def execute_sql_file(cursor: Any, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    if sql.strip():
        cursor.execute(sql)


def _initialise_database(cursor: Any, reset: bool) -> None:
    if reset:
        cursor.execute(
            "DROP SCHEMA IF EXISTS analytics, mart, quality, core, landing, metadata CASCADE;"
        )
    cursor.execute(
        "CREATE SCHEMA IF NOT EXISTS metadata;"
        "CREATE SCHEMA IF NOT EXISTS landing;"
        "CREATE SCHEMA IF NOT EXISTS core;"
        "CREATE SCHEMA IF NOT EXISTS mart;"
        "CREATE SCHEMA IF NOT EXISTS analytics;"
        "CREATE SCHEMA IF NOT EXISTS quality;"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
            pipeline_run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            started_at timestamp NOT NULL DEFAULT current_timestamp,
            completed_at timestamp,
            status text NOT NULL,
            input_directory text NOT NULL,
            loaded_tables integer DEFAULT 0,
            loaded_rows bigint DEFAULT 0,
            error_message text
        );
        """
    )


def _load_source_tables(cursor: Any, input_path: Path) -> int:
    loaded_rows = 0
    for table_name, schema in TABLE_SCHEMAS.items():
        csv_path = input_path / f"{table_name}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing source file: {csv_path}")

        columns = list(schema["columns"])
        cursor.execute(f"DROP TABLE IF EXISTS landing.{quote(table_name)} CASCADE;")
        cursor.execute(
            f"CREATE TABLE landing.{quote(table_name)} ("
            + ", ".join(f"{quote(column)} text" for column in columns)
            + ");"
        )
        copy_sql = (
            f"COPY landing.{quote(table_name)} ("
            + ", ".join(quote(column) for column in columns)
            + ") FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '');"
        )
        with cursor.copy(copy_sql) as copy:
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                while chunk := handle.read(1024 * 1024):
                    copy.write(chunk)
        cursor.execute(f"SELECT count(*) FROM landing.{quote(table_name)};")
        loaded_rows += int(cursor.fetchone()[0])

        cursor.execute(f"DROP TABLE IF EXISTS core.{quote(table_name)} CASCADE;")
        typed_columns = ", ".join(
            f"{quote(column)} {postgres_type(logical_type)}"
            for column, logical_type in schema["columns"].items()
        )
        cursor.execute(f"CREATE TABLE core.{quote(table_name)} ({typed_columns});")
        select_list = ", ".join(
            f"{_cast_expression(column, logical_type)} AS {quote(column)}"
            for column, logical_type in schema["columns"].items()
        )
        cursor.execute(
            f"INSERT INTO core.{quote(table_name)} "
            f"SELECT {select_list} FROM landing.{quote(table_name)};"
        )
        primary_key = schema.get("primary_key", [])
        if primary_key:
            pk_columns = ", ".join(quote(column) for column in primary_key)
            constraint = _safe_object_name("pk", table_name)
            cursor.execute(
                f"ALTER TABLE core.{quote(table_name)} "
                f"ADD CONSTRAINT {quote(constraint)} PRIMARY KEY ({pk_columns});"
            )
    return loaded_rows


def _apply_relationships_and_indexes(cursor: Any) -> None:
    for table_name, schema in TABLE_SCHEMAS.items():
        for foreign_key in schema.get("foreign_keys", []):
            local_columns = list(foreign_key["columns"])
            reference_table, reference_columns = _parse_reference(foreign_key["references"])
            if len(local_columns) != len(reference_columns):
                raise ValueError(
                    f"Foreign-key column mismatch for {table_name}: {foreign_key}"
                )
            local_sql = ", ".join(quote(column) for column in local_columns)
            reference_sql = ", ".join(quote(column) for column in reference_columns)
            constraint = _safe_object_name("fk", table_name, *local_columns)
            index = _safe_object_name("idx", table_name, *local_columns)
            cursor.execute(
                f"ALTER TABLE core.{quote(table_name)} "
                f"ADD CONSTRAINT {quote(constraint)} FOREIGN KEY ({local_sql}) "
                f"REFERENCES core.{quote(reference_table)} ({reference_sql});"
            )
            cursor.execute(
                f"CREATE INDEX {quote(index)} ON core.{quote(table_name)} ({local_sql});"
            )


def _execute_model_sql(cursor: Any, project_root: Path) -> None:
    for directory in ["00_admin", "02_core", "03_marts", "04_analytics", "05_quality"]:
        for sql_file in sorted((project_root / "sql" / directory).glob("*.sql")):
            execute_sql_file(cursor, sql_file)


def build_database(
    input_dir: str | Path,
    project_root: str | Path,
    env_file: str | Path | None = None,
    reset: bool = False,
) -> None:
    """Load generated CSV files and build the complete PostgreSQL analytical model."""
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "psycopg is required for the PostgreSQL build. Install the project dependencies."
        ) from exc

    input_path = Path(input_dir)
    root = Path(project_root)
    connection_kwargs = _connection_kwargs(env_file)
    database_created = _ensure_target_database(psycopg, connection_kwargs)
    if database_created:
        print(f"Created PostgreSQL database '{connection_kwargs['dbname']}'.")

    with psycopg.connect(**connection_kwargs) as connection:
        with connection.cursor() as cursor:
            _initialise_database(cursor, reset)
            cursor.execute(
                "INSERT INTO metadata.pipeline_runs(status, input_directory) "
                "VALUES ('running', %s) RETURNING pipeline_run_id;",
                (str(input_path.resolve()),),
            )
            run_id = int(cursor.fetchone()[0])
        connection.commit()

        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    loaded_rows = _load_source_tables(cursor, input_path)
                    _apply_relationships_and_indexes(cursor)
                    _execute_model_sql(cursor, root)
                    cursor.execute(
                        "UPDATE metadata.pipeline_runs "
                        "SET completed_at = current_timestamp, status = 'succeeded', "
                        "loaded_tables = %s, loaded_rows = %s "
                        "WHERE pipeline_run_id = %s;",
                        (len(TABLE_SCHEMAS), loaded_rows, run_id),
                    )
        except Exception as exc:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE metadata.pipeline_runs "
                    "SET completed_at = current_timestamp, status = 'failed', error_message = %s "
                    "WHERE pipeline_run_id = %s;",
                    (str(exc), run_id),
                )
            connection.commit()
            raise
