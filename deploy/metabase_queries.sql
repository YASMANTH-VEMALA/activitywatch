-- ============================================================================
-- Metabase Cockpit Queries (Pre-configured for PostgreSQL)
-- Target Views: v_cockpit_metrics, v_open_flags_summary, v_project_ai_spend
-- ============================================================================

-- Card 1: Team Utilization Table
-- Question: "What is the daily active vs office utilization by team member?"
SELECT 
    work_date,
    full_name,
    role,
    department,
    active_hours,
    office_hours,
    utilization_percentage,
    ai_spend_usd,
    open_flags_count
FROM v_cockpit_metrics
WHERE work_date >= CURRENT_DATE - INTERVAL '14 days'
ORDER BY work_date DESC, utilization_percentage ASC;

-- Card 2: Open Discrepancies by Rule Code (R01, R02, R05, R07)
-- Question: "How many active discrepancy flags exist per rule?"
SELECT 
    rule_code,
    COUNT(*) AS total_open_flags,
    SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) AS high_severity_count,
    SUM(CASE WHEN severity = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_severity_count
FROM v_open_flags_summary
GROUP BY rule_code
ORDER BY total_open_flags DESC;

-- Card 3: AI Financial Governance (Serious vs Research Spend)
-- Question: "Are project AI budgets on track across Serious and Research initiatives?"
SELECT 
    project_name,
    classification,
    monthly_budget_usd,
    current_spend_usd,
    budget_utilized_pct,
    total_requests
FROM v_project_ai_spend
ORDER BY current_spend_usd DESC;

-- Card 4: Daily Aggregate Utilization Trend
-- Question: "What is the average company-wide workstation utilization over time?"
SELECT 
    work_date,
    ROUND(AVG(utilization_percentage), 1) AS avg_utilization_pct,
    ROUND(SUM(active_hours), 1) AS total_active_hours,
    ROUND(SUM(office_hours), 1) AS total_office_hours,
    ROUND(SUM(ai_spend_usd), 2) AS total_ai_spend_usd
FROM v_cockpit_metrics
GROUP BY work_date
ORDER BY work_date ASC;

