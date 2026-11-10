-- ============================================================================
-- Pilot Seed Data: Stage A & Stage B
-- ============================================================================

-- 1. Default Tracking Policy
INSERT INTO tracking_policies (policy_id, policy_name, standard_start_time, standard_end_time, punch_grace_minutes_r01, max_idle_minutes_r02, single_idle_block_limit_r02, ai_idle_token_threshold_r05)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Standard Pilot Engineering Policy',
    '09:30:00',
    '18:30:00',
    45,
    90,
    45,
    500
) ON CONFLICT DO NOTHING;

-- 2. People & Hierarchy (Leader -> Engineers -> Intern)
-- Team Lead: Priya Sharma
INSERT INTO people (person_id, email, full_name, role, department, policy_id)
VALUES (
    '22222222-2222-2222-2222-222222222221',
    'priya.sharma@example.com',
    'Priya Sharma',
    'lead',
    'Engineering',
    '11111111-1111-1111-1111-111111111111'
) ON CONFLICT DO NOTHING;

-- Engineer 1: Rohan Mehta (reports to Priya)
INSERT INTO people (person_id, email, full_name, role, department, manager_id, policy_id)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'rohan.mehta@example.com',
    'Rohan Mehta',
    'employee',
    'Engineering',
    '22222222-2222-2222-2222-222222222221',
    '11111111-1111-1111-1111-111111111111'
) ON CONFLICT DO NOTHING;

-- Engineer 2: Ananya Patel (reports to Priya)
INSERT INTO people (person_id, email, full_name, role, department, manager_id, policy_id)
VALUES (
    '22222222-2222-2222-2222-222222222223',
    'ananya.patel@example.com',
    'Ananya Patel',
    'employee',
    'Engineering',
    '22222222-2222-2222-2222-222222222221',
    '11111111-1111-1111-1111-111111111111'
) ON CONFLICT DO NOTHING;

-- Intern: Vikram Joshi (reports to Rohan)
INSERT INTO people (person_id, email, full_name, role, department, manager_id, policy_id)
VALUES (
    '22222222-2222-2222-2222-222222222224',
    'vikram.joshi@example.com',
    'Vikram Joshi',
    'intern',
    'Engineering',
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111'
) ON CONFLICT DO NOTHING;

-- 3. Projects (Serious vs Research)
INSERT INTO projects (project_id, name, code, classification, description, monthly_budget_usd)
VALUES 
(
    '33333333-3333-3333-3333-333333333331',
    'Apollo Core Engine',
    'PRJ-APOLLO',
    'Serious',
    'High-throughput real-time ingest and distributed streaming platform.',
    1200.00
),
(
    '33333333-3333-3333-3333-333333333332',
    'OmniSearch Agent',
    'PRJ-OMNI',
    'Serious',
    'Enterprise semantic indexing and vector retrieval copilot.',
    800.00
),
(
    '33333333-3333-3333-3333-333333333333',
    'Neural Sandbox Exploration',
    'PRJ-SANDBOX',
    'Research',
    'Experimental local agentic workflows and synthetic data generation.',
    300.00
) ON CONFLICT DO NOTHING;

-- 4. Project Allocations
INSERT INTO project_members (project_id, person_id, role_in_project, allocation_percentage)
VALUES
('33333333-3333-3333-3333-333333333331', '22222222-2222-2222-2222-222222222221', 'Lead Architect', 50),
('33333333-3333-3333-3333-333333333331', '22222222-2222-2222-2222-222222222222', 'Core Developer', 100),
('33333333-3333-3333-3333-333333333332', '22222222-2222-2222-2222-222222222223', 'ML Engineer', 100),
('33333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222224', 'Research Intern', 100)
ON CONFLICT DO NOTHING;

-- 5. AI Virtual Keys (Per person & project)
INSERT INTO ai_virtual_keys (key_id, person_id, project_id, key_alias, litellm_key_hash, monthly_budget_usd, rate_limit_tpm, rate_limit_rpm)
VALUES
('44444444-4444-4444-4444-444444444441', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333331', 'rohan-apollo-key', 'hash_rohan_apollo_123', 300.00, 60000, 60),
('44444444-4444-4444-4444-444444444442', '22222222-2222-2222-2222-222222222223', '33333333-3333-3333-3333-333333333332', 'ananya-omni-key', 'hash_ananya_omni_123', 250.00, 60000, 60),
('44444444-4444-4444-4444-444444444443', '22222222-2222-2222-2222-222222222224', '33333333-3333-3333-3333-333333333333', 'vikram-sandbox-key', 'hash_vikram_sandbox_123', 100.00, 30000, 30)
ON CONFLICT DO NOTHING;

-- 6. Registered Pilot Laptops
INSERT INTO devices (device_id, person_id, device_name, api_key_hash)
VALUES
('dev-priya-macbook', '22222222-2222-2222-2222-222222222221', 'Priya MacBook Pro M3', 'hash_dev_key_priya'),
('dev-rohan-thinkpad', '22222222-2222-2222-2222-222222222222', 'Rohan ThinkPad X1', 'hash_dev_key_rohan'),
('dev-ananya-dell', '22222222-2222-2222-2222-222222222223', 'Ananya Dell XPS 15', 'hash_dev_key_ananya'),
('dev-vikram-asus', '22222222-2222-2222-2222-222222222224', 'Vikram Asus ZenBook', 'hash_dev_key_vikram')
ON CONFLICT DO NOTHING;

