"""
Badge management utilities for push notifications
Handles badge counting for unanswered questions and match requests
"""
import logging
from typing import Optional
from sqlalchemy import select, and_, func
from src.db import AsyncSessionLocal
from src.models import Question, Answer, MatchStatus, GroupMember
from src.utils.redis import get_telegram_user_id


async def get_unanswered_questions_count(user_id: int, group_id: int) -> int:
    """Get count of unanswered questions for user in group"""
    async with AsyncSessionLocal() as session:
        # Count questions where user has no answer
        subquery = select(Answer.question_id).where(Answer.user_id == user_id)
        
        result = await session.execute(
            select(func.count(Question.id)).where(
                and_(
                    Question.group_id == group_id,
                    Question.is_deleted == 0,
                    Question.status == "approved",
                    ~Question.id.in_(subquery)
                )
            )
        )
        return result.scalar() or 0


async def get_pending_match_requests_count(user_id: int) -> int:
    """Get count of pending incoming match requests for user"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(MatchStatus.id)).where(
                and_(
                    MatchStatus.match_user_id == user_id,
                    MatchStatus.status == "pending"
                )
            )
        )
        return result.scalar() or 0


async def get_total_badge_count(user_id: int, group_id: Optional[int] = None) -> int:
    """Get total badge count (unanswered questions + pending matches)"""
    unanswered_count = 0
    if group_id:
        unanswered_count = await get_unanswered_questions_count(user_id, group_id)
    
    pending_matches = await get_pending_match_requests_count(user_id)
    
    total = unanswered_count + pending_matches
    logging.info(f"[badge_count] user_id={user_id}, group_id={group_id}, "
                f"unanswered={unanswered_count}, matches={pending_matches}, total={total}")
    return total


async def send_badge_notification(bot, user_id: int, message: str, increment_only: bool = True) -> bool:
    """
    Send push notification to increment badge
    
    Args:
        bot: Telegram bot instance
        user_id: Internal user ID
        message: Push notification text
        increment_only: If True, only send if this increments badge (default)
    
    Returns:
        True if notification was sent, False otherwise
    """
    try:
        telegram_id = await get_telegram_user_id(user_id)
        if not telegram_id:
            logging.warning(f"[send_badge_notification] No telegram_id for user_id={user_id}")
            return False
        
        # Send push notification to increment badge
        await bot.send_message(
            telegram_id,
            message,
            disable_notification=False  # This creates a badge increment
        )
        
        logging.info(f"[send_badge_notification] Sent to user_id={user_id}, telegram_id={telegram_id}: {message}")
        return True
        
    except Exception as e:
        logging.exception(f"[send_badge_notification] Error for user_id={user_id}: {e}")
        return False


async def send_initial_badge_if_needed(bot, user_id: int, group_id: Optional[int] = None) -> bool:
    """
    Send specific pending items instead of generic badge notification
    Called on /start to show current pending questions and match requests
    
    Returns:
        True if any pending items were sent, False if no items to show
    """
    from src.services.questions import get_next_unanswered_question
    from src.handlers.system import send_pending_connection_requests
    
    items_sent = False
    
    # Send specific pending questions if any
    if group_id:
        try:
            question = await get_next_unanswered_question(user_id, group_id)
            if question:
                from src.handlers.questions import send_question_to_user
                from src.db import AsyncSessionLocal
                from src.models import User
                from sqlalchemy import select
                
                async with AsyncSessionLocal() as session:
                    user = await session.execute(select(User).where(User.id == user_id))
                    user = user.scalar()
                    if user:
                        await send_question_to_user(bot, user, question)
                        items_sent = True
        except Exception as e:
            logging.exception(f"[send_initial_badge] Error sending pending question: {e}")
    
    # Send specific pending match requests if any
    try:
        match_requests_sent = await send_pending_connection_requests(bot, user_id)
        if match_requests_sent:
            items_sent = True
    except Exception as e:
        logging.exception(f"[send_initial_badge] Error sending pending matches: {e}")
    
    logging.info(f"[send_initial_badge] user_id={user_id}, items_sent={items_sent}")
    return items_sent


async def log_badge_decrement(user_id: int, reason: str) -> None:
    """
    Log badge decrement event. 
    Note: Telegram doesn't support direct badge decrement, 
    but we log this for analytics and potential future features.
    """
    logging.info(f"[badge_decrement] user_id={user_id}, reason={reason}")
    # Badge will be cleared when user opens the bot chat


async def send_silent_notification_if_needed(bot, user_id: int, message: str) -> bool:
    """
    Send silent notification only if user needs to be aware of remaining items
    Used as a fallback when we can't decrement badge directly
    """
    try:
        telegram_id = await get_telegram_user_id(user_id)
        if not telegram_id:
            return False
        
        # Send silent notification (won't increment badge but shows in notifications)
        await bot.send_message(
            telegram_id,
            message,
            disable_notification=True  # Silent notification
        )
        
        logging.info(f"[silent_notification] Sent to user_id={user_id}: {message}")
        return True
        
    except Exception as e:
        logging.exception(f"[silent_notification] Error for user_id={user_id}: {e}")
        return False 