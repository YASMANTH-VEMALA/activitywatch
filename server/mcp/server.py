from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from mcp.tools import tool_get_schema, tool_run_sql, tool_semantic_search, tool_time_resolver

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (FastMCP)"])

class RunSQLRequest(BaseModel):
    query: str

class SemanticSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class TimeResolverRequest(BaseModel):
    expression: str

@router.get("/tools")
async def list_mcp_tools():
    return {
        "tools": [
            {"name": "get_schema", "description": "Returns the read-only curated views schema."},
            {"name": "run_sql", "description": "Executes sandboxed SQL queries under agent_readonly role (5s timeout, LIMIT 500)."},
            {"name": "semantic_search", "description": "Semantic search over window contexts and user activity."},
            {"name": "time_resolver", "description": "Resolves natural language dates to IST range."}
        ]
    }

@router.get("/tools/get_schema")
async def mcp_get_schema():
    return await tool_get_schema()

@router.post("/tools/run_sql")
async def mcp_run_sql(req: RunSQLRequest):
    return await tool_run_sql(req.query)

@router.post("/tools/semantic_search")
async def mcp_semantic_search(req: SemanticSearchRequest):
    return await tool_semantic_search(req.query, req.top_k or 5)

@router.post("/tools/time_resolver")
async def mcp_time_resolver(req: TimeResolverRequest):
    return await tool_time_resolver(req.expression)

