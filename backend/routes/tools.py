"""
SatQuery AI — Tools Route

GET /api/tools — Lists the current model/tool registry.
"""

from fastapi import APIRouter
from backend.models.tool_registry import get_tool_summary, get_registry

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/tools")
async def list_tools():
    """Return the current tool registry (compact summary)."""
    return {
        "tools": get_tool_summary(),
        "total": len(get_registry()),
    }


@router.get("/tools/{tool_id}")
async def get_tool_detail(tool_id: str):
    """Return full detail for a specific tool."""
    from backend.models.tool_registry import get_tool
    tool = get_tool(tool_id)
    if not tool:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    return tool
