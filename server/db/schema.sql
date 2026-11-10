-- ============================================================================
-- Enterprise Workforce & AI Intelligence Platform Database Schema
-- Stage A (Platform, Capture & Intelligence) + Stage B (Work Surfaces)
-- Database: PostgreSQL 15+ / TimescaleDB / Neon
-- Standard Timezone: Stored as TIMESTAMPTZ (UTC), Projected in Asia/Kolkata
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Tracking Policies
CREATE TABLE IF NOT EXISTS tracking_policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    standard_start_time TIME NOT NULL DEFAULT '09:30:00',
    standard_end_time TIME NOT NULL DEFAULT '18:30:00',
    punch_grace_minutes_r01 INT NOT NULL DEFAULT 45,        -- Flag R01 if no laptop activity within 45m of punch-in
    max_idle_minutes_r02 INT NOT NULL DEFAULT 90,           -- Flag R02 if cumulative idle > 90m
    single_idle_block_limit_r02 INT NOT NULL DEFAULT 45,    -- Flag R02 if single idle span > 45m
    ai_idle_token_threshold_r05 INT NOT NULL DEFAULT 500,   -- Flag R05 if tokens > 500 while idle
    approved_ai_tools JSONB NOT NULL DEFAULT '["litellm", "internal-portal", "claude-team"]'::jsonb,
    unapproved_ai_domains JSONB NOT NULL DEFAULT '["chatgpt.com", "claude.ai", "poe.com", "deepseek.com"]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. People & Organizational Hierarchy
CREATE TABLE IF NOT EXISTS people (
    person_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'employee', -- 'intern', 'employee', 'lead', 'admin'
    department VARCHAR(100) NOT NULL DEFAULT 'Engineering',
    manager_id UUID REFERENCES people(person_id) ON DELETE SET NULL,
    policy_id UUID REFERENCES tracking_policies(policy_id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_people_manager ON people(manager_id);

-- 3. Projects (Classification: Serious vs Research)
CREATE TABLE IF NOT EXISTS projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) NOT NULL UNIQUE,
    classification VARCHAR(32) NOT NULL CHECK (classification IN ('Serious', 'Research')),
    description TEXT,
    monthly_budget_usd NUMERIC(10, 2) NOT NULL DEFAULT 500.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Project Allocations
CREATE TABLE IF NOT EXISTS project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    role_in_project VARCHAR(64) DEFAULT 'Contributor',
    allocation_percentage INT DEFAULT 100,
    UNIQUE(project_id, person_id)
);

-- 5. AI Virtual Keys (Per person & project via LiteLLM)
CREATE TABLE IF NOT EXISTS ai_virtual_keys (
    key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    key_alias VARCHAR(128) NOT NULL,
    litellm_key_hash VARCHAR(255) NOT NULL,
    monthly_budget_usd NUMERIC(10, 2) NOT NULL DEFAULT 100.00,
    current_spend_usd NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    rate_limit_tpm INT NOT NULL DEFAULT 60000,
    rate_limit_rpm INT NOT NULL DEFAULT 60,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(person_id, project_id)
);

-- 6. AI Usage Logs (Captures LiteLLM calls + Langfuse trace pointers)
CREATE TABLE IF NOT EXISTS ai_usage_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(128) NOT NULL,
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_name VARCHAR(128) NOT NULL,
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    is_approved_tool BOOLEAN NOT NULL DEFAULT TRUE,
    langfuse_trace_id VARCHAR(128),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_person_time ON ai_usage_logs(person_id, timestamp DESC);

-- 7. Devices (Laptops)
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(64) PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    device_name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ,
    last_ip VARCHAR(64),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 8. Biometric Attendance Punches (Real turnstile or simulated)
CREATE TABLE IF NOT EXISTS biometric_punches (
    punch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    punch_type VARCHAR(16) NOT NULL CHECK (punch_type IN ('IN', 'OUT')),
    punch_time TIMESTAMPTZ NOT NULL,
    device_identifier VARCHAR(64) NOT NULL DEFAULT 'TURNSTILE-01',
    location VARCHAR(128) NOT NULL DEFAULT 'Main Office HQ',
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_punches_person_time ON biometric_punches(person_id, punch_time DESC);

-- 9. Raw ActivityWatch Telemetry
CREATE TABLE IF NOT EXISTS raw_events (
    id BIGSERIAL,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    bucket_id VARCHAR(128) NOT NULL,
    aw_event_id BIGINT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (device_id, bucket_id, aw_event_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_raw_events_unprocessed ON raw_events(processed) WHERE processed = FALSE;

-- 10. Normalized Activity Spans (Window ∩ not-afk + web URLs)
CREATE TABLE IF NOT EXISTS activity_spans (
    span_id BIGSERIAL PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL,
    app_name VARCHAR(255),
    window_title TEXT,
    url TEXT,
    url_domain VARCHAR(255),
    is_afk BOOLEAN NOT NULL DEFAULT FALSE,
    is_unapproved_ai BOOLEAN NOT NULL DEFAULT FALSE,
    category VARCHAR(64) DEFAULT 'General',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spans_person_time ON activity_spans(person_id, start_time DESC);

-- 11. Shared Canonical Event Schema (Unified Timeline Join)
-- Person + Timestamp + Source + Payload
CREATE TABLE IF NOT EXISTS unified_timeline_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    source VARCHAR(32) NOT NULL CHECK (source IN ('laptop_activity', 'biometric_punch', 'ai_call', 'calendar')),
    category VARCHAR(64) NOT NULL DEFAULT 'Work',
    summary TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_person_time ON unified_timeline_events(person_id, timestamp DESC);

-- 12. Discrepancy Flags & Evidence Store
-- Rules: R01 (Punch-in/No laptop), R02 (Excess idle), R05 (AI while idle), R07 (Unapproved AI tool)
CREATE TABLE IF NOT EXISTS discrepancy_flags (
    flag_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    rule_code VARCHAR(16) NOT NULL CHECK (rule_code IN ('R01', 'R02', 'R05', 'R07')),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACCEPTED', 'REJECTED', 'EXPLAINED')),
    target_date DATE NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolution_notes TEXT,
    resolved_by UUID REFERENCES people(person_id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_flags_person_status ON discrepancy_flags(person_id, status, target_date DESC);
CREATE INDEX IF NOT EXISTS idx_flags_rule ON discrepancy_flags(rule_code);

-- 13. Daily Rollup Day Records (Calculated Metrics)
CREATE TABLE IF NOT EXISTS day_records (
    record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    first_punch_in TIMESTAMPTZ,
    last_punch_out TIMESTAMPTZ,
    office_hours NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    active_hours NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    idle_hours NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    ai_time_minutes NUMERIC(6, 2) NOT NULL DEFAULT 0.0,
    ai_spend_usd NUMERIC(8, 4) NOT NULL DEFAULT 0.0,
    ai_tokens_count INT NOT NULL DEFAULT 0,
    utilization_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    open_flags_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(person_id, work_date)
);

CREATE INDEX IF NOT EXISTS idx_day_records_date ON day_records(work_date DESC, person_id);

-- 14. Day-End Update Form Records
CREATE TABLE IF NOT EXISTS day_end_updates (
    update_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    prefilled_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    accomplishments TEXT NOT NULL,
    blockers TEXT,
    project_allocations JSONB NOT NULL DEFAULT '[]'::jsonb,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(person_id, work_date)
);

-- 15. Consent Logs (First login sign-off)
CREATE TABLE IF NOT EXISTS consent_logs (
    consent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    policy_version VARCHAR(32) NOT NULL DEFAULT 'v1.0-pilot',
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(64),
    user_agent TEXT
);

-- ============================================================================
-- COCKPIT & ANALYTICS VIEWS (Directly queryable by Metabase & Frontend)
-- ============================================================================

-- View: Metabase Cockpit Metrics
CREATE OR REPLACE VIEW v_cockpit_metrics AS
SELECT 
    d.work_date,
    p.full_name,
    p.role,
    p.department,
    d.office_hours,
    d.active_hours,
    d.idle_hours,
    d.utilization_percentage,
    d.ai_spend_usd,
    d.open_flags_count
FROM day_records d
JOIN people p ON p.person_id = d.person_id
ORDER BY d.work_date DESC, d.utilization_percentage ASC;

-- View: Open Discrepancy Flags Summary
CREATE OR REPLACE VIEW v_open_flags_summary AS
SELECT 
    f.flag_id,
    p.full_name,
    p.department,
    f.rule_code,
    f.title,
    f.severity,
    f.status,
    f.target_date,
    f.detected_at AT TIME ZONE 'Asia/Kolkata' AS detected_at_ist
FROM discrepancy_flags f
JOIN people p ON p.person_id = f.person_id
WHERE f.status = 'OPEN'
ORDER BY f.detected_at DESC;

-- View: AI Spending by Project (Serious vs Research)
CREATE OR REPLACE VIEW v_project_ai_spend AS
SELECT 
    prj.name AS project_name,
    prj.classification,
    prj.monthly_budget_usd,
    COALESCE(SUM(l.cost_usd), 0.0) AS current_spend_usd,
    ROUND(COALESCE(SUM(l.cost_usd), 0.0) / NULLIF(prj.monthly_budget_usd, 0) * 100, 1) AS budget_utilized_pct,
    COUNT(l.log_id) AS total_requests
FROM projects prj
LEFT JOIN ai_usage_logs l ON l.project_id = prj.project_id
GROUP BY prj.project_id, prj.name, prj.classification, prj.monthly_budget_usd;
