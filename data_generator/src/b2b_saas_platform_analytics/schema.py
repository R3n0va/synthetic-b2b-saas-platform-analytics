from __future__ import annotations

from typing import Any

# Contract types: string, integer, decimal, boolean, date, timestamp.
TABLE_SCHEMAS: dict[str, dict[str, Any]] = {
    "regions": {
        "primary_key": ["region_id"],
        "columns": {
            "region_id": "string", "region_name": "string", "commercial_owner": "string"
        },
    },
    "countries": {
        "primary_key": ["country_code"],
        "foreign_keys": [{"columns": ["region_id"], "references": "regions(region_id)"}],
        "columns": {
            "country_code": "string", "country_name": "string", "region_id": "string",
            "currency_code": "string", "vat_rate": "decimal", "language_code": "string"
        },
    },
    "currencies": {
        "primary_key": ["currency_code"],
        "columns": {"currency_code": "string", "currency_name": "string", "minor_units": "integer"},
    },
    "fx_rates": {
        "primary_key": ["rate_date", "currency_code"],
        "foreign_keys": [{"columns": ["currency_code"], "references": "currencies(currency_code)"}],
        "columns": {"rate_date": "date", "currency_code": "string", "eur_rate": "decimal"},
    },
    "plans": {
        "primary_key": ["plan_id"],
        "columns": {
            "plan_id": "string", "plan_name": "string", "plan_rank": "integer",
            "included_seats": "integer", "active_flag": "boolean"
        },
    },
    "plan_prices": {
        "primary_key": ["plan_price_id"],
        "foreign_keys": [
            {"columns": ["plan_id"], "references": "plans(plan_id)"},
            {"columns": ["currency_code"], "references": "currencies(currency_code)"},
        ],
        "columns": {
            "plan_price_id": "string", "plan_id": "string", "country_code": "string",
            "currency_code": "string", "billing_frequency": "string", "effective_start": "date",
            "effective_end": "date", "base_price": "decimal", "seat_price": "decimal",
            "annual_discount_pct": "decimal"
        },
    },
    "add_ons": {
        "primary_key": ["add_on_id"],
        "columns": {
            "add_on_id": "string", "add_on_name": "string", "monthly_price_eur": "decimal",
            "category": "string", "active_flag": "boolean"
        },
    },
    "accounts": {
        "primary_key": ["account_id"],
        "foreign_keys": [{"columns": ["country_code"], "references": "countries(country_code)"}],
        "columns": {
            "account_id": "string", "account_name": "string", "created_at": "timestamp",
            "country_code": "string", "region_id": "string", "industry": "string",
            "segment": "string", "employee_band": "string", "acquisition_channel": "string",
            "sales_motion": "string", "partner_id": "string", "account_status": "string",
            "legal_currency": "string", "tax_id_present": "boolean"
        },
    },
    "partners": {
        "primary_key": ["partner_id"],
        "columns": {
            "partner_id": "string", "partner_name": "string", "partner_type": "string",
            "country_code": "string", "active_from": "date", "active_flag": "boolean"
        },
    },
    "leads": {
        "primary_key": ["lead_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "lead_id": "string", "account_id": "string", "created_at": "timestamp",
            "source_channel": "string", "lead_status": "string", "mql_at": "timestamp",
            "sql_at": "timestamp", "lead_score": "integer", "campaign_id": "string"
        },
    },
    "marketing_campaigns": {
        "primary_key": ["campaign_id"],
        "columns": {
            "campaign_id": "string", "campaign_name": "string", "channel": "string",
            "country_code": "string", "start_date": "date", "end_date": "date",
            "spend_local": "decimal", "currency_code": "string", "spend_eur": "decimal"
        },
    },
    "opportunities": {
        "primary_key": ["opportunity_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "opportunity_id": "string", "account_id": "string", "created_at": "timestamp",
            "close_date": "date", "stage": "string", "status": "string", "owner_team": "string",
            "expected_arr_eur": "decimal", "probability": "decimal", "loss_reason": "string"
        },
    },
    "opportunity_stage_history": {
        "primary_key": ["stage_event_id"],
        "foreign_keys": [{"columns": ["opportunity_id"], "references": "opportunities(opportunity_id)"}],
        "columns": {
            "stage_event_id": "string", "opportunity_id": "string", "stage_name": "string",
            "entered_at": "timestamp", "exited_at": "timestamp", "stage_sequence": "integer"
        },
    },
    "workspaces": {
        "primary_key": ["workspace_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "workspace_id": "string", "account_id": "string", "workspace_name": "string",
            "created_at": "timestamp", "country_code": "string", "active_flag": "boolean"
        },
    },
    "users": {
        "primary_key": ["user_id"],
        "foreign_keys": [
            {"columns": ["account_id"], "references": "accounts(account_id)"},
            {"columns": ["workspace_id"], "references": "workspaces(workspace_id)"},
        ],
        "columns": {
            "user_id": "string", "account_id": "string", "workspace_id": "string",
            "created_at": "timestamp", "role_name": "string", "user_status": "string",
            "invited_at": "timestamp", "activated_at": "timestamp", "deactivated_at": "timestamp",
            "mobile_user_flag": "boolean"
        },
    },
    "contracts": {
        "primary_key": ["contract_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "contract_id": "string", "account_id": "string", "contract_number": "string",
            "signed_date": "date", "start_date": "date", "end_date": "date",
            "auto_renew_flag": "boolean", "contract_term_months": "integer",
            "billing_frequency": "string", "currency_code": "string", "discount_pct": "decimal",
            "contract_status": "string", "sales_motion": "string"
        },
    },
    "subscriptions": {
        "primary_key": ["subscription_id"],
        "foreign_keys": [
            {"columns": ["account_id"], "references": "accounts(account_id)"},
            {"columns": ["contract_id"], "references": "contracts(contract_id)"},
            {"columns": ["plan_id"], "references": "plans(plan_id)"},
        ],
        "columns": {
            "subscription_id": "string", "account_id": "string", "contract_id": "string",
            "plan_id": "string", "trial_start_date": "date", "trial_end_date": "date",
            "subscription_start_date": "date", "current_status": "string",
            "cancel_requested_date": "date", "ended_date": "date", "churn_type": "string",
            "billing_frequency": "string", "currency_code": "string"
        },
    },
    "subscription_items": {
        "primary_key": ["subscription_item_id"],
        "foreign_keys": [{"columns": ["subscription_id"], "references": "subscriptions(subscription_id)"}],
        "columns": {
            "subscription_item_id": "string", "subscription_id": "string", "item_type": "string",
            "plan_id": "string", "add_on_id": "string", "quantity": "integer",
            "unit_price_local": "decimal", "discount_pct": "decimal", "effective_start": "date",
            "effective_end": "date", "mrr_local": "decimal", "mrr_eur": "decimal"
        },
    },
    "subscription_events": {
        "primary_key": ["subscription_event_id"],
        "foreign_keys": [{"columns": ["subscription_id"], "references": "subscriptions(subscription_id)"}],
        "columns": {
            "subscription_event_id": "string", "subscription_id": "string", "event_at": "timestamp",
            "event_type": "string", "previous_plan_id": "string", "new_plan_id": "string",
            "previous_quantity": "integer", "new_quantity": "integer", "mrr_change_eur": "decimal",
            "event_reason": "string", "initiated_by": "string"
        },
    },
    "renewals": {
        "primary_key": ["renewal_id"],
        "foreign_keys": [{"columns": ["subscription_id"], "references": "subscriptions(subscription_id)"}],
        "columns": {
            "renewal_id": "string", "subscription_id": "string", "renewal_due_date": "date",
            "decision_date": "date", "renewal_status": "string", "renewal_arr_eur": "decimal",
            "renewal_probability": "decimal", "risk_reason": "string"
        },
    },
    "invoices": {
        "primary_key": ["invoice_id"],
        "foreign_keys": [
            {"columns": ["account_id"], "references": "accounts(account_id)"},
            {"columns": ["subscription_id"], "references": "subscriptions(subscription_id)"},
        ],
        "columns": {
            "invoice_id": "string", "account_id": "string", "subscription_id": "string",
            "invoice_number": "string", "invoice_date": "date", "due_date": "date",
            "service_period_start": "date", "service_period_end": "date", "currency_code": "string",
            "subtotal_local": "decimal", "tax_local": "decimal", "total_local": "decimal",
            "total_eur": "decimal", "invoice_status": "string", "paid_date": "date"
        },
    },
    "invoice_lines": {
        "primary_key": ["invoice_line_id"],
        "foreign_keys": [{"columns": ["invoice_id"], "references": "invoices(invoice_id)"}],
        "columns": {
            "invoice_line_id": "string", "invoice_id": "string", "line_type": "string",
            "description": "string", "quantity": "decimal", "unit_price_local": "decimal",
            "discount_local": "decimal", "line_total_local": "decimal", "service_period_start": "date",
            "service_period_end": "date", "subscription_item_id": "string"
        },
    },
    "payment_methods": {
        "primary_key": ["payment_method_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "payment_method_id": "string", "account_id": "string", "method_type": "string",
            "provider": "string", "created_at": "timestamp", "expiry_month": "integer",
            "expiry_year": "integer", "active_flag": "boolean"
        },
    },
    "payment_attempts": {
        "primary_key": ["payment_attempt_id"],
        "foreign_keys": [
            {"columns": ["invoice_id"], "references": "invoices(invoice_id)"},
            {"columns": ["payment_method_id"], "references": "payment_methods(payment_method_id)"},
        ],
        "columns": {
            "payment_attempt_id": "string", "invoice_id": "string", "payment_method_id": "string",
            "attempt_at": "timestamp", "attempt_number": "integer", "amount_local": "decimal",
            "currency_code": "string", "attempt_status": "string", "failure_reason": "string",
            "provider_response_code": "string"
        },
    },
    "payments": {
        "primary_key": ["payment_id"],
        "foreign_keys": [
            {"columns": ["invoice_id"], "references": "invoices(invoice_id)"},
            {"columns": ["payment_attempt_id"], "references": "payment_attempts(payment_attempt_id)"},
        ],
        "columns": {
            "payment_id": "string", "invoice_id": "string", "payment_attempt_id": "string",
            "captured_at": "timestamp", "amount_local": "decimal", "currency_code": "string",
            "amount_eur": "decimal", "payment_status": "string", "settlement_date": "date"
        },
    },
    "credit_notes": {
        "primary_key": ["credit_note_id"],
        "foreign_keys": [{"columns": ["invoice_id"], "references": "invoices(invoice_id)"}],
        "columns": {
            "credit_note_id": "string", "invoice_id": "string", "issued_date": "date",
            "reason": "string", "amount_local": "decimal", "amount_eur": "decimal",
            "credit_note_status": "string"
        },
    },
    "refunds": {
        "primary_key": ["refund_id"],
        "foreign_keys": [{"columns": ["payment_id"], "references": "payments(payment_id)"}],
        "columns": {
            "refund_id": "string", "payment_id": "string", "requested_at": "timestamp",
            "processed_at": "timestamp", "amount_local": "decimal", "amount_eur": "decimal",
            "reason": "string", "refund_status": "string"
        },
    },
    "dunning_events": {
        "primary_key": ["dunning_event_id"],
        "foreign_keys": [{"columns": ["invoice_id"], "references": "invoices(invoice_id)"}],
        "columns": {
            "dunning_event_id": "string", "invoice_id": "string", "event_at": "timestamp",
            "dunning_step": "integer", "channel": "string", "event_status": "string",
            "recovered_after_event_flag": "boolean"
        },
    },
    "product_events": {
        "primary_key": ["product_event_id"],
        "foreign_keys": [
            {"columns": ["account_id"], "references": "accounts(account_id)"},
            {"columns": ["user_id"], "references": "users(user_id)"},
        ],
        "columns": {
            "product_event_id": "string", "account_id": "string", "user_id": "string",
            "event_at": "timestamp", "event_name": "string", "feature_area": "string",
            "platform": "string", "session_id": "string", "workspace_id": "string",
            "numeric_value": "decimal"
        },
    },
    "account_usage_daily": {
        "primary_key": ["account_id", "activity_date"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "account_id": "string", "activity_date": "date", "active_users": "integer",
            "active_mobile_users": "integer", "sessions": "integer", "work_orders_created": "integer",
            "work_orders_completed": "integer", "automation_runs": "integer", "api_calls": "integer",
            "documents_uploaded": "integer", "feature_breadth": "integer"
        },
    },
    "integrations": {
        "primary_key": ["integration_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "integration_id": "string", "account_id": "string", "integration_type": "string",
            "connected_at": "timestamp", "disconnected_at": "timestamp", "integration_status": "string",
            "monthly_sync_volume": "integer"
        },
    },
    "work_orders": {
        "primary_key": ["work_order_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "work_order_id": "string", "account_id": "string", "workspace_id": "string",
            "created_at": "timestamp", "scheduled_at": "timestamp", "completed_at": "timestamp",
            "status": "string", "priority": "string", "service_category": "string",
            "assigned_users": "integer", "customer_signature_flag": "boolean",
            "completion_minutes": "integer"
        },
    },
    "onboarding_tasks": {
        "primary_key": ["onboarding_task_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "onboarding_task_id": "string", "account_id": "string", "task_name": "string",
            "task_sequence": "integer", "due_date": "date", "completed_at": "timestamp",
            "task_status": "string", "owner_type": "string"
        },
    },
    "customer_success_interactions": {
        "primary_key": ["cs_interaction_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "cs_interaction_id": "string", "account_id": "string", "interaction_at": "timestamp",
            "interaction_type": "string", "reason": "string", "outcome": "string",
            "health_score_before": "decimal", "health_score_after": "decimal", "owner_team": "string"
        },
    },
    "support_tickets": {
        "primary_key": ["ticket_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "ticket_id": "string", "account_id": "string", "created_at": "timestamp",
            "first_response_at": "timestamp", "resolved_at": "timestamp", "closed_at": "timestamp",
            "priority": "string", "category": "string", "ticket_status": "string",
            "channel": "string", "escalated_flag": "boolean", "reopened_count": "integer",
            "csat_score": "integer"
        },
    },
    "nps_responses": {
        "primary_key": ["nps_response_id"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "nps_response_id": "string", "account_id": "string", "response_date": "date",
            "nps_score": "integer", "nps_group": "string", "response_channel": "string",
            "comment_theme": "string"
        },
    },
    "account_health_history": {
        "primary_key": ["account_id", "health_month"],
        "foreign_keys": [{"columns": ["account_id"], "references": "accounts(account_id)"}],
        "columns": {
            "account_id": "string", "health_month": "date", "health_score": "decimal",
            "health_segment": "string", "usage_score": "decimal", "support_score": "decimal",
            "payment_score": "decimal", "relationship_score": "decimal", "renewal_risk_flag": "boolean"
        },
    },
    "experiments": {
        "primary_key": ["experiment_id"],
        "columns": {
            "experiment_id": "string", "experiment_name": "string", "start_date": "date",
            "end_date": "date", "unit_of_randomisation": "string", "primary_metric": "string",
            "guardrail_metric": "string", "minimum_detectable_effect": "decimal", "status": "string"
        },
    },
    "experiment_assignments": {
        "primary_key": ["assignment_id"],
        "foreign_keys": [
            {"columns": ["experiment_id"], "references": "experiments(experiment_id)"},
            {"columns": ["account_id"], "references": "accounts(account_id)"},
        ],
        "columns": {
            "assignment_id": "string", "experiment_id": "string", "account_id": "string",
            "variant": "string", "assigned_at": "timestamp", "eligible_flag": "boolean",
            "stratum": "string"
        },
    },
    "experiment_exposures": {
        "primary_key": ["exposure_id"],
        "foreign_keys": [{"columns": ["assignment_id"], "references": "experiment_assignments(assignment_id)"}],
        "columns": {
            "exposure_id": "string", "assignment_id": "string", "exposed_at": "timestamp",
            "exposure_surface": "string", "exposure_count": "integer"
        },
    },
    "experiment_outcomes": {
        "primary_key": ["outcome_id"],
        "foreign_keys": [{"columns": ["assignment_id"], "references": "experiment_assignments(assignment_id)"}],
        "columns": {
            "outcome_id": "string", "assignment_id": "string", "observation_end": "date",
            "primary_outcome": "decimal", "guardrail_outcome": "decimal", "revenue_outcome_eur": "decimal"
        },
    },
}


def postgres_type(logical_type: str) -> str:
    return {
        "string": "text",
        "integer": "bigint",
        "decimal": "numeric(20, 6)",
        "boolean": "boolean",
        "date": "date",
        "timestamp": "timestamp without time zone",
    }[logical_type]
