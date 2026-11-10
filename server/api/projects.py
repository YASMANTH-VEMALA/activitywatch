from fastapi import APIRouter
from db.memory_store import store

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])

@router.get("")
async def list_projects():
    project_list = []
    for prj in store.projects.values():
        p_id = prj["project_id"]
        # Sum AI spend for this project
        project_spend = sum(
            a.get("cost_usd", 0.0) 
            for a in store.ai_usage_logs 
            if a.get("project_id") == p_id
        )
        total_tokens = sum(
            a.get("total_tokens", 0) 
            for a in store.ai_usage_logs 
            if a.get("project_id") == p_id
        )

        item = dict(prj)
        item["current_spend_usd"] = round(project_spend, 4)
        item["total_tokens"] = total_tokens
        item["budget_utilization_pct"] = round(
            (project_spend / max(1.0, prj["monthly_budget_usd"])) * 100.0, 2
        )
        project_list.append(item)

    return {
        "count": len(project_list),
        "projects": project_list
    }
