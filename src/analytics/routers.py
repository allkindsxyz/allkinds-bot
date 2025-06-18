from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..db import get_session
from .services import AnalyticsService
from .schemas import GroupSummary, GroupStats, GlobalStats
from .dashboard import DASHBOARD_HTML

# Create FastAPI app
app = FastAPI(
    title="Allkinds Bot Analytics",
    description="Analytics API for Allkinds Bot platform",
    version="1.0.0"
)

router = APIRouter()


@router.get("/", response_model=List[GroupSummary])
async def get_groups_summary(
    session: AsyncSession = Depends(get_session)
) -> List[GroupSummary]:
    """Get summary information for all groups"""
    service = AnalyticsService(session)
    return await service.get_groups_summary()


@router.get("/global", response_model=GlobalStats)
async def get_global_stats(
    session: AsyncSession = Depends(get_session)
) -> GlobalStats:
    """Get global platform statistics"""
    service = AnalyticsService(session)
    return await service.get_global_stats()


@router.get("/{group_id}/stats", response_model=GroupStats)
async def get_group_stats(
    group_id: int,
    session: AsyncSession = Depends(get_session)
) -> GroupStats:
    """Get detailed statistics for a specific group"""
    service = AnalyticsService(session)
    stats = await service.get_group_stats(group_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return stats


@router.get("/{group_id}/users")
async def get_group_user_activities(
    group_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get user activity statistics for a group"""
    service = AnalyticsService(session)
    
    # First check if group exists
    stats = await service.get_group_stats(group_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Return simplified user stats for now
    return {"message": "User activities endpoint - coming soon", "group_id": group_id}


@router.get("/{group_id}/timeline")
async def get_group_timeline(
    group_id: int,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session)
):
    """Get activity timeline for a group"""
    service = AnalyticsService(session)
    
    # First check if group exists
    stats = await service.get_group_stats(group_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Return timeline placeholder for now
    return {"message": "Timeline endpoint - coming soon", "group_id": group_id, "days": days}


# Include router in the app
app.include_router(router, prefix="/analytics", tags=["analytics"])


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Analytics dashboard with charts and tables"""
    return DASHBOARD_HTML


@app.get("/api")
async def api_root():
    """API health check endpoint"""
    return {"message": "Allkinds Bot Analytics API", "status": "running"}


@app.get("/health")
async def health_check():
    """Detailed health check with database connectivity"""
    import os
    from ..db import engine
    
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"
    
    database_url = os.getenv("DATABASE_URL", "not_set")
    
    return {
        "message": "Allkinds Bot Analytics API", 
        "status": "running",
        "database": db_status,
        "database_url_present": bool(database_url != "not_set"),
        "database_url_prefix": database_url[:20] if database_url != "not_set" else "none"
    } 