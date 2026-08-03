from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statistics import NormalDist

from .schema import TABLE_SCHEMAS
from .utils import iter_months, month_start, write_json
from .validation import load_csv_tables, validate_tables, validation_passed


def _date(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_datetime(frame[column], errors="coerce")


def _number(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def build_mrr_snapshot(tables: dict[str, pd.DataFrame], config: dict[str, Any]) -> pd.DataFrame:
    items = tables["subscription_items"].copy()
    subscriptions = tables["subscriptions"][["subscription_id", "account_id"]].copy()
    accounts = tables["accounts"][[
        "account_id", "country_code", "region_id", "segment", "sales_motion", "acquisition_channel"
    ]].copy()
    if items.empty:
        return pd.DataFrame(columns=[
            "month", "subscription_id", "account_id", "mrr_eur", "country_code", "region_id",
            "segment", "sales_motion", "acquisition_channel",
        ])
    items["effective_start"] = _date(items, "effective_start")
    items["effective_end"] = _date(items, "effective_end")
    items["mrr_eur"] = _number(items, "mrr_eur").fillna(0.0)
    rows: list[dict[str, Any]] = []
    for row in items.itertuples(index=False):
        for month in iter_months(row.effective_start, row.effective_end):
            rows.append(
                {
                    "month": month,
                    "subscription_id": row.subscription_id,
                    "mrr_eur": float(row.mrr_eur),
                    "item_type": row.item_type,
                }
            )
    snapshot = pd.DataFrame(rows)
    snapshot = snapshot.groupby(["month", "subscription_id"], as_index=False).agg(
        mrr_eur=("mrr_eur", "sum"), recurring_items=("item_type", "count")
    )
    snapshot = snapshot.merge(subscriptions, on="subscription_id", how="left").merge(accounts, on="account_id", how="left")
    return snapshot


def build_mrr_bridge(snapshot: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if snapshot.empty:
        empty = pd.DataFrame(columns=["month", "opening_mrr", "new_mrr", "expansion_mrr", "contraction_mrr", "churned_mrr", "reactivation_mrr", "closing_mrr"])
        return empty, pd.DataFrame()
    start = month_start(config["project"]["history_start"])
    end = month_start(config["project"]["history_end"])
    months = pd.DataFrame({"month": list(iter_months(start, end))})
    accounts = snapshot["account_id"].dropna().unique()
    grid = pd.MultiIndex.from_product([accounts, months["month"]], names=["account_id", "month"]).to_frame(index=False)
    account_mrr = snapshot.groupby(["account_id", "month"], as_index=False)["mrr_eur"].sum()
    account_mrr = grid.merge(account_mrr, on=["account_id", "month"], how="left").fillna({"mrr_eur": 0.0})
    account_mrr = account_mrr.sort_values(["account_id", "month"])
    account_mrr["previous_mrr"] = account_mrr.groupby("account_id")["mrr_eur"].shift(1).fillna(0.0)
    account_mrr["ever_active_before"] = account_mrr.groupby("account_id")["previous_mrr"].cummax() > 0
    delta = account_mrr["mrr_eur"] - account_mrr["previous_mrr"]
    account_mrr["movement_type"] = "no_change"
    account_mrr.loc[(account_mrr["previous_mrr"] == 0) & (account_mrr["mrr_eur"] > 0) & ~account_mrr["ever_active_before"], "movement_type"] = "new"
    account_mrr.loc[(account_mrr["previous_mrr"] == 0) & (account_mrr["mrr_eur"] > 0) & account_mrr["ever_active_before"], "movement_type"] = "reactivation"
    account_mrr.loc[(account_mrr["previous_mrr"] > 0) & (account_mrr["mrr_eur"] == 0), "movement_type"] = "churn"
    account_mrr.loc[(account_mrr["previous_mrr"] > 0) & (account_mrr["mrr_eur"] > account_mrr["previous_mrr"]), "movement_type"] = "expansion"
    account_mrr.loc[(account_mrr["mrr_eur"] > 0) & (account_mrr["mrr_eur"] < account_mrr["previous_mrr"]), "movement_type"] = "contraction"
    account_mrr["movement_mrr"] = delta

    bridge_rows = []
    for month, group in account_mrr.groupby("month"):
        opening = float(group["previous_mrr"].sum())
        closing = float(group["mrr_eur"].sum())
        bridge_rows.append(
            {
                "month": month,
                "opening_mrr": round(opening, 2),
                "new_mrr": round(group.loc[group["movement_type"] == "new", "movement_mrr"].sum(), 2),
                "expansion_mrr": round(group.loc[group["movement_type"] == "expansion", "movement_mrr"].sum(), 2),
                "contraction_mrr": round(group.loc[group["movement_type"] == "contraction", "movement_mrr"].sum(), 2),
                "churned_mrr": round(group.loc[group["movement_type"] == "churn", "movement_mrr"].sum(), 2),
                "reactivation_mrr": round(group.loc[group["movement_type"] == "reactivation", "movement_mrr"].sum(), 2),
                "closing_mrr": round(closing, 2),
                "bridge_reconciliation": round(closing - (
                    opening
                    + group.loc[group["movement_type"] == "new", "movement_mrr"].sum()
                    + group.loc[group["movement_type"] == "expansion", "movement_mrr"].sum()
                    + group.loc[group["movement_type"] == "contraction", "movement_mrr"].sum()
                    + group.loc[group["movement_type"] == "churn", "movement_mrr"].sum()
                    + group.loc[group["movement_type"] == "reactivation", "movement_mrr"].sum()
                ), 6),
            }
        )
    return pd.DataFrame(bridge_rows), account_mrr


def build_retention(snapshot: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if snapshot.empty:
        return pd.DataFrame(), pd.DataFrame()
    account_month = snapshot.groupby(["account_id", "month"], as_index=False)["mrr_eur"].sum()
    first_month = account_month.loc[account_month["mrr_eur"] > 0].groupby("account_id", as_index=False)["month"].min().rename(columns={"month": "cohort_month"})
    account_month = account_month.merge(first_month, on="account_id", how="left")
    account_month["cohort_age"] = (
        (account_month["month"].dt.year - account_month["cohort_month"].dt.year) * 12
        + account_month["month"].dt.month - account_month["cohort_month"].dt.month
    )
    cohort_base = account_month[account_month["cohort_age"] == 0].groupby("cohort_month", as_index=False).agg(
        cohort_accounts=("account_id", "nunique"), cohort_mrr=("mrr_eur", "sum")
    )
    cohort = account_month.groupby(["cohort_month", "cohort_age"], as_index=False).agg(
        retained_accounts=("account_id", lambda s: int(s.nunique())), retained_mrr=("mrr_eur", "sum")
    ).merge(cohort_base, on="cohort_month", how="left")
    cohort["logo_retention"] = cohort["retained_accounts"] / cohort["cohort_accounts"]
    cohort["revenue_retention"] = cohort["retained_mrr"] / cohort["cohort_mrr"]

    monthly = []
    for month in sorted(account_month["month"].unique()):
        current = account_month[account_month["month"] == month]
        previous_month = pd.Timestamp(month) - pd.DateOffset(months=1)
        previous = account_month[account_month["month"] == previous_month][["account_id", "mrr_eur"]].rename(columns={"mrr_eur": "previous_mrr"})
        merged = previous.merge(current[["account_id", "mrr_eur"]], on="account_id", how="left").fillna({"mrr_eur": 0.0})
        opening = merged["previous_mrr"].sum()
        churn = (merged["previous_mrr"] - merged["mrr_eur"]).clip(lower=0).sum()
        expansion = (merged["mrr_eur"] - merged["previous_mrr"]).clip(lower=0).sum()
        monthly.append(
            {
                "month": month,
                "gross_revenue_retention": (opening - churn) / opening if opening else np.nan,
                "net_revenue_retention": (opening - churn + expansion) / opening if opening else np.nan,
                "opening_mrr": opening,
            }
        )
    return cohort, pd.DataFrame(monthly)


def build_sales_funnel(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    accounts = tables["accounts"]
    leads = tables["leads"]
    opportunities = tables["opportunities"]
    subscriptions = tables["subscriptions"]
    base = accounts.groupby(["country_code", "region_id", "sales_motion", "acquisition_channel"], as_index=False).agg(
        accounts=("account_id", "nunique")
    )
    lead_summary = leads.merge(accounts[["account_id", "country_code", "region_id", "sales_motion", "acquisition_channel"]], on="account_id", how="left").groupby(
        ["country_code", "region_id", "sales_motion", "acquisition_channel"], as_index=False
    ).agg(
        leads=("lead_id", "nunique"),
        mqls=("mql_at", lambda s: int(s.notna().sum())),
        sqls=("sql_at", lambda s: int(s.notna().sum())),
    )
    if opportunities.empty:
        opportunity_summary = pd.DataFrame(columns=["country_code", "region_id", "sales_motion", "acquisition_channel", "opportunities", "won_opportunities", "pipeline_arr_eur"])
    else:
        opportunity_summary = opportunities.merge(accounts[["account_id", "country_code", "region_id", "sales_motion", "acquisition_channel"]], on="account_id", how="left")
        opportunity_summary["expected_arr_eur"] = _number(opportunity_summary, "expected_arr_eur").fillna(0)
        opportunity_summary = opportunity_summary.groupby(["country_code", "region_id", "sales_motion", "acquisition_channel"], as_index=False).agg(
            opportunities=("opportunity_id", "nunique"), won_opportunities=("status", lambda s: int((s == "won").sum())), pipeline_arr_eur=("expected_arr_eur", "sum")
        )
    paid = subscriptions.merge(accounts[["account_id", "country_code", "region_id", "sales_motion", "acquisition_channel"]], on="account_id", how="left").groupby(
        ["country_code", "region_id", "sales_motion", "acquisition_channel"], as_index=False
    ).agg(paid_accounts=("account_id", "nunique"))
    funnel = base.merge(lead_summary, on=["country_code", "region_id", "sales_motion", "acquisition_channel"], how="left").merge(
        opportunity_summary, on=["country_code", "region_id", "sales_motion", "acquisition_channel"], how="left"
    ).merge(paid, on=["country_code", "region_id", "sales_motion", "acquisition_channel"], how="left").fillna(0)
    funnel["lead_to_mql"] = np.where(funnel["leads"] > 0, funnel["mqls"] / funnel["leads"], np.nan)
    funnel["mql_to_sql"] = np.where(funnel["mqls"] > 0, funnel["sqls"] / funnel["mqls"], np.nan)
    funnel["opportunity_win_rate"] = np.where(funnel["opportunities"] > 0, funnel["won_opportunities"] / funnel["opportunities"], np.nan)
    funnel["account_to_paid"] = np.where(funnel["accounts"] > 0, funnel["paid_accounts"] / funnel["accounts"], np.nan)
    return funnel


def build_payment_recovery(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    attempts = tables["payment_attempts"].copy()
    invoices = tables["invoices"][["invoice_id", "account_id", "invoice_date", "total_eur", "country_code"]].copy() if "country_code" in tables["invoices"].columns else tables["invoices"][["invoice_id", "account_id", "invoice_date", "total_eur"]].copy()
    accounts = tables["accounts"][["account_id", "country_code", "segment"]]
    if attempts.empty:
        return pd.DataFrame()
    attempts["attempt_number"] = _number(attempts, "attempt_number")
    attempts["attempt_month"] = _date(attempts, "attempt_at").dt.to_period("M").dt.to_timestamp()
    first = attempts.sort_values(["invoice_id", "attempt_number"]).groupby("invoice_id", as_index=False).first()
    outcome = attempts.groupby("invoice_id", as_index=False).agg(
        attempt_count=("payment_attempt_id", "count"), eventually_succeeded=("attempt_status", lambda s: int((s == "succeeded").any()))
    )
    base = first[["invoice_id", "attempt_month", "attempt_status", "failure_reason"]].rename(columns={"attempt_status": "first_attempt_status"}).merge(outcome, on="invoice_id").merge(
        tables["invoices"][["invoice_id", "account_id", "total_eur"]], on="invoice_id", how="left"
    ).merge(accounts, on="account_id", how="left")
    base["total_eur"] = _number(base, "total_eur").fillna(0)
    failed = base[base["first_attempt_status"] == "failed"].copy()
    return failed.groupby(["attempt_month", "country_code", "segment"], as_index=False).agg(
        failed_invoices=("invoice_id", "nunique"), recovered_invoices=("eventually_succeeded", "sum"),
        failed_value_eur=("total_eur", "sum"), recovered_value_eur=("total_eur", lambda s: s[failed.loc[s.index, "eventually_succeeded"] == 1].sum()),
        average_attempts=("attempt_count", "mean")
    ).assign(recovery_rate=lambda f: f["recovered_invoices"] / f["failed_invoices"])


def build_product_adoption(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    usage = tables["account_usage_daily"].copy()
    accounts = tables["accounts"][["account_id", "country_code", "region_id", "segment"]]
    if usage.empty:
        return pd.DataFrame()
    usage["activity_month"] = _date(usage, "activity_date").dt.to_period("M").dt.to_timestamp()
    for column in ["active_users", "sessions", "work_orders_created", "work_orders_completed", "automation_runs", "api_calls", "feature_breadth"]:
        usage[column] = _number(usage, column).fillna(0)
    monthly = usage.groupby(["account_id", "activity_month"], as_index=False).agg(
        active_users=("active_users", "max"), sessions=("sessions", "sum"), work_orders_created=("work_orders_created", "sum"),
        work_orders_completed=("work_orders_completed", "sum"), automation_runs=("automation_runs", "sum"),
        api_calls=("api_calls", "sum"), feature_breadth=("feature_breadth", "max")
    ).merge(accounts, on="account_id", how="left")
    monthly["work_order_completion_rate"] = np.where(monthly["work_orders_created"] > 0, monthly["work_orders_completed"] / monthly["work_orders_created"], np.nan)
    monthly["automation_adopted"] = monthly["automation_runs"] > 0
    monthly["api_adopted"] = monthly["api_calls"] > 0
    return monthly.groupby(["activity_month", "country_code", "region_id", "segment"], as_index=False).agg(
        active_accounts=("account_id", "nunique"), active_users=("active_users", "sum"), sessions=("sessions", "sum"),
        work_orders_created=("work_orders_created", "sum"), work_order_completion_rate=("work_order_completion_rate", "mean"),
        automation_adoption_rate=("automation_adopted", "mean"), api_adoption_rate=("api_adopted", "mean"),
        average_feature_breadth=("feature_breadth", "mean")
    )


def build_account_health(tables: dict[str, pd.DataFrame], snapshot: pd.DataFrame) -> pd.DataFrame:
    health = tables["account_health_history"].copy()
    if health.empty:
        return pd.DataFrame()
    health["health_month"] = _date(health, "health_month")
    for column in ["health_score", "usage_score", "support_score", "payment_score", "relationship_score"]:
        health[column] = _number(health, column)
    mrr = snapshot.groupby(["account_id", "month"], as_index=False)["mrr_eur"].sum()
    result = health.merge(mrr, left_on=["account_id", "health_month"], right_on=["account_id", "month"], how="left").drop(columns=["month"], errors="ignore")
    result["mrr_eur"] = result["mrr_eur"].fillna(0)
    return result


def build_country_performance(tables: dict[str, pd.DataFrame], snapshot: pd.DataFrame) -> pd.DataFrame:
    accounts = tables["accounts"][["account_id", "country_code", "region_id", "segment"]]
    latest_month = snapshot["month"].max() if not snapshot.empty else None
    current = snapshot[snapshot["month"] == latest_month] if latest_month is not None else snapshot
    current_summary = current.groupby(["country_code", "region_id"], as_index=False).agg(
        active_accounts=("account_id", "nunique"), mrr_eur=("mrr_eur", "sum")
    ) if not current.empty else pd.DataFrame(columns=["country_code", "region_id", "active_accounts", "mrr_eur"])
    invoices = tables["invoices"].merge(accounts, on="account_id", how="left")
    invoices["total_eur"] = _number(invoices, "total_eur").fillna(0)
    invoice_summary = invoices.groupby(["country_code", "region_id"], as_index=False).agg(
        invoiced_revenue_eur=("total_eur", "sum"), invoices=("invoice_id", "nunique"),
        paid_invoice_rate=("invoice_status", lambda s: float((s == "paid").mean()))
    ) if not invoices.empty else pd.DataFrame(columns=["country_code", "region_id", "invoiced_revenue_eur", "invoices", "paid_invoice_rate"])
    return current_summary.merge(invoice_summary, on=["country_code", "region_id"], how="outer").fillna(0)


def build_experiment_decisions(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    assignments = tables["experiment_assignments"]
    exposures = tables["experiment_exposures"]
    outcomes = tables["experiment_outcomes"]
    experiments = tables["experiments"]
    if assignments.empty or outcomes.empty:
        return pd.DataFrame()
    data = assignments.merge(exposures[["assignment_id", "exposure_id"]], on="assignment_id", how="inner").merge(outcomes, on="assignment_id", how="inner")
    data["primary_outcome"] = _number(data, "primary_outcome")
    data["guardrail_outcome"] = _number(data, "guardrail_outcome")
    data["revenue_outcome_eur"] = _number(data, "revenue_outcome_eur")
    rows = []
    for experiment_id, group in data.groupby("experiment_id"):
        control = group[group["variant"] == "control"]["primary_outcome"].dropna()
        treatment = group[group["variant"] == "treatment"]["primary_outcome"].dropna()
        if len(control) < 2 or len(treatment) < 2:
            continue
        effect = treatment.mean() - control.mean()
        se = math.sqrt(treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control))
        z = effect / se if se > 0 else 0.0
        p_value = 2 * (1 - NormalDist().cdf(abs(z))) if se > 0 else 1.0
        lower = effect - 1.96 * se
        upper = effect + 1.96 * se
        guardrail_control = group[group["variant"] == "control"]["guardrail_outcome"].mean()
        guardrail_treatment = group[group["variant"] == "treatment"]["guardrail_outcome"].mean()
        revenue_effect = group[group["variant"] == "treatment"]["revenue_outcome_eur"].mean() - group[group["variant"] == "control"]["revenue_outcome_eur"].mean()
        definition = experiments.loc[experiments["experiment_id"] == experiment_id].iloc[0]
        mde = float(definition["minimum_detectable_effect"])
        if p_value < 0.05 and effect > 0 and lower > -mde * 0.25:
            decision = "LAUNCH"
        elif p_value < 0.05 and effect < 0:
            decision = "DO NOT LAUNCH"
        else:
            decision = "INCONCLUSIVE"
        rows.append(
            {
                "experiment_id": experiment_id,
                "experiment_name": definition["experiment_name"],
                "control_n": len(control), "treatment_n": len(treatment),
                "control_mean": control.mean(), "treatment_mean": treatment.mean(),
                "absolute_effect": effect,
                "relative_effect": effect / control.mean() if control.mean() else np.nan,
                "ci_lower": lower, "ci_upper": upper, "p_value": p_value,
                "guardrail_control": guardrail_control, "guardrail_treatment": guardrail_treatment,
                "average_revenue_effect_eur": revenue_effect, "decision": decision,
            }
        )
    return pd.DataFrame(rows)


def build_unit_economics(tables: dict[str, pd.DataFrame], snapshot: pd.DataFrame) -> pd.DataFrame:
    campaigns = tables["marketing_campaigns"].copy()
    accounts = tables["accounts"][["account_id", "country_code", "acquisition_channel", "created_at"]]
    subscriptions = tables["subscriptions"][["account_id", "subscription_start_date"]]
    if campaigns.empty:
        return pd.DataFrame()
    campaigns["month"] = _date(campaigns, "start_date").dt.to_period("M").dt.to_timestamp()
    campaigns["spend_eur"] = _number(campaigns, "spend_eur").fillna(0)
    spend = campaigns.groupby(["month", "country_code", "channel"], as_index=False)["spend_eur"].sum()
    acquired = accounts.merge(subscriptions, on="account_id", how="inner")
    acquired["month"] = _date(acquired, "subscription_start_date").dt.to_period("M").dt.to_timestamp()
    acquired = acquired.groupby(["month", "country_code", "acquisition_channel"], as_index=False).agg(new_customers=("account_id", "nunique"))
    result = spend.merge(acquired, left_on=["month", "country_code", "channel"], right_on=["month", "country_code", "acquisition_channel"], how="left")
    result["new_customers"] = result["new_customers"].fillna(0)
    result["cac_eur"] = np.where(result["new_customers"] > 0, result["spend_eur"] / result["new_customers"], np.nan)
    return result.drop(columns=["acquisition_channel"], errors="ignore")


def write_markdown_table(frame: pd.DataFrame, path: Path, title: str, intro: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[column]):
            display[column] = display[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].round(4)
    body = f"# {title}\n\n"
    if intro:
        body += intro.strip() + "\n\n"
    body += display.to_markdown(index=False) if not display.empty else "No records."
    body += "\n"
    path.write_text(body, encoding="utf-8", newline="\n")


def generate_reports(
    input_dir: str | Path,
    report_dir: str | Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    output = Path(report_dir)
    output.mkdir(parents=True, exist_ok=True)
    tables = load_csv_tables(input_dir)
    validation = validate_tables(tables)
    snapshot = build_mrr_snapshot(tables, config)
    bridge, movements = build_mrr_bridge(snapshot, config)
    cohorts, retention = build_retention(snapshot)
    sales_funnel = build_sales_funnel(tables)
    payment_recovery = build_payment_recovery(tables)
    adoption = build_product_adoption(tables)
    account_health = build_account_health(tables, snapshot)
    country_performance = build_country_performance(tables, snapshot)
    experiment_decisions = build_experiment_decisions(tables)
    unit_economics = build_unit_economics(tables, snapshot)

    outputs = {
        "mrr_snapshot": snapshot,
        "mrr_bridge": bridge,
        "account_mrr_movements": movements,
        "cohort_retention": cohorts,
        "revenue_retention": retention,
        "sales_funnel": sales_funnel,
        "payment_recovery": payment_recovery,
        "product_adoption": adoption,
        "account_health": account_health,
        "country_performance": country_performance,
        "experiment_decisions": experiment_decisions,
        "unit_economics": unit_economics,
        "data_quality_results": validation,
    }
    manifest = {"reports": {}, "validation_passed": validation_passed(validation)}
    for name, frame in outputs.items():
        path = output / f"{name}.csv"
        frame.to_csv(path, index=False, lineterminator="\n")
        manifest["reports"][name] = {"file": path.name, "rows": int(len(frame))}

    latest_bridge = bridge.iloc[-1] if not bridge.empty else None
    active_accounts = int(snapshot.loc[snapshot["month"] == snapshot["month"].max(), "account_id"].nunique()) if not snapshot.empty else 0
    latest_nrr = float(retention.dropna(subset=["net_revenue_retention"]).iloc[-1]["net_revenue_retention"]) if not retention.dropna(subset=["net_revenue_retention"]).empty else float("nan")
    failed = tables["payment_attempts"]
    failed_count = int((failed["attempt_status"] == "failed").sum()) if not failed.empty else 0
    executive = {
        "reporting_month": str(latest_bridge["month"].date()) if latest_bridge is not None else None,
        "active_accounts": active_accounts,
        "closing_mrr_eur": round(float(latest_bridge["closing_mrr"]), 2) if latest_bridge is not None else 0.0,
        "arr_eur": round(float(latest_bridge["closing_mrr"] * 12), 2) if latest_bridge is not None else 0.0,
        "net_revenue_retention": round(latest_nrr, 4) if not math.isnan(latest_nrr) else None,
        "failed_payment_attempts": failed_count,
        "accounts_at_risk": int((account_health.loc[account_health["health_month"] == account_health["health_month"].max(), "renewal_risk_flag"].astype(str).str.lower() == "true").sum()) if not account_health.empty else 0,
        "quality_checks": int(len(validation)),
        "quality_failures": int((~validation["passed"]).sum()),
    }
    write_json(output / "executive_summary.json", executive)
    executive_md = "# Executive SaaS Summary\n\n"
    executive_md += "| Metric | Value |\n|---|---:|\n"
    for key, value in executive.items():
        executive_md += f"| {key.replace('_', ' ').title()} | {value} |\n"
    executive_md += "\n## Management interpretation\n\n"
    executive_md += "The report pack separates recurring-revenue movements, customer retention, acquisition efficiency, product adoption, payment recovery and renewal risk. Each KPI can be traced to generated source records and governed definitions.\n"
    (output / "executive_summary.md").write_text(executive_md, encoding="utf-8", newline="\n")

    write_markdown_table(bridge.tail(18), output / "mrr_bridge.md", "MRR Bridge", "Monthly recurring-revenue movement and reconciliation.")
    write_markdown_table(country_performance.sort_values("mrr_eur", ascending=False), output / "country_performance.md", "Country Performance")
    write_markdown_table(experiment_decisions, output / "experiment_decisions.md", "Experiment Decisions")
    write_markdown_table(validation[~validation["passed"]], output / "data_quality_failures.md", "Data Quality Failures")
    write_json(output / "report_manifest.json", manifest)
    return manifest
