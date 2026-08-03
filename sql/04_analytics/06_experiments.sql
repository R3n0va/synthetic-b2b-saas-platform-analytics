CREATE OR REPLACE VIEW analytics.experiment_assignment_integrity AS
SELECT
    e.experiment_id,
    e.experiment_name,
    a.variant,
    count(*) AS assignments,
    count(*)::numeric / sum(count(*)) OVER (PARTITION BY e.experiment_id) AS assignment_share,
    count(DISTINCT a.account_id) AS unique_accounts,
    count(*) - count(DISTINCT a.account_id) AS duplicate_assignments
FROM core.experiments e
JOIN core.experiment_assignments a USING (experiment_id)
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.experiment_exposure AS
SELECT
    e.experiment_id,
    e.experiment_name,
    a.variant,
    count(DISTINCT a.assignment_id) AS assigned,
    count(DISTINCT x.assignment_id) AS exposed,
    count(DISTINCT x.assignment_id)::numeric / nullif(count(DISTINCT a.assignment_id), 0) AS exposure_rate,
    avg(x.exposure_count) AS average_exposures
FROM core.experiments e
JOIN core.experiment_assignments a USING (experiment_id)
LEFT JOIN core.experiment_exposures x USING (assignment_id)
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.experiment_outcomes AS
SELECT
    ea.experiment_id,
    ea.experiment_name,
    ea.variant,
    ea.assigned_accounts,
    ea.exposed_accounts,
    ea.primary_mean,
    ea.guardrail_mean,
    ea.average_revenue_outcome_eur,
    ea.primary_mean - max(ea.primary_mean) FILTER (WHERE ea.variant = 'control') OVER (PARTITION BY ea.experiment_id) AS absolute_effect_vs_control,
    ea.primary_mean / nullif(max(ea.primary_mean) FILTER (WHERE ea.variant = 'control') OVER (PARTITION BY ea.experiment_id), 0) - 1 AS relative_effect_vs_control
FROM mart.experiment_analysis ea;

CREATE OR REPLACE VIEW analytics.experiment_segment_effects AS
SELECT
    a.experiment_id,
    a.variant,
    split_part(a.stratum, '|', 1) AS country_code,
    split_part(a.stratum, '|', 2) AS segment,
    count(*) AS observations,
    avg(o.primary_outcome) AS primary_mean,
    avg(o.guardrail_outcome) AS guardrail_mean,
    avg(o.revenue_outcome_eur) AS average_revenue_outcome_eur
FROM core.experiment_assignments a
JOIN core.experiment_exposures x USING (assignment_id)
JOIN core.experiment_outcomes o USING (assignment_id)
GROUP BY 1,2,3,4;
