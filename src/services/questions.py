from src.models import Question, Answer, GroupMember, Group, User
from sqlalchemy import select, and_
from src.db import AsyncSessionLocal

async def ensure_user_exists(session, user_id):
    user = await session.execute(select(User).where(User.id == user_id))
    user = user.scalar()
    if not user:
        user = User()
        user.id = user_id
        session.add(user)
        await session.flush()
    return user

async def get_next_unanswered_question(session, group_id, user_id):
    await ensure_user_exists(session, user_id)
    q = await session.execute(
        select(Question).where(
            and_(Question.group_id == group_id, Question.is_deleted == 0)
        ).order_by(Question.created_at)
    )
    questions = q.scalars().all()
    for question in questions:
        ans = await session.execute(select(Answer).where(and_(Answer.question_id == question.id, Answer.user_id == user_id)))
        ans = ans.scalar()
        if not ans:
            return question
    return None

async def is_duplicate_question(session, group_id, text):
    q = await session.execute(
        select(Question).where(
            Question.group_id == group_id,
            Question.is_deleted == 0,
            Question.text == text.strip()
        )
    )
    return q.scalar() is not None

async def moderate_question(text):
    # Basic moderation: reject too short questions and obvious spam
    if len(text.strip()) < 5:
        return False, "Question too short."
    # TODO: add AI/ML filtering
    return True, None

async def get_group_members(session, group_id):
    members = await session.execute(select(GroupMember.user_id).where(GroupMember.group_id == group_id))
    return [row[0] for row in members.all()] 