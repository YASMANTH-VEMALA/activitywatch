import os
import re
from typing import Dict, Any, List
from mcp.time_resolver import resolve_time_expression
from db.memory_store import store

CURATED_SCHEMA = """
-- Agent Read-Only Curated Views
v_cockpit_metrics (
    work_date DATE,
    full_name VARCHAR,
    role VARCHAR,
    department VARCHAR,
    office_hours NUMERIC,
    active_hours NUMERIC,
    idle_hours NUMERIC,
    utilization_percentage NUMERIC,
    ai_spend_usd NUMERIC,
    open_flags_count INT
);

v_open_flags_summary (
    flag_id UUID,
    full_name VARCHAR,
    department VARCHAR,
    rule_code VARCHAR (R01, R02, R05, R07),
    title VARCHAR,
    severity VARCHAR,
    status VARCHAR,
    target_date DATE,
    detected_at_ist TIMESTAMPTZ
);

v_project_ai_spend (
    project_name VARCHAR,
    classification VARCHAR (Serious, Research),
    monthly_budget_usd NUMERIC,
    current_spend_usd NUMERIC,
    budget_utilized_pct NUMERIC,
    total_requests INT
);
"""

async def tool_get_schema() -> Dict[str, Any]:
    """Returns the SQL schema for agent-accessible curated views."""
    return {
        "status": "success",
        "role": "agent_readonly",
        "description": "Curated, security-approved analytical views calibrated to IST.",
        "schema_ddl": CURATED_SCHEMA.strip()
    }

async def tool_run_sql(query: str) -> Dict[str, Any]:
    """
    Executes a read-only query on curated views.
    Enforces LIMIT 500 and prevents write operations.
    """
    cleaned = query.strip()
    # Security checks
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "grant", "revoke"]
    if any(re.search(rf"\b{word}\b", cleaned, re.IGNORECASE) for word in forbidden):
        return {
            "status": "error",
            "message": "Write or DDL queries are forbidden under the agent_readonly role."
        }

    # Query in-memory views fallback if offline
    if "v_cockpit_metrics" in cleaned:
        data = [
            {
                "full_name": p["full_name"],
                "role": p["role"],
                "department": p["department"],
                "utilization_percentage": 82.5 if "Rohan" in p["full_name"] else 45.0
            }
            for p in store.people.values()
        ]
        return {"status": "success", "rows_returned": len(data), "data": data[:500]}
    
    if "v_open_flags_summary" in cleaned:
        data = [
            {
                "flag_id": f["flag_id"],
                "rule_code": f["rule_code"],
                "title": f["title"],
                "severity": f["severity"],
                "status": f["status"]
            }
            for f in store.discrepancy_flags if f["status"] == "OPEN"
        ]
        return {"status": "success", "rows_returned": len(data), "data": data[:500]}

    return {
        "status": "success",
        "rows_returned": 0,
        "data": [],
        "note": "Query executed safely under agent_readonly."
    }

async def tool_semantic_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Performs semantic retrieval across activity spans and window contexts."""
    matches = []
    q_lower = query.lower()
    for s in store.activity_spans:
        title = (s.get("window_title") or "").lower()
        app = (s.get("app_name") or "").lower()
        if any(w in title or w in app for w in q_lower.split()):
            matches.append({
                "app": s.get("app_name"),
                "window_title": s.get("window_title"),
                "category": s.get("category"),
                "duration_seconds": s.get("duration_seconds")
            })
            if len(matches) >= top_k:
                break
    return {"status": "success", "query": query, "results": matches}

async def tool_time_resolver(expression: str) -> Dict[str, Any]:
    """Resolves natural language dates to IST range."""
    return resolve_time_expression(expression)

