from __future__ import annotations

import pytest

from b2b_saas_platform_analytics.database import (
    _cast_expression,
    _parse_reference,
    _safe_object_name,
    quote,
)


def test_identifier_quoting_escapes_double_quotes():
    assert quote('a"b') == '"a""b"'


def test_reference_parser_supports_composite_keys():
    table, columns = _parse_reference("parent(left_id, right_id)")
    assert table == "parent"
    assert columns == ["left_id", "right_id"]


def test_reference_parser_rejects_invalid_format():
    with pytest.raises(ValueError):
        _parse_reference("parent.left_id")


def test_database_object_names_remain_within_postgresql_limit():
    name = _safe_object_name("fk", "very_long_table_name" * 5, "very_long_column" * 5)
    assert len(name) <= 60


def test_integer_cast_accepts_nullable_pandas_decimal_format_without_rounding():
    expression = _cast_expression("previous_quantity", "integer")
    assert "numeric::bigint" in expression
    assert "^[+-]?[0-9]+([.]0+)?$" in expression
    assert "ELSE" in expression and "::bigint" in expression


def test_non_integer_casts_keep_direct_governed_postgresql_type():
    assert _cast_expression("amount_eur", "decimal") == (
        "NULLIF(BTRIM(\"amount_eur\"), '')::numeric(20, 6)"
    )


class _FakeCursor:
    def __init__(self, database_exists: bool):
        self.database_exists = database_exists
        self.statements: list[tuple[object, object | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement, parameters=None):
        self.statements.append((statement, parameters))

    def fetchone(self):
        return (1,) if self.database_exists else None


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


class _FakePsycopg:
    def __init__(self, database_exists: bool, error: Exception | None = None):
        self.cursor = _FakeCursor(database_exists)
        self.error = error
        self.connect_calls: list[dict[str, object]] = []

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return _FakeConnection(self.cursor)


def test_maintenance_connection_uses_postgres_by_default(monkeypatch):
    from b2b_saas_platform_analytics.database import _maintenance_connection_kwargs

    monkeypatch.delenv("PGMAINTENANCEDB", raising=False)
    result = _maintenance_connection_kwargs({"dbname": "target", "host": "localhost"})
    assert result == {"dbname": "postgres", "host": "localhost"}


def test_existing_target_database_is_not_recreated(monkeypatch):
    from b2b_saas_platform_analytics.database import _ensure_target_database

    monkeypatch.setenv("PGMAINTENANCEDB", "postgres")
    driver = _FakePsycopg(database_exists=True)
    created = _ensure_target_database(
        driver,
        {"host": "localhost", "port": 5432, "dbname": "synthetic_b2b_saas", "user": "postgres"},
    )

    assert created is False
    assert driver.connect_calls[0]["dbname"] == "postgres"
    assert driver.connect_calls[0]["autocommit"] is True
    assert len(driver.cursor.statements) == 1


def test_missing_target_database_is_created_safely(monkeypatch):
    from b2b_saas_platform_analytics.database import _ensure_target_database

    monkeypatch.setenv("PGMAINTENANCEDB", "postgres")
    driver = _FakePsycopg(database_exists=False)
    created = _ensure_target_database(
        driver,
        {"host": "localhost", "port": 5432, "dbname": 'saas"analytics', "user": "postgres"},
    )

    assert created is True
    create_statement = str(driver.cursor.statements[1][0])
    assert 'CREATE DATABASE "saas""analytics"' in create_statement
    assert "TEMPLATE template0" in create_statement


def test_database_creation_failure_returns_actionable_error(monkeypatch):
    from b2b_saas_platform_analytics.database import _ensure_target_database

    monkeypatch.setenv("PGMAINTENANCEDB", "postgres")
    driver = _FakePsycopg(database_exists=False, error=OSError("connection refused"))

    with pytest.raises(RuntimeError, match="CREATEDB permission"):
        _ensure_target_database(
            driver,
            {"host": "localhost", "port": 5432, "dbname": "synthetic_b2b_saas", "user": "postgres"},
        )
