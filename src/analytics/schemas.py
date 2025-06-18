from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GroupSummary(BaseModel):
    """Summary information for a group"""
    id: int
    name: str
    description: Optional[str] = None
    member_count: int
    creator_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class GroupStats(BaseModel):
    """Detailed statistics for a group"""
    id: int
    name: str
    description: Optional[str] = None
    member_count: int
    creator_name: str
    created_at: datetime
    total_questions: int
    total_answers: int
    active_users_today: int
    active_users_week: int
    
    class Config:
        from_attributes = True


class GlobalStats(BaseModel):
    """Global platform statistics"""
    total_users: int
    total_groups: int
    total_questions: int
    total_answers: int
    active_users_today: int
    active_users_week: int
    groups_created_today: int
    groups_created_week: int 