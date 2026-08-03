from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .schema import TABLE_SCHEMAS


@dataclass
class ValidationResult:
    check_id: str
    table_name: str
    check_type: str
    severity: str
    passed: bool
    failure_count: int
    details: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _result(
    check_id: str,
    table_name: str,
    check_type: str,
    failures: int,
    details: str,
    severity: str = "error",
) -> ValidationResult:
    return ValidationResult(
        check_id=check_id,
        table_name=table_name,
        check_type=check_type,
        severity=severity,
        passed=failures == 0,
        failure_count=int(failures),
        details=details,
    )


def load_csv_tables(input_dir: str | Path) -> dict[str, pd.DataFrame]:
    input_path = Path(input_dir)
    tables: dict[str, pd.DataFrame] = {}
    for table_name in TABLE_SCHEMAS:
        path = input_path / f"{table_name}.csv"
        if not path.exists():
            tables[table_name] = pd.DataFrame(columns=TABLE_SCHEMAS[table_name]["columns"])
        else:
            tables[table_name] = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    return tables


def validate_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    results: list[ValidationResult] = []

    for table_name, schema in TABLE_SCHEMAS.items():
        frame = tables.get(table_name)
        expected_columns = list(schema["columns"])
        if frame is None:
            results.append(_result(f"{table_name}.exists", table_name, "table_exists", 1, "Table is missing."))
            continue
        missing_columns = sorted(set(expected_columns) - set(frame.columns))
        unexpected_columns = sorted(set(frame.columns) - set(expected_columns))
        results.append(
            _result(
                f"{table_name}.columns",
                table_name,
                "schema",
                len(missing_columns),
                f"Missing columns: {missing_columns}; unexpected columns: {unexpected_columns}",
            )
        )
        if missing_columns:
            continue

        for column, logical_type in schema["columns"].items():
            series = frame[column]
            non_null = series.dropna()
            failures = 0
            if logical_type == "integer":
                parsed = pd.to_numeric(non_null, errors="coerce")
                failures = int(parsed.isna().sum() + ((parsed.dropna() % 1) != 0).sum())
            elif logical_type == "decimal":
                failures = int(pd.to_numeric(non_null, errors="coerce").isna().sum())
            elif logical_type in {"date", "timestamp"}:
                failures = int(pd.to_datetime(non_null, errors="coerce").isna().sum())
            elif logical_type == "boolean":
                accepted = {"true", "false", "True", "False", "1", "0", True, False, 1, 0}
                failures = int((~non_null.isin(accepted)).sum())
            results.append(
                _result(
                    f"{table_name}.{column}.type",
                    table_name,
                    "type",
                    failures,
                    f"Column {column} conforms to logical type {logical_type}.",
                )
            )

        primary_key = schema.get("primary_key", [])
        if primary_key:
            null_pk = int(frame[primary_key].isna().any(axis=1).sum())
            duplicate_pk = int(frame.duplicated(primary_key, keep=False).sum())
            results.append(_result(f"{table_name}.pk_not_null", table_name, "primary_key", null_pk, f"Primary key {primary_key} is not null."))
            results.append(_result(f"{table_name}.pk_unique", table_name, "primary_key", duplicate_pk, f"Primary key {primary_key} is unique."))

    for table_name, schema in TABLE_SCHEMAS.items():
        frame = tables.get(table_name)
        if frame is None or frame.empty:
            continue
        for index, fk in enumerate(schema.get("foreign_keys", []), start=1):
            columns = fk["columns"]
            reference_table, reference_columns_raw = fk["references"].split("(", 1)
            reference_columns = reference_columns_raw.rstrip(")").split(",")
            parent = tables.get(reference_table)
            if parent is None or parent.empty or any(column not in frame for column in columns):
                failures = int(frame[columns].notna().all(axis=1).sum())
            else:
                child_keys = frame[columns].dropna().astype(str).agg("|".join, axis=1)
                parent_keys = set(parent[reference_columns].dropna().astype(str).agg("|".join, axis=1))
                failures = int((~child_keys.isin(parent_keys)).sum())
            results.append(
                _result(
                    f"{table_name}.fk_{index}", table_name, "foreign_key", failures,
                    f"Foreign key {columns} references {reference_table}({reference_columns}).",
                )
            )

    def business_check(
        check_id: str,
        table_name: str,
        predicate: Callable[[pd.DataFrame], pd.Series],
        details: str,
        severity: str = "error",
    ) -> None:
        frame = tables.get(table_name, pd.DataFrame())
        failures = int(predicate(frame).fillna(False).sum()) if not frame.empty else 0
        results.append(_result(check_id, table_name, "business_rule", failures, details, severity))

    business_check(
        "subscriptions.date_order", "subscriptions",
        lambda f: pd.to_datetime(f["trial_start_date"], errors="coerce").notna()
        & (pd.to_datetime(f["trial_start_date"], errors="coerce") > pd.to_datetime(f["subscription_start_date"], errors="coerce")),
        "Trial start cannot be after paid subscription start.",
    )
    business_check(
        "subscriptions.end_after_start", "subscriptions",
        lambda f: pd.to_datetime(f["ended_date"], errors="coerce").notna()
        & (pd.to_datetime(f["ended_date"], errors="coerce") < pd.to_datetime(f["subscription_start_date"], errors="coerce")),
        "Subscription end cannot precede subscription start.",
    )
    business_check(
        "subscription_items.valid_interval", "subscription_items",
        lambda f: pd.to_datetime(f["effective_end"], errors="coerce") < pd.to_datetime(f["effective_start"], errors="coerce"),
        "Subscription item effective end must not precede effective start.",
    )
    business_check(
        "subscription_items.non_negative_mrr", "subscription_items",
        lambda f: pd.to_numeric(f["mrr_eur"], errors="coerce") < 0,
        "Recurring item MRR cannot be negative.",
    )
    business_check(
        "invoices.arithmetic", "invoices",
        lambda f: (
            pd.to_numeric(f["subtotal_local"], errors="coerce")
            + pd.to_numeric(f["tax_local"], errors="coerce")
            - pd.to_numeric(f["total_local"], errors="coerce")
        ).abs() > 0.02,
        "Invoice subtotal plus tax must reconcile to total.",
    )
    business_check(
        "invoice_lines.non_negative", "invoice_lines",
        lambda f: pd.to_numeric(f["line_total_local"], errors="coerce") < 0,
        "Invoice line totals cannot be negative.",
    )
    business_check(
        "payment_attempts.positive_amount", "payment_attempts",
        lambda f: pd.to_numeric(f["amount_local"], errors="coerce") <= 0,
        "Payment attempt amount must be positive.",
    )
    business_check(
        "payments.positive_amount", "payments",
        lambda f: pd.to_numeric(f["amount_eur"], errors="coerce") <= 0,
        "Captured payment amount must be positive.",
    )
    business_check(
        "usage.non_negative", "account_usage_daily",
        lambda f: f[[
            "active_users", "sessions", "work_orders_created", "work_orders_completed",
            "automation_runs", "api_calls", "documents_uploaded", "feature_breadth",
        ]].apply(pd.to_numeric, errors="coerce").lt(0).any(axis=1),
        "Usage counts cannot be negative.",
    )
    business_check(
        "work_orders.completed_chronology", "work_orders",
        lambda f: pd.to_datetime(f["completed_at"], errors="coerce").notna()
        & (pd.to_datetime(f["completed_at"], errors="coerce") < pd.to_datetime(f["created_at"], errors="coerce")),
        "Completed work orders cannot complete before creation.",
    )
    business_check(
        "support.resolution_chronology", "support_tickets",
        lambda f: pd.to_datetime(f["resolved_at"], errors="coerce") < pd.to_datetime(f["created_at"], errors="coerce"),
        "Support tickets cannot resolve before creation.",
    )
    business_check(
        "health.score_range", "account_health_history",
        lambda f: ~pd.to_numeric(f["health_score"], errors="coerce").between(0, 100),
        "Account health score must be between 0 and 100.",
    )
    business_check(
        "nps.score_range", "nps_responses",
        lambda f: ~pd.to_numeric(f["nps_score"], errors="coerce").between(0, 10),
        "NPS score must be between 0 and 10.",
    )

    # Cross-table financial reconciliation.
    invoices = tables.get("invoices", pd.DataFrame())
    lines = tables.get("invoice_lines", pd.DataFrame())
    if not invoices.empty and not lines.empty:
        line_totals = lines.assign(
            line_total_numeric=pd.to_numeric(lines["line_total_local"], errors="coerce")
        ).groupby("invoice_id", as_index=False)["line_total_numeric"].sum()
        reconciled = invoices.merge(line_totals, on="invoice_id", how="left")
        failures = int((
            pd.to_numeric(reconciled["subtotal_local"], errors="coerce")
            - reconciled["line_total_numeric"].fillna(0)
        ).abs().gt(0.02).sum())
        results.append(_result("invoices.lines_reconcile", "invoices", "reconciliation", failures, "Invoice subtotal reconciles to invoice lines."))

    attempts = tables.get("payment_attempts", pd.DataFrame())
    payments = tables.get("payments", pd.DataFrame())
    if not attempts.empty and not payments.empty:
        succeeded = set(attempts.loc[attempts["attempt_status"] == "succeeded", "payment_attempt_id"])
        failures = int((~payments["payment_attempt_id"].isin(succeeded)).sum())
        results.append(_result("payments.successful_attempt", "payments", "reconciliation", failures, "Every captured payment references a successful payment attempt."))

    return pd.DataFrame([result.as_dict() for result in results])


def validation_passed(results: pd.DataFrame) -> bool:
    if results.empty:
        return False
    blocking = results[results["severity"] == "error"]
    return bool(blocking["passed"].all())
