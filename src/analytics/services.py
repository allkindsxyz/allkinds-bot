from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import List, Optional

from ..models import User, Group, GroupMember, Question, Answer
from .schemas import GroupSummary, GroupStats, GlobalStats


class AnalyticsService:
    """Service for analytics operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_groups_summary(self) -> List[GroupSummary]:
        """Get summary information for all groups"""
        query = (
            select(
                Group.id,
                Group.name,
                Group.description,
                Group.created_at,
                User.name.label('creator_name'),
                func.count(GroupMember.user_id).label('member_count')
            )
            .join(User, Group.creator_id == User.id)
            .outerjoin(GroupMember, Group.id == GroupMember.group_id)
            .group_by(Group.id, Group.name, Group.description, Group.created_at, User.name)
            .order_by(Group.created_at.desc())
        )
        
        result = await self.session.execute(query)
        rows = result.fetchall()
        
        return [
            GroupSummary(
                id=row.id,
                name=row.name,
                description=row.description,
                creator_name=row.creator_name,
                created_at=row.created_at,
                member_count=row.member_count or 0
            )
            for row in rows
        ]
    
    async def get_group_stats(self, group_id: int) -> Optional[GroupStats]:
        """Get detailed statistics for a specific group"""
        # Get basic group info
        group_query = (
            select(
                Group.id,
                Group.name,
                Group.description,
                Group.created_at,
                User.name.label('creator_name'),
                func.count(GroupMember.user_id).label('member_count')
            )
            .join(User, Group.creator_id == User.id)
            .outerjoin(GroupMember, Group.id == GroupMember.group_id)
            .where(Group.id == group_id)
            .group_by(Group.id, Group.name, Group.description, Group.created_at, User.name)
        )
        
        result = await self.session.execute(group_query)
        group_row = result.fetchone()
        
        if not group_row:
            return None
        
        # Get question count
        questions_query = select(func.count(Question.id)).where(Question.group_id == group_id)
        questions_result = await self.session.execute(questions_query)
        total_questions = questions_result.scalar() or 0
        
        # Get answer count
        answers_query = (
            select(func.count(Answer.id))
            .join(Question, Answer.question_id == Question.id)
            .where(Question.group_id == group_id)
        )
        answers_result = await self.session.execute(answers_query)
        total_answers = answers_result.scalar() or 0
        
        # Active users today (simplified - users who answered questions today)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        active_today_query = (
            select(func.count(func.distinct(Answer.user_id)))
            .join(Question, Answer.question_id == Question.id)
            .where(
                and_(
                    Question.group_id == group_id,
                    Answer.created_at >= today_start
                )
            )
        )
        active_today_result = await self.session.execute(active_today_query)
        active_users_today = active_today_result.scalar() or 0
        
        # Active users this week
        week_start = today_start - timedelta(days=7)
        active_week_query = (
            select(func.count(func.distinct(Answer.user_id)))
            .join(Question, Answer.question_id == Question.id)
            .where(
                and_(
                    Question.group_id == group_id,
                    Answer.created_at >= week_start
                )
            )
        )
        active_week_result = await self.session.execute(active_week_query)
        active_users_week = active_week_result.scalar() or 0
        
        return GroupStats(
            id=group_row.id,
            name=group_row.name,
            description=group_row.description,
            creator_name=group_row.creator_name,
            created_at=group_row.created_at,
            member_count=group_row.member_count or 0,
            total_questions=total_questions,
            total_answers=total_answers,
            active_users_today=active_users_today,
            active_users_week=active_users_week
        )
    
    async def get_global_stats(self) -> GlobalStats:
        """Get global platform statistics"""
        # Total users
        users_query = select(func.count(User.id))
        users_result = await self.session.execute(users_query)
        total_users = users_result.scalar() or 0
        
        # Total groups
        groups_query = select(func.count(Group.id))
        groups_result = await self.session.execute(groups_query)
        total_groups = groups_result.scalar() or 0
        
        # Total questions
        questions_query = select(func.count(Question.id))
        questions_result = await self.session.execute(questions_query)
        total_questions = questions_result.scalar() or 0
        
        # Total answers
        answers_query = select(func.count(Answer.id))
        answers_result = await self.session.execute(answers_query)
        total_answers = answers_result.scalar() or 0
        
        # Active users today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        active_today_query = (
            select(func.count(func.distinct(Answer.user_id)))
            .where(Answer.created_at >= today_start)
        )
        active_today_result = await self.session.execute(active_today_query)
        active_users_today = active_today_result.scalar() or 0
        
        # Active users this week
        week_start = today_start - timedelta(days=7)
        active_week_query = (
            select(func.count(func.distinct(Answer.user_id)))
            .where(Answer.created_at >= week_start)
        )
        active_week_result = await self.session.execute(active_week_query)
        active_users_week = active_week_result.scalar() or 0
        
        # Groups created today
        groups_today_query = (
            select(func.count(Group.id))
            .where(Group.created_at >= today_start)
        )
        groups_today_result = await self.session.execute(groups_today_query)
        groups_created_today = groups_today_result.scalar() or 0
        
        # Groups created this week
        groups_week_query = (
            select(func.count(Group.id))
            .where(Group.created_at >= week_start)
        )
        groups_week_result = await self.session.execute(groups_week_query)
        groups_created_week = groups_week_result.scalar() or 0
        
        return GlobalStats(
            total_users=total_users,
            total_groups=total_groups,
            total_questions=total_questions,
            total_answers=total_answers,
            active_users_today=active_users_today,
            active_users_week=active_users_week,
            groups_created_today=groups_created_today,
            groups_created_week=groups_created_week
        ) 