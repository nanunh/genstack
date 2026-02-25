from fastapi import APIRouter, HTTPException

from token_usage_manager import global_token_manager

router = APIRouter()


@router.get("/api/projects/{project_id}/token-usage")
async def get_project_token_usage(project_id: str):
    """Get token usage statistics for a specific project"""
    try:
        usage_data = global_token_manager.get_project_usage(project_id)
        return usage_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/token-usage/summary")
async def get_token_usage_summary():
    """Get overall token usage summary"""
    try:
        summary = global_token_manager.get_usage_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/token-usage/daily")
async def get_daily_token_usage(days: int = 7):
    """Get daily token usage for the last N days"""
    try:
        daily_usage = global_token_manager.get_daily_usage(days)
        return {"daily_usage": daily_usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/token-usage/cleanup")
async def cleanup_token_usage(days_to_keep: int = 30):
    """Clean up old token usage data"""
    try:
        global_token_manager.cleanup_old_data(days_to_keep)
        return {"message": f"Cleaned up token usage data older than {days_to_keep} days"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
