# Enterprise Workforce & AI Intelligence Platform (Stage A & Stage B)

A unified platform combining client-side **ActivityWatch** telemetry, turnstile biometric attendance, and an enterprise **AI Gateway (LiteLLM + Langfuse)** into an intelligence engine and work experience surface.

---

## 1. Scope & Deliverables

### Stage A: Platform, Capture & Intelligence ("Owns all data in + the brain")
* **Docker Compose Base**: Timescale/pgvector PostgreSQL, LiteLLM AI Proxy, Langfuse, Caddy, and FastAPI backend.
* **Virtual AI Keys**: Budget-capped and rate-limited keys managed per person and project.
* **Edge Telemetry**: Local `aw-shipper` daemon on pilot laptops with SQLite outbox, 10-minute sliding overlap window, and client-side redaction.
* **Biometric Ingest**: Real turnstile webhook or simulated punches feeding canonical daily records.
* **People & Hierarchy**: Organizational tree with default tracking policies.
* **Unified Event Schema**: Canonical `(person_id, timestamp, end_timestamp, duration, source, category, summary, payload)`.
* **Automated Rule Engine**:
  * **R01**: Punch-in / No Laptop Activity (within 45m grace period).
  * **R02**: Excess Workstation Idle (cumulative > 90m or single block > 45m).
  * **R05**: AI Call Executed While User is Idle / AFK (> 15m unmonitored script).
  * **R07**: Unapproved AI Tool or Route Invoked (direct consumer web ChatGPT/Claude).
* **Metrics & Analytics**: Active hours, office badge hours, utilization percentage, AI spend ($), and immutable evidence records.

### Stage B: Experience & Work Surfaces ("Owns everything a human sees")
* **Responsive Web App**:
  * **Consent Notice**: First-login transparency modal with audit logging.
  * **My Day Screen**: Interactive color-coded visual timeline, active vs office hours, AI time & spend, and "What is Captured" transparency drawer.
  * **Discrepancy Centre / Team View**: Rule-filtered flag list with slide-over Evidence Panel and `Accept`, `Reject`, and `Explain` resolution workflows.
  * **Project Management**: `Serious` (core/billable) vs `Research` (experimental) tags, allotted people, and AI spend burn-rate.
  * **Day-End Update Form**: Pre-filled draft accomplishments from ActivityWatch + LiteLLM data.
* **Metabase Cockpit**: Direct connection to PostgreSQL views for real-time utilization, open flags, and AI budget governance.

---

## 2. Directory Structure

```
activitywatch/
├── docker-compose.yml           # Postgres, LiteLLM, Langfuse, Caddy, Backend, Metabase
├── Caddyfile                    # Single HTTPS entrypoint & reverse proxy
├── .env.example                 # Configuration environment template
├── client/
│   ├── config.example.toml      # Laptop shipper settings
│   ├── requirements.txt         # Standard library only
│   └── aw_shipper/
│       ├── config.py            # Device ID, server URL, redaction regexes
│       ├── aw_client.py         # localhost:5600 ActivityWatch REST client
│       ├── outbox.py            # SQLite outbox queue & cursor manager
│       ├── redaction.py         # Client-side sensitive data scrubber
│       ├── shipper.py           # Gzip batch compression & HTTP dispatcher
│       └── main.py              # CLI & daemon sync loop
├── server/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI application & web server
│   ├── db/
│   │   ├── schema.sql           # PostgreSQL DDL, hypertables, views, RBAC
│   │   ├── seed.sql             # Pilot people, projects, policies, devices
│   │   ├── connection.py        # Async connection pool
│   │   └── memory_store.py      # Resilient state store & pilot simulation
│   ├── ingest/
│   │   └── models.py            # Pydantic request/response schemas
│   ├── workers/
│   │   ├── span_builder.py      # Normalizes window focus ∩ AFK + web URLs
│   │   ├── timeline_joiner.py   # Merges activity + punches + AI into one timeline
│   │   ├── rule_engine.py       # Detects R01, R02, R05, R07 + evidence
│   │   └── metrics.py           # Daily rollups & utilization calculator
│   ├── api/
│   │   ├── ingest_api.py        # POST /v1/ingest, POST /v1/heartbeat
│   │   ├── timelines.py         # GET /api/v1/timelines/{person_id}
│   │   ├── flags.py             # GET/POST /api/v1/flags & evidence
│   │   ├── projects.py          # GET /api/v1/projects (Serious vs Research)
│   │   ├── day_end.py           # GET/POST /api/v1/day-end (pre-filled summary)
│   │   ├── punches.py           # POST /api/v1/punches
│   │   └── metrics.py           # GET /api/v1/metrics/cockpit & consent
│   ├── mcp/
│   │   ├── server.py            # FastMCP router over HTTP/SSE
│   │   ├── tools.py             # get_schema, run_sql, semantic_search
│   │   └── time_resolver.py     # IST-calibrated natural language date parser
│   └── static/
│       └── index.html           # Stage B Responsive Web App
└── tests/
    ├── test_redaction.py        # Client scrub tests
    ├── test_rules.py            # R01, R02, R05, R07 rule engine tests
    ├── test_outbox.py           # SQLite outbox queue & overlap tests
    ├── test_timeline_join.py    # Canonical event schema join tests
    └── test_store_and_flow.py   # End-to-end data flow & pilot scenarios
```

---

## 3. Quick Start & Execution

### Running the Platform via Docker Compose
```bash
# 1. Clone or navigate to the directory
cd activitywatch

# 2. Configure environment
cp .env.example .env

# 3. Spin up central stack
docker compose up -d
```
* **Web Application (Stage B)**: Visit `http://localhost:8000` (or `http://localhost`)
* **API Documentation**: Visit `http://localhost:8000/docs`
* **Metabase Cockpit**: Visit `http://localhost:3001`
* **Langfuse Tracing**: Visit `http://localhost:3000`
* **LiteLLM AI Gateway**: `http://localhost:4000`

---

### Running the Edge Laptop Shipper
On each pilot laptop running ActivityWatch:
```bash
# Run one test sync cycle:
python -m client.aw_shipper.main --once --device-id dev-rohan-thinkpad --server-url http://localhost:8000/v1/ingest

# Or run continuously as a background daemon:
python -m client.aw_shipper.main --device-id dev-rohan-thinkpad --server-url http://localhost:8000/v1/ingest
```

---

## 4. Running the Test Suite
All 13 unit and integration tests run with standard library Python:
```bash
python -m unittest discover tests
```
Output:
```
Ran 13 tests in 0.082s
OK
```

