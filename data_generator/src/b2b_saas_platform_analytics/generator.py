from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .schema import TABLE_SCHEMAS
from .utils import (
    clamp,
    dataframe_fingerprint,
    iter_months,
    month_end,
    month_start,
    prefixed_id,
    random_date,
    weighted_choice,
    write_json,
)


@dataclass
class GeneratedDataset:
    tables: dict[str, pd.DataFrame]
    internal: dict[str, Any]


COUNTRY_NAMES = {
    "DE": "Germany", "AT": "Austria", "CH": "Switzerland", "NL": "Netherlands",
    "BE": "Belgium", "FR": "France", "GB": "United Kingdom", "IE": "Ireland",
    "ES": "Spain", "IT": "Italy", "SE": "Sweden", "DK": "Denmark", "NO": "Norway",
    "PL": "Poland", "CZ": "Czechia",
}
LANGUAGES = {
    "DE": "de", "AT": "de", "CH": "de", "NL": "nl", "BE": "fr", "FR": "fr",
    "GB": "en", "IE": "en", "ES": "es", "IT": "it", "SE": "sv", "DK": "da",
    "NO": "no", "PL": "pl", "CZ": "cs",
}
CURRENCY_NAMES = {
    "EUR": "Euro", "GBP": "Pound sterling", "CHF": "Swiss franc", "SEK": "Swedish krona",
    "DKK": "Danish krone", "NOK": "Norwegian krone", "PLN": "Polish zloty", "CZK": "Czech koruna",
}
FX_BASE = {"EUR": 1.0, "GBP": 1.17, "CHF": 1.04, "SEK": 0.088, "DKK": 0.134, "NOK": 0.086, "PLN": 0.23, "CZK": 0.040}
PLAN_ORDER = ["Starter", "Professional", "Business", "Enterprise"]
PLAN_BY_SEGMENT = {
    "micro": ["Starter", "Starter", "Professional"],
    "small": ["Starter", "Professional", "Professional"],
    "medium": ["Professional", "Business", "Business"],
    "mid_market": ["Business", "Business", "Enterprise"],
    "enterprise": ["Enterprise", "Enterprise", "Business"],
}
ROLE_WEIGHTS = {
    "administrator": 0.08, "dispatcher": 0.20, "field_worker": 0.57,
    "finance": 0.06, "manager": 0.07, "external_contractor": 0.02,
}
FEATURES = [
    ("work_order_created", "work_orders"), ("work_order_completed", "work_orders"),
    ("schedule_viewed", "scheduling"), ("mobile_check_in", "mobile"),
    ("document_uploaded", "documents"), ("automation_run", "automation"),
    ("dashboard_viewed", "analytics"), ("integration_sync", "integrations"),
    ("customer_signature", "customer_portal"), ("api_request", "api"),
]


def _iso_date(value: pd.Timestamp | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _iso_ts(value: pd.Timestamp | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat(sep=" ")


def _scenario_adjustments(config: dict[str, Any]) -> dict[str, float]:
    return config.get("scenario", {}).get("adjustments", {}) or {}


def _fx_lookup(fx_rates: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], float]:
    return {
        (row.currency_code, pd.Timestamp(row.rate_date)): float(row.eur_rate)
        for row in fx_rates.itertuples(index=False)
    }


def _nearest_month_rate(
    lookup: dict[tuple[str, pd.Timestamp], float], currency: str, date: pd.Timestamp
) -> float:
    if currency == "EUR":
        return 1.0
    return lookup[(currency, month_start(date))]


def generate_reference(config: dict[str, Any], rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    geo = config["geography"]["countries"]
    regions = sorted({values["region"] for values in geo.values()})
    region_rows = [
        {
            "region_id": region.lower().replace(" ", "_"),
            "region_name": region,
            "commercial_owner": f"Regional Team {index + 1}",
        }
        for index, region in enumerate(regions)
    ]
    region_map = {row["region_name"]: row["region_id"] for row in region_rows}

    country_rows = []
    currencies = set()
    for code, values in geo.items():
        currencies.add(values["currency"])
        country_rows.append(
            {
                "country_code": code,
                "country_name": COUNTRY_NAMES[code],
                "region_id": region_map[values["region"]],
                "currency_code": values["currency"],
                "vat_rate": values["vat_rate"],
                "language_code": LANGUAGES[code],
            }
        )
    currency_rows = [
        {"currency_code": code, "currency_name": CURRENCY_NAMES[code], "minor_units": 2}
        for code in sorted(currencies)
    ]

    start = month_start(config["project"]["history_start"])
    end = month_start(config["project"]["history_end"])
    fx_rows = []
    for currency in sorted(currencies):
        rate = FX_BASE[currency]
        for month in iter_months(start, end):
            if currency != "EUR":
                rate *= float(np.exp(rng.normal(0.0, 0.018)))
                rate = clamp(rate, FX_BASE[currency] * 0.75, FX_BASE[currency] * 1.25)
            fx_rows.append(
                {"rate_date": _iso_date(month), "currency_code": currency, "eur_rate": round(rate, 6)}
            )

    pricing = config["pricing"]
    plan_rows = []
    for rank, (name, values) in enumerate(pricing["plans"].items(), start=1):
        plan_rows.append(
            {
                "plan_id": f"plan_{name.lower()}", "plan_name": name, "plan_rank": rank,
                "included_seats": values["included_seats"], "active_flag": True,
            }
        )
    addon_categories = {
        "Advanced Analytics": "analytics", "Route Optimisation": "operations",
        "API Package": "platform", "ERP Integration": "integration",
        "Customer Portal": "customer_experience", "Document Management": "operations",
        "Premium Support": "service", "Additional Storage": "infrastructure",
    }
    addon_rows = [
        {
            "add_on_id": f"addon_{name.lower().replace(' ', '_')}", "add_on_name": name,
            "monthly_price_eur": price, "category": addon_categories[name], "active_flag": True,
        }
        for name, price in pricing["add_ons"].items()
    ]

    fx_frame = pd.DataFrame(fx_rows)
    lookup = _fx_lookup(fx_frame.assign(rate_date=pd.to_datetime(fx_frame["rate_date"])))
    price_rows = []
    price_id = 1
    increase_date = pd.Timestamp(config["scenarios"]["price_increase_date"])
    history_end = pd.Timestamp(config["project"]["history_end"])
    periods = [
        (pd.Timestamp(config["project"]["history_start"]), increase_date - pd.Timedelta(days=1), 1.0),
        (increase_date, history_end, 1.0 + float(config["scenarios"]["price_increase_pct"])),
    ]
    for country_code, country in geo.items():
        currency = country["currency"]
        for plan_name, plan in pricing["plans"].items():
            for effective_start, effective_end, multiplier in periods:
                if effective_start > history_end:
                    continue
                rate = _nearest_month_rate(lookup, currency, effective_start)
                for frequency in ("monthly", "annual"):
                    price_rows.append(
                        {
                            "plan_price_id": prefixed_id("pp", price_id),
                            "plan_id": f"plan_{plan_name.lower()}",
                            "country_code": country_code,
                            "currency_code": currency,
                            "billing_frequency": frequency,
                            "effective_start": _iso_date(effective_start),
                            "effective_end": _iso_date(min(effective_end, history_end)),
                            "base_price": round(plan["base_monthly_eur"] * multiplier / rate, 2),
                            "seat_price": round(plan["seat_monthly_eur"] * multiplier / rate, 2),
                            "annual_discount_pct": plan["annual_discount"] if frequency == "annual" else 0.0,
                        }
                    )
                    price_id += 1

    return {
        "regions": pd.DataFrame(region_rows),
        "countries": pd.DataFrame(country_rows),
        "currencies": pd.DataFrame(currency_rows),
        "fx_rates": fx_frame,
        "plans": pd.DataFrame(plan_rows),
        "plan_prices": pd.DataFrame(price_rows),
        "add_ons": pd.DataFrame(addon_rows),
    }


def generate_partners_campaigns_accounts(
    config: dict[str, Any], reference: dict[str, pd.DataFrame], rng: np.random.Generator
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    start = pd.Timestamp(config["project"]["history_start"])
    end = pd.Timestamp(config["project"]["history_end"])
    n_accounts = int(config["volumes"]["accounts"])
    geo = config["geography"]["countries"]
    adjustments = _scenario_adjustments(config)

    partner_count = max(12, int(n_accounts * 0.018))
    country_weights = {code: values["weight"] for code, values in geo.items()}
    partner_countries = weighted_choice(rng, country_weights, partner_count)
    partner_rows = []
    for idx, country in enumerate(partner_countries, start=1):
        partner_rows.append(
            {
                "partner_id": prefixed_id("partner", idx),
                "partner_name": f"{COUNTRY_NAMES[country]} Solutions Partner {idx:03d}",
                "partner_type": rng.choice(["reseller", "systems_integrator", "industry_consultant"], p=[0.38, 0.37, 0.25]),
                "country_code": country,
                "active_from": _iso_date(random_date(rng, start, end - pd.Timedelta(days=180))[0]),
                "active_flag": True,
            }
        )
    partners = pd.DataFrame(partner_rows)

    campaign_rows = []
    campaign_id = 1
    paid_channels = ["paid_search", "paid_social", "events", "partner"]
    for month in iter_months(start, end):
        for country, country_cfg in geo.items():
            if rng.random() > 0.62:
                continue
            for channel in rng.choice(paid_channels, size=int(rng.integers(1, 3)), replace=False):
                currency = country_cfg["currency"]
                spend_eur = float(rng.lognormal(mean=8.2, sigma=0.55))
                base_rate = FX_BASE[currency]
                campaign_rows.append(
                    {
                        "campaign_id": prefixed_id("campaign", campaign_id),
                        "campaign_name": f"{country}-{channel}-{month:%Y%m}",
                        "channel": channel,
                        "country_code": country,
                        "start_date": _iso_date(month),
                        "end_date": _iso_date(month_end(month)),
                        "spend_local": round(spend_eur / base_rate, 2),
                        "currency_code": currency,
                        "spend_eur": round(spend_eur, 2),
                    }
                )
                campaign_id += 1
    campaigns = pd.DataFrame(campaign_rows)

    country_choices = weighted_choice(rng, country_weights, n_accounts)
    segment_weights = {name: values["weight"] for name, values in config["business"]["segments"].items()}
    segments = weighted_choice(rng, segment_weights, n_accounts)
    channels = weighted_choice(rng, config["business"]["acquisition_channels"], n_accounts)
    created_dates = random_date(rng, start, end - pd.Timedelta(days=30), n_accounts)
    industries = rng.choice(config["business"]["industries"], size=n_accounts)

    account_rows = []
    lead_rows = []
    opportunity_rows = []
    stage_rows = []
    account_internal_rows = []
    stage_event_id = 1

    campaign_by_country_channel: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in campaigns.itertuples(index=False):
        campaign_by_country_channel[(row.country_code, row.channel)].append(row.campaign_id)

    for idx in range(n_accounts):
        account_id = prefixed_id("account", idx + 1)
        country = str(country_choices[idx])
        segment = str(segments[idx])
        channel = str(channels[idx])
        created_at = pd.Timestamp(created_dates[idx]) + pd.Timedelta(hours=int(rng.integers(8, 19)))
        motion_cfg = config["business"]["sales_motion_by_segment"][segment]
        sales_motion = str(weighted_choice(rng, motion_cfg)[0])
        if channel == "partner":
            sales_motion = "partner_led"
        if channel == "outbound_sales" and sales_motion == "self_service":
            sales_motion = "sales_assisted"

        segment_cfg = config["business"]["segments"][segment]
        target_seats = int(rng.integers(segment_cfg["min_seats"], segment_cfg["max_seats"] + 1))
        employee_multiplier = float(rng.uniform(1.2, 3.8))
        employee_estimate = max(target_seats, int(target_seats * employee_multiplier))
        employee_band = (
            "1-9" if employee_estimate < 10 else "10-49" if employee_estimate < 50 else
            "50-249" if employee_estimate < 250 else "250-999" if employee_estimate < 1000 else "1000+"
        )

        if sales_motion == "self_service":
            conversion_probability = float(config["behaviour"]["self_service_trial_to_paid_base"])
        elif sales_motion == "partner_led":
            conversion_probability = float(config["behaviour"]["opportunity_win_base"]) * 1.18
        else:
            conversion_probability = float(config["behaviour"]["opportunity_win_base"])
        conversion_probability *= float(adjustments.get("conversion_multiplier", 1.0))
        conversion_probability *= {"micro": 0.92, "small": 1.0, "medium": 1.08, "mid_market": 1.12, "enterprise": 1.15}[segment]
        converted = bool(rng.random() < clamp(conversion_probability, 0.05, 0.88))

        if sales_motion == "self_service":
            lag_days = int(rng.integers(2, 35))
        else:
            lag_days = int(clamp(rng.lognormal(mean=4.0, sigma=0.55), 20, 220))
        subscription_start = created_at.normalize() + pd.Timedelta(days=lag_days)
        if subscription_start > end:
            converted = False
            subscription_start = pd.NaT

        partner_id = None
        if sales_motion == "partner_led" and not partners.empty:
            local = partners.loc[partners["country_code"] == country, "partner_id"].tolist()
            partner_id = str(rng.choice(local if local else partners["partner_id"].tolist()))

        account_rows.append(
            {
                "account_id": account_id,
                "account_name": f"{COUNTRY_NAMES[country]} Field Services {idx + 1:05d}",
                "created_at": _iso_ts(created_at),
                "country_code": country,
                "region_id": reference["countries"].set_index("country_code").loc[country, "region_id"],
                "industry": str(industries[idx]),
                "segment": segment,
                "employee_band": employee_band,
                "acquisition_channel": channel,
                "sales_motion": sales_motion,
                "partner_id": partner_id,
                "account_status": "customer" if converted else str(rng.choice(["prospect", "lost"], p=[0.38, 0.62])),
                "legal_currency": geo[country]["currency"],
                "tax_id_present": bool(rng.random() < 0.94),
            }
        )

        campaign_candidates = campaign_by_country_channel.get((country, channel), [])
        campaign_id_value = str(rng.choice(campaign_candidates)) if campaign_candidates else None
        lead_score = int(clamp(rng.normal(58 if converted else 41, 18), 0, 100))
        mql = created_at + pd.Timedelta(days=int(rng.integers(0, 8))) if lead_score >= 45 else pd.NaT
        sql_at = mql + pd.Timedelta(days=int(rng.integers(1, 12))) if pd.notna(mql) and sales_motion != "self_service" else pd.NaT
        lead_id = prefixed_id("lead", idx + 1)
        lead_rows.append(
            {
                "lead_id": lead_id, "account_id": account_id, "created_at": _iso_ts(created_at),
                "source_channel": channel,
                "lead_status": "converted" if converted else ("qualified" if lead_score >= 55 else "disqualified"),
                "mql_at": _iso_ts(mql), "sql_at": _iso_ts(sql_at), "lead_score": lead_score,
                "campaign_id": campaign_id_value,
            }
        )

        opportunity_id = None
        if sales_motion != "self_service" and pd.notna(sql_at):
            opportunity_id = prefixed_id("opp", len(opportunity_rows) + 1)
            close_date = subscription_start if converted else sql_at.normalize() + pd.Timedelta(days=int(rng.integers(25, 160)))
            expected_arr = target_seats * {"micro": 250, "small": 380, "medium": 520, "mid_market": 660, "enterprise": 780}[segment]
            stages = ["qualification", "discovery", "demonstration", "proposal", "negotiation"]
            stage_count = len(stages) if converted else int(rng.integers(1, len(stages) + 1))
            entered = pd.Timestamp(sql_at)
            for seq, stage in enumerate(stages[:stage_count], start=1):
                duration = int(rng.integers(3, 22))
                exited = entered + pd.Timedelta(days=duration)
                if converted and seq == stage_count:
                    exited = pd.Timestamp(close_date)
                stage_rows.append(
                    {
                        "stage_event_id": prefixed_id("stage", stage_event_id),
                        "opportunity_id": opportunity_id, "stage_name": stage,
                        "entered_at": _iso_ts(entered), "exited_at": _iso_ts(exited),
                        "stage_sequence": seq,
                    }
                )
                stage_event_id += 1
                entered = exited
            loss_reason = None if converted else str(rng.choice([
                "budget", "timing", "competitor", "missing_feature", "no_decision", "security_review"
            ], p=[0.22, 0.19, 0.20, 0.14, 0.17, 0.08]))
            opportunity_rows.append(
                {
                    "opportunity_id": opportunity_id, "account_id": account_id,
                    "created_at": _iso_ts(sql_at), "close_date": _iso_date(close_date),
                    "stage": "closed_won" if converted else "closed_lost",
                    "status": "won" if converted else "lost",
                    "owner_team": f"{reference['countries'].set_index('country_code').loc[country, 'region_id']}_sales",
                    "expected_arr_eur": round(expected_arr, 2),
                    "probability": 1.0 if converted else 0.0, "loss_reason": loss_reason,
                }
            )

        account_internal_rows.append(
            {
                "account_id": account_id, "converted_flag": converted,
                "subscription_start": subscription_start, "target_seats": target_seats,
                "country_code": country, "segment": segment, "sales_motion": sales_motion,
                "created_at": created_at, "partner_id": partner_id, "opportunity_id": opportunity_id,
            }
        )

    tables = {
        "partners": partners,
        "marketing_campaigns": campaigns,
        "accounts": pd.DataFrame(account_rows),
        "leads": pd.DataFrame(lead_rows),
        "opportunities": pd.DataFrame(opportunity_rows, columns=TABLE_SCHEMAS["opportunities"]["columns"].keys()),
        "opportunity_stage_history": pd.DataFrame(stage_rows, columns=TABLE_SCHEMAS["opportunity_stage_history"]["columns"].keys()),
    }
    return tables, pd.DataFrame(account_internal_rows)


def _choose_plan(rng: np.random.Generator, segment: str) -> str:
    return str(rng.choice(PLAN_BY_SEGMENT[segment]))


def _plan_mrr_eur(config: dict[str, Any], plan_name: str, seats: int, annual: bool, date: pd.Timestamp) -> float:
    plan = config["pricing"]["plans"][plan_name]
    multiplier = 1.0
    if date >= pd.Timestamp(config["scenarios"]["price_increase_date"]):
        multiplier += float(config["scenarios"]["price_increase_pct"])
    gross = (plan["base_monthly_eur"] + max(0, seats - plan["included_seats"]) * plan["seat_monthly_eur"]) * multiplier
    if annual:
        gross *= 1.0 - plan["annual_discount"]
    return float(gross)


def generate_subscriptions_users(
    config: dict[str, Any], reference: dict[str, pd.DataFrame], account_internal: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    end = pd.Timestamp(config["project"]["history_end"])
    geo = config["geography"]["countries"]
    fx_frame = reference["fx_rates"].copy()
    fx_frame["rate_date"] = pd.to_datetime(fx_frame["rate_date"])
    fx_lookup = _fx_lookup(fx_frame)
    adjustments = _scenario_adjustments(config)

    workspace_rows: list[dict[str, Any]] = []
    user_rows: list[dict[str, Any]] = []
    contract_rows: list[dict[str, Any]] = []
    subscription_rows: list[dict[str, Any]] = []
    item_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    renewal_rows: list[dict[str, Any]] = []
    onboarding_rows: list[dict[str, Any]] = []
    payment_method_rows: list[dict[str, Any]] = []
    schedule_rows: list[dict[str, Any]] = []
    subscription_meta: dict[str, dict[str, Any]] = {}

    workspace_id = user_id = item_id = event_id = renewal_id = onboarding_id = pm_id = 1
    converted_accounts = account_internal[account_internal["converted_flag"]].copy()

    for sub_index, account in enumerate(converted_accounts.itertuples(index=False), start=1):
        account_id = account.account_id
        start_date = pd.Timestamp(account.subscription_start)
        country = account.country_code
        segment = account.segment
        currency = geo[country]["currency"]
        plan_name = _choose_plan(rng, segment)
        annual_probability = float(config["behaviour"]["annual_share"]) + {
            "micro": -0.22, "small": -0.08, "medium": 0.08, "mid_market": 0.18, "enterprise": 0.28
        }[segment]
        annual = bool(rng.random() < clamp(annual_probability, 0.15, 0.94))
        billing_frequency = "annual" if annual else "monthly"
        term_months = int(rng.choice([12, 24, 36], p=[0.72, 0.20, 0.08])) if annual else 1
        discount_pct = float(config["pricing"]["plans"][plan_name]["annual_discount"] if annual else 0.0)
        if account.sales_motion != "self_service":
            discount_pct += float(rng.choice([0.0, 0.03, 0.05, 0.08, 0.12], p=[0.30, 0.22, 0.23, 0.18, 0.07]))
        discount_pct = clamp(discount_pct, 0.0, 0.35)

        onboarding_probability = float(config["behaviour"]["onboarding_completion_base"])
        onboarding_probability *= float(adjustments.get("adoption_multiplier", 1.0))
        onboarding_probability += {"micro": -0.08, "small": -0.02, "medium": 0.04, "mid_market": 0.08, "enterprise": 0.10}[segment]
        onboarding_complete = bool(rng.random() < clamp(onboarding_probability, 0.40, 0.97))

        monthly_churn = float(config["behaviour"]["monthly_logo_churn_base"])
        monthly_churn *= float(adjustments.get("churn_multiplier", 1.0))
        monthly_churn *= {"micro": 1.65, "small": 1.25, "medium": 0.80, "mid_market": 0.55, "enterprise": 0.36}[segment]
        if annual:
            monthly_churn *= 0.58
        if onboarding_complete:
            monthly_churn *= 0.66

        max_life_months = max(1, len(list(iter_months(start_date, end))))
        churn_month_index = None
        for month_index in range(1, max_life_months):
            if rng.random() < monthly_churn:
                churn_month_index = month_index
                break
        ended_date = None
        churn_type = None
        if churn_month_index is not None:
            churn_month = list(iter_months(start_date, end))[churn_month_index]
            ended_date = month_end(churn_month)
            churn_type = str(rng.choice(["voluntary", "involuntary"], p=[0.74, 0.26]))

        subscription_id = prefixed_id("subscription", sub_index)
        contract_id = prefixed_id("contract", sub_index)
        contract_end = start_date + pd.DateOffset(months=term_months) - pd.Timedelta(days=1)
        contract_status = "terminated" if ended_date is not None else ("active" if contract_end >= end else "expired")
        contract_rows.append(
            {
                "contract_id": contract_id, "account_id": account_id,
                "contract_number": f"CTR-{start_date:%Y}-{sub_index:06d}",
                "signed_date": _iso_date(start_date - pd.Timedelta(days=int(rng.integers(1, 15)))),
                "start_date": _iso_date(start_date), "end_date": _iso_date(contract_end),
                "auto_renew_flag": bool(rng.random() < (0.91 if annual else 0.98)),
                "contract_term_months": term_months, "billing_frequency": billing_frequency,
                "currency_code": currency, "discount_pct": round(discount_pct, 4),
                "contract_status": contract_status, "sales_motion": account.sales_motion,
            }
        )
        trial_start = account.created_at if account.sales_motion == "self_service" else pd.NaT
        trial_end = start_date - pd.Timedelta(days=1) if account.sales_motion == "self_service" else pd.NaT
        cancel_requested = ended_date - pd.Timedelta(days=int(rng.integers(1, 31))) if ended_date is not None and churn_type == "voluntary" else pd.NaT
        subscription_rows.append(
            {
                "subscription_id": subscription_id, "account_id": account_id, "contract_id": contract_id,
                "plan_id": f"plan_{plan_name.lower()}", "trial_start_date": _iso_date(trial_start),
                "trial_end_date": _iso_date(trial_end), "subscription_start_date": _iso_date(start_date),
                "current_status": "churned" if ended_date is not None else "active",
                "cancel_requested_date": _iso_date(cancel_requested), "ended_date": _iso_date(ended_date),
                "churn_type": churn_type, "billing_frequency": billing_frequency, "currency_code": currency,
            }
        )
        if account.sales_motion == "self_service":
            event_rows.append(
                {
                    "subscription_event_id": prefixed_id("subevent", event_id), "subscription_id": subscription_id,
                    "event_at": _iso_ts(pd.Timestamp(account.created_at)), "event_type": "trial_started",
                    "previous_plan_id": None, "new_plan_id": f"plan_{plan_name.lower()}",
                    "previous_quantity": None, "new_quantity": int(account.target_seats),
                    "mrr_change_eur": 0.0, "event_reason": "self_service_trial", "initiated_by": "customer",
                }
            )
            event_id += 1

        initial_seats = int(account.target_seats)
        months = list(iter_months(start_date, ended_date or end))
        current_plan = plan_name
        current_seats = initial_seats
        state_history: list[tuple[pd.Timestamp, str, int, float]] = []
        for month_index, month in enumerate(months):
            if month_index > 0:
                expansion_rate = float(config["behaviour"]["monthly_expansion_base"])
                contraction_rate = float(config["behaviour"]["monthly_contraction_base"]) * float(adjustments.get("contraction_multiplier", 1.0))
                expansion_rate *= {"micro": 0.65, "small": 0.90, "medium": 1.15, "mid_market": 1.35, "enterprise": 1.45}[segment]
                if onboarding_complete:
                    expansion_rate *= 1.25
                change_type = None
                old_seats = current_seats
                old_plan = current_plan
                if rng.random() < expansion_rate:
                    growth = max(1, int(round(current_seats * rng.uniform(0.08, 0.28))))
                    current_seats += growth
                    change_type = "seat_expanded"
                elif rng.random() < contraction_rate:
                    reduction = max(1, int(round(current_seats * rng.uniform(0.05, 0.20))))
                    current_seats = max(1, current_seats - reduction)
                    change_type = "seat_contracted"
                current_rank = PLAN_ORDER.index(current_plan)
                if current_rank < len(PLAN_ORDER) - 1 and current_seats > config["pricing"]["plans"][current_plan]["included_seats"] * 4 and rng.random() < 0.09:
                    current_plan = PLAN_ORDER[current_rank + 1]
                    change_type = "plan_upgraded"
                if change_type:
                    old_mrr = _plan_mrr_eur(config, old_plan, old_seats, annual, month)
                    new_mrr = _plan_mrr_eur(config, current_plan, current_seats, annual, month)
                    event_rows.append(
                        {
                            "subscription_event_id": prefixed_id("subevent", event_id),
                            "subscription_id": subscription_id, "event_at": _iso_ts(month + pd.Timedelta(days=4)),
                            "event_type": change_type, "previous_plan_id": f"plan_{old_plan.lower()}",
                            "new_plan_id": f"plan_{current_plan.lower()}", "previous_quantity": old_seats,
                            "new_quantity": current_seats, "mrr_change_eur": round(new_mrr - old_mrr, 2),
                            "event_reason": "customer_growth" if new_mrr > old_mrr else "capacity_adjustment",
                            "initiated_by": "customer",
                        }
                    )
                    event_id += 1
            mrr_eur = _plan_mrr_eur(config, current_plan, current_seats, annual, month) * (1.0 - max(0.0, discount_pct - (config["pricing"]["plans"][current_plan]["annual_discount"] if annual else 0.0)))
            rate = _nearest_month_rate(fx_lookup, currency, month)
            schedule_rows.append(
                {
                    "subscription_id": subscription_id, "account_id": account_id, "month": month,
                    "plan_name": current_plan, "seats": current_seats, "mrr_eur": round(mrr_eur, 2),
                    "mrr_local": round(mrr_eur / rate, 2), "currency_code": currency,
                    "billing_frequency": billing_frequency, "segment": segment, "country_code": country,
                    "onboarding_complete": onboarding_complete,
                }
            )
            state_history.append((month, current_plan, current_seats, mrr_eur))

        # Compress monthly state into effective-dated subscription items.
        run_start = 0
        for position in range(1, len(state_history) + 1):
            boundary = position == len(state_history) or state_history[position][1:3] != state_history[run_start][1:3]
            if not boundary:
                continue
            effective_start, run_plan, run_seats, run_mrr = state_history[run_start]
            effective_end = month_end(state_history[position - 1][0])
            rate = _nearest_month_rate(fx_lookup, currency, effective_start)
            item_rows.append(
                {
                    "subscription_item_id": prefixed_id("subitem", item_id), "subscription_id": subscription_id,
                    "item_type": "plan", "plan_id": f"plan_{run_plan.lower()}", "add_on_id": None,
                    "quantity": run_seats, "unit_price_local": round(run_mrr / rate / max(run_seats, 1), 4),
                    "discount_pct": round(discount_pct, 4), "effective_start": _iso_date(effective_start),
                    "effective_end": _iso_date(effective_end), "mrr_local": round(run_mrr / rate, 2),
                    "mrr_eur": round(run_mrr, 2),
                }
            )
            item_id += 1
            run_start = position

        activation_mrr = state_history[0][3]
        event_rows.append(
            {
                "subscription_event_id": prefixed_id("subevent", event_id), "subscription_id": subscription_id,
                "event_at": _iso_ts(start_date), "event_type": "subscription_activated",
                "previous_plan_id": None, "new_plan_id": f"plan_{plan_name.lower()}",
                "previous_quantity": 0, "new_quantity": initial_seats,
                "mrr_change_eur": round(activation_mrr, 2), "event_reason": "new_business",
                "initiated_by": "system",
            }
        )
        event_id += 1

        # Add-ons are adopted by mature accounts and represented as separate recurring items.
        addon_probability = {"micro": 0.12, "small": 0.28, "medium": 0.52, "mid_market": 0.72, "enterprise": 0.88}[segment]
        addon_count = int(rng.integers(1, 4)) if rng.random() < addon_probability and len(months) >= 3 else 0
        addon_names = list(config["pricing"]["add_ons"])
        selected_addons = rng.choice(addon_names, size=addon_count, replace=False) if addon_count else []
        for addon_name in selected_addons:
            adoption_month = months[int(rng.integers(1, min(len(months), 8)))]
            addon_eur = float(config["pricing"]["add_ons"][str(addon_name)])
            if annual:
                addon_eur *= 0.90
            rate = _nearest_month_rate(fx_lookup, currency, adoption_month)
            item_rows.append(
                {
                    "subscription_item_id": prefixed_id("subitem", item_id), "subscription_id": subscription_id,
                    "item_type": "add_on", "plan_id": None,
                    "add_on_id": f"addon_{str(addon_name).lower().replace(' ', '_')}", "quantity": 1,
                    "unit_price_local": round(addon_eur / rate, 2), "discount_pct": 0.0,
                    "effective_start": _iso_date(adoption_month), "effective_end": _iso_date(month_end(months[-1])),
                    "mrr_local": round(addon_eur / rate, 2), "mrr_eur": round(addon_eur, 2),
                }
            )
            item_id += 1
            event_rows.append(
                {
                    "subscription_event_id": prefixed_id("subevent", event_id), "subscription_id": subscription_id,
                    "event_at": _iso_ts(adoption_month + pd.Timedelta(days=10)), "event_type": "add_on_added",
                    "previous_plan_id": f"plan_{current_plan.lower()}", "new_plan_id": f"plan_{current_plan.lower()}",
                    "previous_quantity": 0, "new_quantity": 1, "mrr_change_eur": round(addon_eur, 2),
                    "event_reason": str(addon_name).lower().replace(" ", "_"), "initiated_by": "customer",
                }
            )
            event_id += 1
            for schedule in schedule_rows:
                if schedule["subscription_id"] == subscription_id and schedule["month"] >= adoption_month:
                    schedule["mrr_eur"] = round(schedule["mrr_eur"] + addon_eur, 2)
                    schedule["mrr_local"] = round(schedule["mrr_local"] + addon_eur / _nearest_month_rate(fx_lookup, currency, schedule["month"]), 2)

        if ended_date is not None:
            if pd.notna(cancel_requested):
                event_rows.append(
                    {
                        "subscription_event_id": prefixed_id("subevent", event_id), "subscription_id": subscription_id,
                        "event_at": _iso_ts(cancel_requested), "event_type": "cancellation_requested",
                        "previous_plan_id": f"plan_{current_plan.lower()}", "new_plan_id": None,
                        "previous_quantity": current_seats, "new_quantity": 0, "mrr_change_eur": 0.0,
                        "event_reason": str(rng.choice(["budget", "low_usage", "missing_feature", "service_quality", "business_closed", "competitor"])),
                        "initiated_by": "customer",
                    }
                )
                event_id += 1
            final_mrr = schedule_rows[-1]["mrr_eur"] if schedule_rows else activation_mrr
            event_rows.append(
                {
                    "subscription_event_id": prefixed_id("subevent", event_id), "subscription_id": subscription_id,
                    "event_at": _iso_ts(ended_date), "event_type": "subscription_churned",
                    "previous_plan_id": f"plan_{current_plan.lower()}", "new_plan_id": None,
                    "previous_quantity": current_seats, "new_quantity": 0, "mrr_change_eur": round(-final_mrr, 2),
                    "event_reason": churn_type, "initiated_by": "system" if churn_type == "involuntary" else "customer",
                }
            )
            event_id += 1

        # Renewal records for annual contracts.
        if annual:
            due = start_date + pd.DateOffset(years=1)
            while due <= end:
                if ended_date is not None and due > ended_date:
                    break
                decision = due - pd.Timedelta(days=int(rng.integers(5, 45)))
                latest_mrr = next((row["mrr_eur"] for row in reversed(schedule_rows) if row["subscription_id"] == subscription_id and row["month"] <= month_start(due)), activation_mrr)
                renewal_probability = clamp(0.84 + (0.08 if onboarding_complete else -0.12) - monthly_churn * 5, 0.20, 0.98)
                renewed = ended_date is None or due <= ended_date
                renewal_rows.append(
                    {
                        "renewal_id": prefixed_id("renewal", renewal_id), "subscription_id": subscription_id,
                        "renewal_due_date": _iso_date(due), "decision_date": _iso_date(decision),
                        "renewal_status": "renewed" if renewed else "churned",
                        "renewal_arr_eur": round(latest_mrr * 12, 2),
                        "renewal_probability": round(renewal_probability, 4),
                        "risk_reason": None if renewed else str(rng.choice(["low_adoption", "budget", "support_issues", "payment_risk"])),
                    }
                )
                renewal_id += 1
                due += pd.DateOffset(years=1)

        # Workspaces and users.
        workspace_count = {"micro": 1, "small": 1, "medium": int(rng.integers(1, 3)), "mid_market": int(rng.integers(2, 5)), "enterprise": int(rng.integers(3, 8))}[segment]
        account_workspaces = []
        for w_idx in range(workspace_count):
            wid = prefixed_id("workspace", workspace_id)
            workspace_id += 1
            account_workspaces.append(wid)
            workspace_rows.append(
                {
                    "workspace_id": wid, "account_id": account_id,
                    "workspace_name": f"{account_id} Workspace {w_idx + 1}",
                    "created_at": _iso_ts(start_date + pd.Timedelta(days=int(rng.integers(0, 12)))),
                    "country_code": country, "active_flag": ended_date is None,
                }
            )
        max_users = int(config["volumes"]["max_users_per_account"])
        user_count = min(max_users, max(1, int(round(initial_seats * rng.uniform(0.75, 1.08)))))
        for _ in range(user_count):
            uid = prefixed_id("user", user_id)
            user_id += 1
            invited = start_date + pd.Timedelta(days=int(rng.integers(0, 40)))
            activated = invited + pd.Timedelta(hours=int(rng.integers(1, 96))) if rng.random() < (0.90 if onboarding_complete else 0.70) else pd.NaT
            user_rows.append(
                {
                    "user_id": uid, "account_id": account_id, "workspace_id": str(rng.choice(account_workspaces)),
                    "created_at": _iso_ts(invited), "role_name": str(weighted_choice(rng, ROLE_WEIGHTS)[0]),
                    "user_status": "active" if ended_date is None else "deactivated",
                    "invited_at": _iso_ts(invited), "activated_at": _iso_ts(activated),
                    "deactivated_at": _iso_ts(ended_date) if ended_date is not None else None,
                    "mobile_user_flag": bool(rng.random() < 0.68),
                }
            )

        # Onboarding checklist.
        tasks = ["company_profile", "invite_team", "create_workspace", "create_first_work_order", "complete_first_work_order", "connect_integration"]
        for task_sequence, task in enumerate(tasks, start=1):
            due = start_date + pd.Timedelta(days=task_sequence * 5)
            completion_likelihood = clamp((0.96 - task_sequence * 0.055) if onboarding_complete else (0.75 - task_sequence * 0.09), 0.15, 0.98)
            completed = rng.random() < completion_likelihood
            completed_at = start_date + pd.Timedelta(days=int(rng.integers(task_sequence, task_sequence * 7 + 1))) if completed else pd.NaT
            onboarding_rows.append(
                {
                    "onboarding_task_id": prefixed_id("onboard", onboarding_id), "account_id": account_id,
                    "task_name": task, "task_sequence": task_sequence, "due_date": _iso_date(due),
                    "completed_at": _iso_ts(completed_at), "task_status": "completed" if completed else "open",
                    "owner_type": "customer_success" if account.sales_motion != "self_service" else "customer",
                }
            )
            onboarding_id += 1

        method_type = str(rng.choice(["card", "sepa_debit", "bank_transfer"], p=[0.48, 0.34, 0.18]))
        if segment in {"mid_market", "enterprise"}:
            method_type = str(rng.choice(["sepa_debit", "bank_transfer"], p=[0.35, 0.65]))
        payment_method_rows.append(
            {
                "payment_method_id": prefixed_id("pm", pm_id), "account_id": account_id,
                "method_type": method_type, "provider": "Adyen" if method_type != "bank_transfer" else "bank",
                "created_at": _iso_ts(start_date - pd.Timedelta(days=1)),
                "expiry_month": int(rng.integers(1, 13)) if method_type == "card" else None,
                "expiry_year": int(rng.integers(2027, 2031)) if method_type == "card" else None,
                "active_flag": True,
            }
        )
        subscription_meta[subscription_id] = {
            "payment_method_id": prefixed_id("pm", pm_id), "ended_date": ended_date,
            "churn_type": churn_type, "vat_rate": geo[country]["vat_rate"], "onboarding_complete": onboarding_complete,
            "segment": segment, "country_code": country, "account_id": account_id,
        }
        pm_id += 1

    tables = {
        "workspaces": pd.DataFrame(workspace_rows, columns=TABLE_SCHEMAS["workspaces"]["columns"].keys()),
        "users": pd.DataFrame(user_rows, columns=TABLE_SCHEMAS["users"]["columns"].keys()),
        "contracts": pd.DataFrame(contract_rows, columns=TABLE_SCHEMAS["contracts"]["columns"].keys()),
        "subscriptions": pd.DataFrame(subscription_rows, columns=TABLE_SCHEMAS["subscriptions"]["columns"].keys()),
        "subscription_items": pd.DataFrame(item_rows, columns=TABLE_SCHEMAS["subscription_items"]["columns"].keys()),
        "subscription_events": pd.DataFrame(event_rows, columns=TABLE_SCHEMAS["subscription_events"]["columns"].keys()),
        "renewals": pd.DataFrame(renewal_rows, columns=TABLE_SCHEMAS["renewals"]["columns"].keys()),
        "onboarding_tasks": pd.DataFrame(onboarding_rows, columns=TABLE_SCHEMAS["onboarding_tasks"]["columns"].keys()),
        "payment_methods": pd.DataFrame(payment_method_rows, columns=TABLE_SCHEMAS["payment_methods"]["columns"].keys()),
    }
    internal = {
        "subscription_schedule": pd.DataFrame(schedule_rows),
        "subscription_meta": subscription_meta,
    }
    return tables, internal


def generate_billing(
    config: dict[str, Any],
    reference: dict[str, pd.DataFrame],
    subscription_tables: dict[str, pd.DataFrame],
    internal: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    schedule = internal["subscription_schedule"].copy()
    meta = internal["subscription_meta"]
    subscriptions = subscription_tables["subscriptions"].set_index("subscription_id")
    payment_methods = subscription_tables["payment_methods"].set_index("account_id")
    end = pd.Timestamp(config["project"]["history_end"])
    fx_frame = reference["fx_rates"].copy()
    fx_frame["rate_date"] = pd.to_datetime(fx_frame["rate_date"])
    fx_lookup = _fx_lookup(fx_frame)
    improved_date = pd.Timestamp(config["scenarios"]["improved_dunning_date"])
    adjustments = _scenario_adjustments(config)

    invoice_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []
    payment_rows: list[dict[str, Any]] = []
    credit_rows: list[dict[str, Any]] = []
    refund_rows: list[dict[str, Any]] = []
    dunning_rows: list[dict[str, Any]] = []
    invoice_outcomes: list[dict[str, Any]] = []

    invoice_id_counter = line_id = attempt_id = payment_id = credit_id = refund_id = dunning_id = 1
    for subscription_id, group in schedule.groupby("subscription_id", sort=False):
        group = group.sort_values("month")
        subscription = subscriptions.loc[subscription_id]
        start_date = pd.Timestamp(subscription["subscription_start_date"])
        account_id = subscription["account_id"]
        billing_frequency = subscription["billing_frequency"]
        currency = subscription["currency_code"]
        method = payment_methods.loc[account_id]
        if isinstance(method, pd.DataFrame):
            method = method.iloc[0]
        sub_meta = meta[subscription_id]
        ended_date = sub_meta["ended_date"]
        churn_type = sub_meta["churn_type"]

        for row in group.itertuples(index=False):
            month = pd.Timestamp(row.month)
            if billing_frequency == "annual":
                months_since_start = (month.year - start_date.year) * 12 + month.month - start_date.month
                if months_since_start % 12 != 0:
                    continue
                service_start = month
                service_end = min(month + pd.DateOffset(years=1) - pd.Timedelta(days=1), ended_date or end)
                subtotal_local = float(row.mrr_local) * 12
            else:
                service_start = month
                service_end = min(month_end(month), ended_date or month_end(month))
                subtotal_local = float(row.mrr_local)

            invoice_date = max(start_date, service_start)
            due_days = 30 if method["method_type"] == "bank_transfer" else 3
            due_date = invoice_date + pd.Timedelta(days=due_days)
            vat_rate = float(sub_meta["vat_rate"])
            tax_local = subtotal_local * vat_rate
            total_local = subtotal_local + tax_local
            fx_rate = _nearest_month_rate(fx_lookup, currency, invoice_date)
            total_eur = total_local * fx_rate
            invoice_id_value = prefixed_id("invoice", invoice_id_counter)
            invoice_number = f"INV-{invoice_date:%Y%m}-{invoice_id_counter:07d}"
            invoice_id_counter += 1

            line_rows.append(
                {
                    "invoice_line_id": prefixed_id("invline", line_id), "invoice_id": invoice_id_value,
                    "line_type": "recurring_subscription", "description": f"SaaS subscription {service_start:%Y-%m}",
                    "quantity": 1.0, "unit_price_local": round(subtotal_local, 2), "discount_local": 0.0,
                    "line_total_local": round(subtotal_local, 2), "service_period_start": _iso_date(service_start),
                    "service_period_end": _iso_date(service_end), "subscription_item_id": None,
                }
            )
            line_id += 1

            method_type = method["method_type"]
            failure_probability = float(config["behaviour"]["payment_failure_base"])
            failure_probability *= {"card": 1.25, "sepa_debit": 0.72, "bank_transfer": 0.45}[method_type]
            failure_probability *= {"micro": 1.25, "small": 1.10, "medium": 0.90, "mid_market": 0.70, "enterprise": 0.55}[sub_meta["segment"]]
            force_final_failure = bool(
                churn_type == "involuntary"
                and ended_date is not None
                and month_start(ended_date) == month_start(invoice_date)
            )
            first_failed = force_final_failure or rng.random() < failure_probability
            recovered = False
            paid_at: pd.Timestamp | None = None
            successful_attempt_id: str | None = None
            attempt_count = 1 if not first_failed else int(rng.integers(2, 5))
            for attempt_number in range(1, attempt_count + 1):
                attempt_at = invoice_date + pd.Timedelta(days=(attempt_number - 1) * int(rng.integers(2, 5)))
                if attempt_number == 1 and not first_failed:
                    status = "succeeded"
                elif force_final_failure:
                    status = "failed"
                else:
                    base_recovery = float(config["behaviour"]["payment_recovery_base"])
                    if attempt_at >= improved_date:
                        base_recovery += float(config["scenarios"]["improved_dunning_recovery_lift"])
                    base_recovery += float(adjustments.get("payment_recovery_lift", 0.0))
                    per_attempt = clamp(base_recovery / max(attempt_count - 1, 1), 0.12, 0.72)
                    status = "succeeded" if attempt_number > 1 and not recovered and rng.random() < per_attempt else "failed"
                failure_reason = None
                response_code = "approved"
                if status == "failed":
                    failure_reason = str(rng.choice(
                        ["insufficient_funds", "expired_card", "bank_decline", "technical_error", "mandate_missing"],
                        p=[0.38, 0.16, 0.23, 0.14, 0.09],
                    ))
                    response_code = {
                        "insufficient_funds": "51", "expired_card": "54", "bank_decline": "05",
                        "technical_error": "96", "mandate_missing": "M01",
                    }[failure_reason]
                attempt_id_value = prefixed_id("payattempt", attempt_id)
                attempt_id += 1
                attempt_rows.append(
                    {
                        "payment_attempt_id": attempt_id_value, "invoice_id": invoice_id_value,
                        "payment_method_id": method["payment_method_id"], "attempt_at": _iso_ts(attempt_at),
                        "attempt_number": attempt_number, "amount_local": round(total_local, 2),
                        "currency_code": currency, "attempt_status": status,
                        "failure_reason": failure_reason, "provider_response_code": response_code,
                    }
                )
                if status == "failed":
                    dunning_rows.append(
                        {
                            "dunning_event_id": prefixed_id("dunning", dunning_id), "invoice_id": invoice_id_value,
                            "event_at": _iso_ts(attempt_at + pd.Timedelta(hours=4)), "dunning_step": attempt_number,
                            "channel": str(rng.choice(["email", "in_app", "customer_success"], p=[0.62, 0.25, 0.13])),
                            "event_status": "sent", "recovered_after_event_flag": False,
                        }
                    )
                    dunning_id += 1
                else:
                    recovered = attempt_number > 1
                    paid_at = attempt_at
                    successful_attempt_id = attempt_id_value
                    if recovered and dunning_rows:
                        dunning_rows[-1]["recovered_after_event_flag"] = True
                    break

            invoice_status = "paid" if paid_at is not None else ("overdue" if due_date <= end else "open")
            invoice_rows.append(
                {
                    "invoice_id": invoice_id_value, "account_id": account_id, "subscription_id": subscription_id,
                    "invoice_number": invoice_number, "invoice_date": _iso_date(invoice_date),
                    "due_date": _iso_date(due_date), "service_period_start": _iso_date(service_start),
                    "service_period_end": _iso_date(service_end), "currency_code": currency,
                    "subtotal_local": round(subtotal_local, 2), "tax_local": round(tax_local, 2),
                    "total_local": round(total_local, 2), "total_eur": round(total_eur, 2),
                    "invoice_status": invoice_status, "paid_date": _iso_date(paid_at),
                }
            )
            if paid_at is not None and successful_attempt_id is not None:
                payment_id_value = prefixed_id("payment", payment_id)
                payment_rows.append(
                    {
                        "payment_id": payment_id_value, "invoice_id": invoice_id_value,
                        "payment_attempt_id": successful_attempt_id, "captured_at": _iso_ts(paid_at),
                        "amount_local": round(total_local, 2), "currency_code": currency,
                        "amount_eur": round(total_eur, 2), "payment_status": "captured",
                        "settlement_date": _iso_date(paid_at + pd.Timedelta(days=2)),
                    }
                )
                payment_id += 1

                # Commercial adjustments and refunds are rare but reconciled.
                if rng.random() < 0.012:
                    credit_amount = round(subtotal_local * float(rng.uniform(0.05, 0.35)), 2)
                    credit_rows.append(
                        {
                            "credit_note_id": prefixed_id("credit", credit_id), "invoice_id": invoice_id_value,
                            "issued_date": _iso_date(paid_at + pd.Timedelta(days=int(rng.integers(2, 30)))),
                            "reason": str(rng.choice(["billing_correction", "service_credit", "contract_adjustment"])),
                            "amount_local": credit_amount, "amount_eur": round(credit_amount * fx_rate, 2),
                            "credit_note_status": "issued",
                        }
                    )
                    credit_id += 1
                if rng.random() < 0.006:
                    refund_amount = round(total_local * float(rng.uniform(0.10, 1.0)), 2)
                    requested = paid_at + pd.Timedelta(days=int(rng.integers(3, 40)))
                    refund_rows.append(
                        {
                            "refund_id": prefixed_id("refund", refund_id), "payment_id": payment_id_value,
                            "requested_at": _iso_ts(requested), "processed_at": _iso_ts(requested + pd.Timedelta(days=2)),
                            "amount_local": refund_amount, "amount_eur": round(refund_amount * fx_rate, 2),
                            "reason": str(rng.choice(["duplicate_charge", "service_failure", "customer_request"])),
                            "refund_status": "processed",
                        }
                    )
                    refund_id += 1

            invoice_outcomes.append(
                {
                    "account_id": account_id, "subscription_id": subscription_id,
                    "invoice_month": month_start(invoice_date), "invoice_status": invoice_status,
                    "first_attempt_failed": first_failed, "recovered": recovered,
                    "total_eur": round(total_eur, 2),
                }
            )

    tables = {
        "invoices": pd.DataFrame(invoice_rows, columns=TABLE_SCHEMAS["invoices"]["columns"].keys()),
        "invoice_lines": pd.DataFrame(line_rows, columns=TABLE_SCHEMAS["invoice_lines"]["columns"].keys()),
        "payment_attempts": pd.DataFrame(attempt_rows, columns=TABLE_SCHEMAS["payment_attempts"]["columns"].keys()),
        "payments": pd.DataFrame(payment_rows, columns=TABLE_SCHEMAS["payments"]["columns"].keys()),
        "credit_notes": pd.DataFrame(credit_rows, columns=TABLE_SCHEMAS["credit_notes"]["columns"].keys()),
        "refunds": pd.DataFrame(refund_rows, columns=TABLE_SCHEMAS["refunds"]["columns"].keys()),
        "dunning_events": pd.DataFrame(dunning_rows, columns=TABLE_SCHEMAS["dunning_events"]["columns"].keys()),
    }
    return tables, {"invoice_outcomes": pd.DataFrame(invoice_outcomes)}


def generate_usage_success_support(
    config: dict[str, Any],
    account_tables: dict[str, pd.DataFrame],
    subscription_tables: dict[str, pd.DataFrame],
    billing_internal: dict[str, Any],
    subscription_internal: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    schedule = subscription_internal["subscription_schedule"].copy()
    accounts = account_tables["accounts"].set_index("account_id")
    users = subscription_tables["users"].copy()
    workspaces = subscription_tables["workspaces"].copy()
    invoice_outcomes = billing_internal["invoice_outcomes"]
    adjustments = _scenario_adjustments(config)
    sample_days = int(config["volumes"]["usage_sampling_days_per_month"])

    user_map = {account_id: group.to_dict("records") for account_id, group in users.groupby("account_id")}
    workspace_map = {account_id: group["workspace_id"].tolist() for account_id, group in workspaces.groupby("account_id")}

    integration_rows: list[dict[str, Any]] = []
    usage_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    work_order_rows: list[dict[str, Any]] = []
    ticket_rows: list[dict[str, Any]] = []
    nps_rows: list[dict[str, Any]] = []
    cs_rows: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []

    integration_id = product_event_id = work_order_id = ticket_id = nps_id = cs_id = 1

    integrations_by_account: dict[str, int] = defaultdict(int)
    for account_id in schedule["account_id"].drop_duplicates():
        segment = accounts.loc[account_id, "segment"]
        count_weights = {
            "micro": [0.78, 0.20, 0.02, 0.00], "small": [0.48, 0.38, 0.12, 0.02],
            "medium": [0.20, 0.40, 0.30, 0.10], "mid_market": [0.08, 0.25, 0.40, 0.27],
            "enterprise": [0.02, 0.10, 0.35, 0.53],
        }[segment]
        integration_count = int(rng.choice([0, 1, 2, 3], p=count_weights))
        integrations_by_account[account_id] = integration_count
        first_month = pd.Timestamp(schedule.loc[schedule["account_id"] == account_id, "month"].min())
        for _ in range(integration_count):
            connected = first_month + pd.Timedelta(days=int(rng.integers(10, 120)))
            integration_rows.append(
                {
                    "integration_id": prefixed_id("integration", integration_id), "account_id": account_id,
                    "integration_type": str(rng.choice(["erp", "accounting", "calendar", "crm", "identity", "webhook"])),
                    "connected_at": _iso_ts(connected), "disconnected_at": None,
                    "integration_status": "active", "monthly_sync_volume": int(rng.lognormal(7.2, 1.0)),
                }
            )
            integration_id += 1

    monthly_usage_summary: list[dict[str, Any]] = []
    for row in schedule.itertuples(index=False):
        account_id = row.account_id
        month = pd.Timestamp(row.month)
        account = accounts.loc[account_id]
        segment = account["segment"]
        account_users = user_map.get(account_id, [])
        if not account_users:
            continue
        seats = int(row.seats)
        integration_count = integrations_by_account[account_id]
        base_adoption = {
            "micro": 0.50, "small": 0.58, "medium": 0.66, "mid_market": 0.72, "enterprise": 0.76
        }[segment]
        base_adoption *= float(adjustments.get("adoption_multiplier", 1.0))
        if row.onboarding_complete:
            base_adoption += 0.14
        base_adoption += min(0.10, integration_count * 0.035)
        tenure_months = max(0, (month.year - pd.Timestamp(schedule.loc[schedule["account_id"] == account_id, "month"].min()).year) * 12 + month.month - pd.Timestamp(schedule.loc[schedule["account_id"] == account_id, "month"].min()).month)
        adoption = clamp(base_adoption + 0.08 * math.tanh(tenure_months / 5) + rng.normal(0, 0.06), 0.12, 0.98)
        utilisation = clamp(adoption * rng.uniform(0.78, 1.08), 0.08, 1.0)
        active_users_month = max(1, min(len(account_users), int(round(seats * utilisation))))
        days_in_month = month_end(month).day
        day_numbers = sorted(rng.choice(np.arange(1, days_in_month + 1), size=min(sample_days, days_in_month), replace=False))
        month_work_orders = 0
        month_completed = 0
        month_automation = 0
        month_sessions = 0
        month_feature_breadth: set[str] = set()

        for day_number in day_numbers:
            date = pd.Timestamp(month.year, month.month, int(day_number))
            active_users = max(1, int(round(active_users_month * rng.uniform(0.35, 0.95))))
            sessions = max(active_users, int(rng.poisson(active_users * rng.uniform(1.1, 2.4))))
            work_orders_created = int(rng.poisson(max(0.5, active_users * {"micro": 0.8, "small": 1.1, "medium": 1.5, "mid_market": 1.9, "enterprise": 2.3}[segment])))
            completion_rate = clamp(0.58 + adoption * 0.34 + rng.normal(0, 0.04), 0.40, 0.98)
            work_orders_completed = int(round(work_orders_created * completion_rate))
            automation_runs = int(rng.poisson(work_orders_created * (0.05 + 0.35 * adoption) * (1.25 if integration_count else 0.65)))
            api_calls = int(rng.poisson((integration_count + (1 if segment in {"mid_market", "enterprise"} else 0)) * 20 * adoption))
            documents = int(rng.poisson(max(0.1, work_orders_completed * 0.45)))
            feature_breadth = int(clamp(round(2 + adoption * 7 + integration_count + rng.normal(0, 1)), 1, 10))
            mobile_users = int(round(active_users * (0.72 if segment != "enterprise" else 0.62)))
            usage_rows.append(
                {
                    "account_id": account_id, "activity_date": _iso_date(date), "active_users": active_users,
                    "active_mobile_users": mobile_users, "sessions": sessions,
                    "work_orders_created": work_orders_created, "work_orders_completed": work_orders_completed,
                    "automation_runs": automation_runs, "api_calls": api_calls,
                    "documents_uploaded": documents, "feature_breadth": feature_breadth,
                }
            )
            month_work_orders += work_orders_created
            month_completed += work_orders_completed
            month_automation += automation_runs
            month_sessions += sessions

            # Detailed work orders preserve operational lifecycle without generating every aggregate count at scale.
            detailed_count = min(work_orders_created, 12)
            for _ in range(detailed_count):
                created = date + pd.Timedelta(hours=int(rng.integers(6, 18)), minutes=int(rng.integers(0, 60)))
                scheduled = created + pd.Timedelta(hours=int(rng.integers(2, 96)))
                completed_flag = rng.random() < completion_rate
                completion_minutes = int(clamp(rng.lognormal(4.3, 0.55), 15, 720)) if completed_flag else None
                completed = scheduled + pd.Timedelta(minutes=completion_minutes) if completed_flag else pd.NaT
                work_order_rows.append(
                    {
                        "work_order_id": prefixed_id("workorder", work_order_id), "account_id": account_id,
                        "workspace_id": str(rng.choice(workspace_map[account_id])), "created_at": _iso_ts(created),
                        "scheduled_at": _iso_ts(scheduled), "completed_at": _iso_ts(completed),
                        "status": "completed" if completed_flag else str(rng.choice(["scheduled", "cancelled"], p=[0.82, 0.18])),
                        "priority": str(rng.choice(["low", "normal", "high", "urgent"], p=[0.10, 0.60, 0.24, 0.06])),
                        "service_category": str(rng.choice(["maintenance", "repair", "installation", "inspection", "cleaning"])),
                        "assigned_users": int(rng.integers(1, 4)),
                        "customer_signature_flag": bool(completed_flag and rng.random() < 0.72),
                        "completion_minutes": completion_minutes,
                    }
                )
                work_order_id += 1

            event_count = min(10, max(2, int(round(sessions * 0.12))))
            selected_users = rng.choice(account_users, size=event_count, replace=True)
            for selected in selected_users:
                event_name, feature_area = FEATURES[int(rng.integers(0, len(FEATURES)))]
                month_feature_breadth.add(feature_area)
                event_rows.append(
                    {
                        "product_event_id": prefixed_id("event", product_event_id), "account_id": account_id,
                        "user_id": selected["user_id"], "event_at": _iso_ts(date + pd.Timedelta(seconds=int(rng.integers(0, 86400)))),
                        "event_name": event_name, "feature_area": feature_area,
                        "platform": "mobile" if selected["mobile_user_flag"] and rng.random() < 0.70 else "web",
                        "session_id": prefixed_id("session", product_event_id), "workspace_id": selected["workspace_id"],
                        "numeric_value": round(float(rng.lognormal(1.0, 0.8)), 4),
                    }
                )
                product_event_id += 1

        monthly_usage_summary.append(
            {
                "account_id": account_id, "month": month, "active_users": active_users_month,
                "seats": seats, "seat_utilisation": round(active_users_month / max(seats, 1), 4),
                "sessions": month_sessions, "work_orders": month_work_orders,
                "completed_work_orders": month_completed, "automation_runs": month_automation,
                "feature_breadth": len(month_feature_breadth), "adoption_score": adoption,
            }
        )

        ticket_lambda = float(config["behaviour"]["support_ticket_rate_per_account_month"])
        ticket_lambda *= float(adjustments.get("support_ticket_multiplier", 1.0))
        ticket_lambda *= {"micro": 0.65, "small": 0.85, "medium": 1.15, "mid_market": 1.55, "enterprise": 2.20}[segment]
        ticket_lambda *= 1.20 - adoption * 0.35
        ticket_count = int(rng.poisson(ticket_lambda))
        for _ in range(ticket_count):
            created = month + pd.Timedelta(days=int(rng.integers(0, month_end(month).day)), hours=int(rng.integers(7, 20)))
            priority = str(rng.choice(["low", "normal", "high", "urgent"], p=[0.12, 0.58, 0.24, 0.06]))
            response_hours = float(rng.lognormal(1.2 if priority in {"high", "urgent"} else 1.8, 0.55))
            resolution_hours = response_hours + float(rng.lognormal(2.5, 0.70))
            resolved = created + pd.Timedelta(hours=resolution_hours)
            escalated = bool(priority in {"high", "urgent"} and rng.random() < 0.28)
            csat = int(clamp(round(rng.normal(4.3 - (0.8 if escalated else 0), 0.8)), 1, 5))
            ticket_rows.append(
                {
                    "ticket_id": prefixed_id("ticket", ticket_id), "account_id": account_id,
                    "created_at": _iso_ts(created), "first_response_at": _iso_ts(created + pd.Timedelta(hours=response_hours)),
                    "resolved_at": _iso_ts(resolved), "closed_at": _iso_ts(resolved + pd.Timedelta(hours=8)),
                    "priority": priority,
                    "category": str(rng.choice(["billing", "configuration", "mobile", "integration", "reporting", "permissions", "performance"])),
                    "ticket_status": "closed", "channel": str(rng.choice(["email", "portal", "chat", "phone"], p=[0.34, 0.38, 0.20, 0.08])),
                    "escalated_flag": escalated, "reopened_count": int(rng.poisson(0.10 if not escalated else 0.35)),
                    "csat_score": csat,
                }
            )
            ticket_id += 1

    usage_summary = pd.DataFrame(monthly_usage_summary)
    tickets = pd.DataFrame(ticket_rows, columns=TABLE_SCHEMAS["support_tickets"]["columns"].keys())
    ticket_monthly = pd.DataFrame(columns=["account_id", "month", "tickets", "escalations", "avg_csat"])
    if not tickets.empty:
        tmp = tickets.copy()
        tmp["month"] = pd.to_datetime(tmp["created_at"]).dt.to_period("M").dt.to_timestamp()
        ticket_monthly = tmp.groupby(["account_id", "month"], as_index=False).agg(
            tickets=("ticket_id", "count"), escalations=("escalated_flag", "sum"), avg_csat=("csat_score", "mean")
        )

    invoice_monthly = invoice_outcomes.groupby(["account_id", "invoice_month"], as_index=False).agg(
        overdue_invoices=("invoice_status", lambda s: int((s != "paid").sum())),
        failed_attempts=("first_attempt_failed", "sum"), recovered=("recovered", "sum")
    ).rename(columns={"invoice_month": "month"}) if not invoice_outcomes.empty else pd.DataFrame(columns=["account_id", "month", "overdue_invoices", "failed_attempts", "recovered"])

    health = usage_summary.merge(ticket_monthly, on=["account_id", "month"], how="left").merge(invoice_monthly, on=["account_id", "month"], how="left")
    for column in ["tickets", "escalations", "avg_csat", "overdue_invoices", "failed_attempts", "recovered"]:
        if column not in health:
            health[column] = 0
        health[column] = health[column].fillna(0)
    for row in health.itertuples(index=False):
        usage_score = clamp(10 + 50 * row.seat_utilisation + 3.0 * row.feature_breadth + 5 * min(row.automation_runs / 20, 1), 0, 100)
        support_score = clamp(92 - row.tickets * 10 - row.escalations * 20 + max(0, row.avg_csat - 3) * 4, 0, 100)
        payment_score = clamp(95 - row.overdue_invoices * 48 - row.failed_attempts * 14 + row.recovered * 8, 0, 100)
        relationship_score = clamp(48 + (11 if accounts.loc[row.account_id, "sales_motion"] != "self_service" else 0) + rng.normal(0, 12), 0, 100)
        health_score = 0.50 * usage_score + 0.15 * support_score + 0.20 * payment_score + 0.15 * relationship_score
        segment = "healthy" if health_score >= 75 else "watch" if health_score >= 62 else "at_risk" if health_score >= 45 else "critical"
        health_rows.append(
            {
                "account_id": row.account_id, "health_month": _iso_date(row.month),
                "health_score": round(health_score, 2), "health_segment": segment,
                "usage_score": round(usage_score, 2), "support_score": round(support_score, 2),
                "payment_score": round(payment_score, 2), "relationship_score": round(relationship_score, 2),
                "renewal_risk_flag": segment in {"at_risk", "critical"},
            }
        )
        if segment in {"at_risk", "critical"} and rng.random() < 0.38:
            interaction_at = pd.Timestamp(row.month) + pd.Timedelta(days=int(rng.integers(5, 25)))
            improvement = float(rng.uniform(3, 14))
            cs_rows.append(
                {
                    "cs_interaction_id": prefixed_id("cs", cs_id), "account_id": row.account_id,
                    "interaction_at": _iso_ts(interaction_at),
                    "interaction_type": str(rng.choice(["risk_review", "adoption_workshop", "executive_check_in", "renewal_planning"])),
                    "reason": segment, "outcome": str(rng.choice(["action_plan", "resolved", "follow_up_required"], p=[0.52, 0.27, 0.21])),
                    "health_score_before": round(health_score, 2),
                    "health_score_after": round(clamp(health_score + improvement, 0, 100), 2),
                    "owner_team": f"{accounts.loc[row.account_id, 'region_id']}_customer_success",
                }
            )
            cs_id += 1

    # NPS is sampled from health history and therefore follows product and service experience.
    health_frame = pd.DataFrame(health_rows)
    if not health_frame.empty:
        for account_id, group in health_frame.groupby("account_id"):
            if rng.random() >= float(config["behaviour"]["nps_response_rate"]):
                continue
            latest = group.iloc[-1]
            score = int(clamp(round((latest["health_score"] - 20) / 8 + rng.normal(0, 1.4)), 0, 10))
            nps_group = "promoter" if score >= 9 else "passive" if score >= 7 else "detractor"
            nps_rows.append(
                {
                    "nps_response_id": prefixed_id("nps", nps_id), "account_id": account_id,
                    "response_date": latest["health_month"], "nps_score": score, "nps_group": nps_group,
                    "response_channel": str(rng.choice(["in_app", "email"])),
                    "comment_theme": str(rng.choice(
                        ["ease_of_use", "mobile_experience", "support", "reporting", "integrations", "pricing"]
                    )),
                }
            )
            nps_id += 1

    tables = {
        "integrations": pd.DataFrame(integration_rows, columns=TABLE_SCHEMAS["integrations"]["columns"].keys()),
        "account_usage_daily": pd.DataFrame(usage_rows, columns=TABLE_SCHEMAS["account_usage_daily"]["columns"].keys()),
        "product_events": pd.DataFrame(event_rows, columns=TABLE_SCHEMAS["product_events"]["columns"].keys()),
        "work_orders": pd.DataFrame(work_order_rows, columns=TABLE_SCHEMAS["work_orders"]["columns"].keys()),
        "support_tickets": tickets,
        "nps_responses": pd.DataFrame(nps_rows, columns=TABLE_SCHEMAS["nps_responses"]["columns"].keys()),
        "customer_success_interactions": pd.DataFrame(cs_rows, columns=TABLE_SCHEMAS["customer_success_interactions"]["columns"].keys()),
        "account_health_history": health_frame,
    }
    return tables, {"monthly_usage_summary": usage_summary}


def generate_experiments(
    config: dict[str, Any],
    account_tables: dict[str, pd.DataFrame],
    subscription_tables: dict[str, pd.DataFrame],
    usage_internal: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, pd.DataFrame]:
    accounts = account_tables["accounts"]
    subscriptions = subscription_tables["subscriptions"]
    usage = usage_internal["monthly_usage_summary"]
    end = pd.Timestamp(config["project"]["history_end"])
    definitions = [
        ("exp_onboarding", "Guided onboarding checklist", config["scenarios"]["onboarding_experiment_start"], "30_day_activation", "support_tickets_30d", 0.05),
        ("exp_annual_discount", "Annual plan discount framing", config["scenarios"]["annual_discount_experiment_start"], "annual_plan_selection", "discounted_arpa", 0.04),
        ("exp_automation_prompt", "Automation feature adoption prompt", config["scenarios"]["automation_prompt_experiment_start"], "automation_adoption", "seven_day_retention", 0.06),
        ("exp_cs_intervention", "Customer success renewal intervention", config["scenarios"]["customer_success_experiment_start"], "renewal_rate", "contraction_rate", 0.05),
    ]
    experiment_rows = []
    assignment_rows = []
    exposure_rows = []
    outcome_rows = []
    assignment_id = exposure_id = outcome_id = 1
    subscriptions_by_account = subscriptions.set_index("account_id")

    for experiment_id, name, start_value, primary_metric, guardrail, mde in definitions:
        start = pd.Timestamp(start_value)
        experiment_end = min(end, start + pd.Timedelta(days=120))
        experiment_rows.append(
            {
                "experiment_id": experiment_id, "experiment_name": name, "start_date": _iso_date(start),
                "end_date": _iso_date(experiment_end), "unit_of_randomisation": "account",
                "primary_metric": primary_metric, "guardrail_metric": guardrail,
                "minimum_detectable_effect": mde, "status": "completed" if experiment_end < end else "running",
            }
        )
        eligible = accounts[pd.to_datetime(accounts["created_at"]) <= experiment_end].copy()
        if experiment_id == "exp_cs_intervention":
            eligible = eligible[eligible["segment"].isin(["medium", "mid_market", "enterprise"])]
        if experiment_id == "exp_annual_discount":
            eligible = eligible[eligible["sales_motion"] == "self_service"]
        sample_size = min(len(eligible), max(80, int(len(eligible) * 0.35)))
        if sample_size == 0:
            continue
        eligible = eligible.sample(n=sample_size, random_state=int(rng.integers(1, 2_000_000_000)))
        variants = np.array(["control", "treatment"] * ((sample_size + 1) // 2))[:sample_size]
        rng.shuffle(variants)
        for row, variant in zip(eligible.itertuples(index=False), variants, strict=False):
            assigned_at = start + pd.Timedelta(days=int(rng.integers(0, max(1, (experiment_end - start).days + 1))))
            aid = prefixed_id("assignment", assignment_id)
            assignment_rows.append(
                {
                    "assignment_id": aid, "experiment_id": experiment_id, "account_id": row.account_id,
                    "variant": variant, "assigned_at": _iso_ts(assigned_at), "eligible_flag": True,
                    "stratum": f"{row.country_code}|{row.segment}",
                }
            )
            exposure_probability = 0.90 if experiment_id != "exp_cs_intervention" else 0.82
            exposed = rng.random() < exposure_probability
            if exposed:
                exposure_rows.append(
                    {
                        "exposure_id": prefixed_id("exposure", exposure_id), "assignment_id": aid,
                        "exposed_at": _iso_ts(assigned_at + pd.Timedelta(hours=int(rng.integers(1, 96)))),
                        "exposure_surface": {
                            "exp_onboarding": "onboarding_checklist", "exp_annual_discount": "pricing_page",
                            "exp_automation_prompt": "in_app_prompt", "exp_cs_intervention": "customer_success_call",
                        }[experiment_id],
                        "exposure_count": int(rng.integers(1, 5)),
                    }
                )
                exposure_id += 1

            treatment = variant == "treatment" and exposed
            if experiment_id == "exp_onboarding":
                base = 0.63 + (0.06 if treatment else 0.0)
                primary = float(rng.random() < base)
                guardrail_value = float(rng.poisson(0.42 - (0.04 if treatment else 0.0)))
                revenue = float(rng.lognormal(6.0, 0.6)) * primary
            elif experiment_id == "exp_annual_discount":
                base = 0.44 + (0.055 if treatment else 0.0)
                primary = float(rng.random() < base)
                guardrail_value = float(rng.normal(420 - (18 if treatment else 0), 95))
                revenue = max(0.0, guardrail_value * 12 * primary)
            elif experiment_id == "exp_automation_prompt":
                base = 0.29 + (0.075 if treatment else 0.0)
                primary = float(rng.random() < base)
                guardrail_value = float(rng.random() < (0.74 + (0.015 if treatment else 0.0)))
                revenue = float(rng.lognormal(6.4, 0.65))
            else:
                base = 0.78 + (0.06 if treatment else 0.0)
                primary = float(rng.random() < base)
                guardrail_value = float(rng.random() < (0.14 - (0.015 if treatment else 0.0)))
                revenue = float(rng.lognormal(7.0, 0.7)) * primary
            outcome_rows.append(
                {
                    "outcome_id": prefixed_id("outcome", outcome_id), "assignment_id": aid,
                    "observation_end": _iso_date(min(end, assigned_at + pd.Timedelta(days=90))),
                    "primary_outcome": round(primary, 6), "guardrail_outcome": round(guardrail_value, 6),
                    "revenue_outcome_eur": round(revenue, 2),
                }
            )
            outcome_id += 1
            assignment_id += 1

    return {
        "experiments": pd.DataFrame(experiment_rows, columns=TABLE_SCHEMAS["experiments"]["columns"].keys()),
        "experiment_assignments": pd.DataFrame(assignment_rows, columns=TABLE_SCHEMAS["experiment_assignments"]["columns"].keys()),
        "experiment_exposures": pd.DataFrame(exposure_rows, columns=TABLE_SCHEMAS["experiment_exposures"]["columns"].keys()),
        "experiment_outcomes": pd.DataFrame(outcome_rows, columns=TABLE_SCHEMAS["experiment_outcomes"]["columns"].keys()),
    }


def generate_dataset(config: dict[str, Any]) -> GeneratedDataset:
    rng = np.random.default_rng(int(config["project"]["seed"]))
    reference = generate_reference(config, rng)
    account_tables, account_internal = generate_partners_campaigns_accounts(config, reference, rng)
    subscription_tables, subscription_internal = generate_subscriptions_users(
        config, reference, account_internal, rng
    )
    billing_tables, billing_internal = generate_billing(
        config, reference, subscription_tables, subscription_internal, rng
    )
    usage_tables, usage_internal = generate_usage_success_support(
        config, account_tables, subscription_tables, billing_internal, subscription_internal, rng
    )
    experiment_tables = generate_experiments(
        config, account_tables, subscription_tables, usage_internal, rng
    )
    tables = {}
    for block in [reference, account_tables, subscription_tables, billing_tables, usage_tables, experiment_tables]:
        tables.update(block)
    # Ensure every declared source table is present and column order follows the contract.
    for table_name, schema in TABLE_SCHEMAS.items():
        columns = list(schema["columns"])
        frame = tables.get(table_name, pd.DataFrame(columns=columns))
        for column in columns:
            if column not in frame:
                frame[column] = None
        tables[table_name] = frame[columns]
    return GeneratedDataset(
        tables=tables,
        internal={
            **subscription_internal,
            **billing_internal,
            **usage_internal,
            "effective_config": config,
        },
    )


def _prepare_frame_for_csv(table_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Return a CSV-safe frame that preserves governed integer formatting.

    Nullable integer columns often become floating-point columns inside pandas,
    which would otherwise be written as ``12.0``. PostgreSQL ``BIGINT`` and the
    published data contracts expect integer text, so integral values are
    normalised to pandas' nullable ``Int64`` dtype before serialisation.
    """
    prepared = frame.copy()
    schema = TABLE_SCHEMAS[table_name]
    for column, logical_type in schema["columns"].items():
        if logical_type != "integer":
            continue
        original = prepared[column]
        populated = original.notna() & original.astype(str).str.strip().ne("")
        numeric = pd.to_numeric(original, errors="coerce")
        non_numeric = populated & numeric.isna()
        if non_numeric.any():
            example = original.loc[non_numeric].iloc[0]
            raise ValueError(
                f"Table {table_name}.{column} contains a non-numeric value: {example!r}"
            )
        integral = numeric.isna() | np.isclose(numeric % 1, 0.0)
        if not bool(integral.all()):
            example = original.loc[~integral].iloc[0]
            raise ValueError(
                f"Table {table_name}.{column} contains a non-integral value: {example!r}"
            )
        prepared[column] = numeric.round().astype("Int64")
    return prepared


def write_dataset(dataset: GeneratedDataset, output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"tables": {}, "total_rows": 0}
    for table_name in TABLE_SCHEMAS:
        frame = _prepare_frame_for_csv(table_name, dataset.tables[table_name])
        path = output / f"{table_name}.csv"
        frame.to_csv(path, index=False, na_rep="", lineterminator="\n")
        rows = int(len(frame))
        manifest["tables"][table_name] = {
            "file": path.name,
            "rows": rows,
            "columns": list(frame.columns),
            "sha256": dataframe_fingerprint(frame),
        }
        manifest["total_rows"] += rows
    write_json(output / "manifest.json", manifest)
    write_json(output / "effective_config.json", dataset.internal["effective_config"])
    return manifest
