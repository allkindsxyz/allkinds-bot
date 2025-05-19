from typing import List, Dict, Optional, Any
from src.db import AsyncSessionLocal
from src.models import User, Group, GroupMember, GroupCreator, Answer, Question, MatchStatus
from src.keyboards.groups import get_admin_keyboard, get_user_keyboard, get_group_main_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os, logging
from sqlalchemy import select, func
from src.utils import generate_unique_invite_code
from src.constants import WELCOME_BONUS

ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

async def ensure_admin_in_db() -> None:
    """Ensure the admin user and creator record exist in the DB."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == ADMIN_USER_ID))
        user = user.scalar()
        if not user:
            user = User(telegram_user_id=ADMIN_USER_ID)
            session.add(user)
            await session.flush()
        creator = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
        creator = creator.scalar()
        if not creator:
            session.add(GroupCreator(user_id=user.id))
            await session.commit()

async def is_group_creator(user_id: int) -> bool:
    """Check if user is a group creator."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            return False
        creator = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
        return creator.scalar() is not None

async def get_user_groups(user_id: int) -> List[Dict[str, Any]]:
    """Get all groups for a user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).join(GroupMember).join(User).where(User.telegram_user_id == user_id)
        )
        groups = result.scalars().all()
        logging.info(f"[get_user_groups] user_id={user_id}, groups={[g.name for g in groups]}")
        return [{"id": g.id, "name": g.name} for g in groups]

async def is_onboarded(user_id: int, group_id: int) -> bool:
    """Check if user is onboarded in a group."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GroupMember).join(User).where(
                User.telegram_user_id == user_id,
                GroupMember.group_id == group_id,
                GroupMember.nickname.isnot(None),
                GroupMember.photo_url.isnot(None),
                (GroupMember.geolocation_lat.isnot(None) | GroupMember.city.isnot(None))
            )
        )
        return result.scalar() is not None

async def get_group_balance(user_id: int, group_id: int) -> int:
    """Get user's balance in a group."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GroupMember.balance).join(User).where(
                User.telegram_user_id == user_id,
                GroupMember.group_id == group_id
            )
        )
        balance = result.scalar()
        return balance if balance is not None else 0

async def get_group_members(group_id: int) -> List[Dict[str, Any]]:
    """Return all members of a group with onboarding status."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GroupMember, User).join(User).where(GroupMember.group_id == group_id)
        )
        members = []
        for gm, user in result.all():
            onboarded = bool(gm.nickname and gm.photo_url and (gm.geolocation_lat is not None or gm.city))
            members.append({
                "user_id": user.id,
                "telegram_user_id": user.telegram_user_id,
                "nickname": gm.nickname,
                "role": gm.role,
                "onboarded": onboarded,
                "balance": gm.balance
            })
        return members

async def get_group_stats(group_id: int) -> Dict[str, Any]:
    """Return group statistics: total members, onboarded, average balance."""
    async with AsyncSessionLocal() as session:
        total = await session.execute(
            select(func.count(GroupMember.id)).where(GroupMember.group_id == group_id)
        )
        total_members = total.scalar() or 0
        onboarded = await session.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id,
                GroupMember.nickname.isnot(None),
                GroupMember.photo_url.isnot(None),
                (GroupMember.geolocation_lat.isnot(None) | GroupMember.city.isnot(None))
            )
        )
        onboarded_members = onboarded.scalar() or 0
        avg_balance = await session.execute(
            select(func.avg(GroupMember.balance)).where(GroupMember.group_id == group_id)
        )
        avg_balance_val = avg_balance.scalar() or 0
        return {
            "total_members": total_members,
            "onboarded_members": onboarded_members,
            "avg_balance": avg_balance_val
        }

async def get_group_onboarding_status(group_id: int) -> List[Dict[str, Any]]:
    """Return onboarding status for all group members."""
    members = await get_group_members(group_id)
    return [{"telegram_user_id": m["telegram_user_id"], "onboarded": m["onboarded"]} for m in members]

async def show_user_groups(message, user_id, state):
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            await message.answer("You are not registered. Use /start.")
            return
        groups = await session.execute(
            select(Group).join(GroupMember).where(GroupMember.user_id == user.id)
        )
        groups = groups.scalars().all()
        if not groups:
            is_creator = await is_group_creator(user_id)
            if is_creator:
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Create a new group", callback_data="create_new_group")], [InlineKeyboardButton(text="Join another group with code", callback_data="join_another_group_with_code")]])
            else:
                kb = get_user_keyboard()
            await message.answer("You are not in any groups.", reply_markup=kb)
            return
        current_group = None
        if user.current_group_id:
            current_group = next((g for g in groups if g.id == user.current_group_id), None)
        if not current_group:
            current_group = groups[0]
            user.current_group_id = current_group.id
            await session.commit()
        bot_info = await message.bot.get_me()
        deeplink = f"https://t.me/{bot_info.username}?start={current_group.invite_code}"
        text = f"You are in <b>{current_group.name}</b>\n{current_group.description}\n\nInvite link: {deeplink}\nInvite code: <code>{current_group.invite_code}</code>"
        is_creator = (current_group.creator_user_id == user.id)
        kb = get_group_main_keyboard(user.id, current_group.id, current_group.name, is_creator)
        kb.inline_keyboard.append([])
        other_groups = [g for g in groups if g.id != current_group.id]
        for g in other_groups:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"Switch to {g.name}", callback_data=f"switch_to_group_{g.id}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="Create a new group", callback_data="create_new_group")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="Join another group with code", callback_data="join_another_group_with_code")])
        sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        data = await state.get_data()
        ids = data.get("my_groups_msg_ids", [])
        ids.append(sent.message_id)
        await state.update_data(my_groups_msg_ids=ids)

async def create_group_service(user_id: int, name: str, description: str) -> dict:
    """Создать группу и вернуть её данные."""
    invite_code = await generate_unique_invite_code()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            user = User(telegram_user_id=user_id)
            session.add(user)
            await session.flush()
        group = Group(name=name, description=description, invite_code=invite_code, creator_user_id=user.id)
        session.add(group)
        member = GroupMember(user_id=user.id, group_id=group.id)
        session.add(member)
        user.current_group_id = group.id
        await session.commit()
        return {"id": group.id, "name": group.name, "invite_code": group.invite_code}

async def join_group_by_code_service(user_id: int, code: str) -> dict | None:
    """Вступить в группу по коду. Вернуть данные группы или None."""
    async with AsyncSessionLocal() as session:
        group = await session.execute(select(Group).where(Group.invite_code == code))
        group = group.scalar()
        if not group:
            return None
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            user = User(telegram_user_id=user_id)
            session.add(user)
            await session.flush()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
        member = member.scalar()
        if not member:
            member = GroupMember(user_id=user.id, group_id=group.id, balance=WELCOME_BONUS)
            session.add(member)
            user.current_group_id = group.id
            await session.commit()
            # Проверяем статус онбординга
            onboarded = await is_onboarded(user_id, group.id)
            if not onboarded:
                return {"id": group.id, "name": group.name, "needs_onboarding": True}
        return {"id": group.id, "name": group.name, "needs_onboarding": False}

async def switch_group_service(user_id: int, group_id: int) -> dict:
    """Сменить текущую группу пользователя. Вернуть статус и данные группы."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        onboarded = member and member.nickname and (member.geolocation_lat or member.city) and member.photo_url
        if onboarded:
            user.current_group_id = group_id
            await session.commit()
            group = await session.execute(select(Group).where(Group.id == group_id))
            group = group.scalar()
            return {"ok": True, "group": {"id": group.id, "name": group.name}}
        return {"ok": False, "reason": "not_onboarded"}

async def delete_group_service(group_id: int) -> dict:
    """Удалить группу и вернуть результат (список пользователей для уведомления)."""
    async with AsyncSessionLocal() as session:
        group = await session.execute(select(Group).where(Group.id == group_id))
        group = group.scalar()
        if not group:
            return {"ok": False, "reason": "not_found"}
        members = await session.execute(select(GroupMember).where(GroupMember.group_id == group_id))
        members = members.scalars().all()
        users_to_update = await session.execute(select(User).where(User.current_group_id == group_id))
        users_to_update = users_to_update.scalars().all()
        for user in users_to_update:
            user.current_group_id = None
        await session.commit()
        notify_users = []
        for member in members:
            user = await session.execute(select(User).where(User.id == member.user_id))
            user = user.scalar()
            if user and user.id != group.creator_user_id:
                notify_users.append({"telegram_user_id": user.telegram_user_id, "group_name": group.name})
        await session.commit()
        await session.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group_id))
        await session.execute(Group.__table__.delete().where(Group.id == group_id))
        await session.commit()
        return {"ok": True, "notify_users": notify_users}

async def leave_group_service(user_id: int, group_id: int) -> dict:
    """Покинуть группу. Вернуть статус и список оставшихся групп."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        await session.execute(
            GroupMember.__table__.delete().where(GroupMember.user_id == user.id, GroupMember.group_id == group_id)
        )
        await session.commit()
        if user.current_group_id == group_id:
            user.current_group_id = None
            await session.commit()
        groups = await session.execute(
            select(Group).join(GroupMember).where(GroupMember.user_id == user.id)
        )
        groups = groups.scalars().all()
        if not groups:
            user.current_group_id = None
            await session.commit()
        return {"ok": True, "groups": [{"id": g.id, "name": g.name} for g in groups]}

async def find_best_match(user_id: int, group_id: int, exclude_user_ids: list[int] = None) -> dict | None:
    """Найти лучшего мэтча для пользователя в группе по максимальному совпадению ответов, исключая hidden/postponed. Similarity: 1 - (Σ|A_i-B_i|)/(4*N)."""
    exclude_user_ids = exclude_user_ids or []
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            return None
        # Исключаем пользователей с match_status
        statuses = await session.execute(select(MatchStatus.match_user_id, MatchStatus.status).where(
            MatchStatus.user_id == user.id, MatchStatus.group_id == group_id))
        for match_user_id, status in statuses.all():
            if status in ("hidden", "postponed"):
                exclude_user_ids.append(match_user_id)
        # Получаем все ответы пользователя по вопросам группы
        user_answers = await session.execute(
            select(Answer.question_id, Answer.value).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        user_answers = {row[0]: row[1] for row in user_answers.all()}
        if not user_answers:
            return None
        # Получаем всех других участников группы
        members = await session.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id != user.id))
        members = members.scalars().all()
        # Считаем количество валидных пользователей для мэтча
        valid_users_count = 0
        best_match = None
        best_score = -1
        max_distance = 4
        best_common_questions = 0
        for member in members:
            if member.user_id in exclude_user_ids:
                continue
            # Ответы мэтча
            match_answers = await session.execute(
                select(Answer.question_id, Answer.value).where(
                    Answer.user_id == member.user_id,
                    Answer.value.isnot(None),
                    Answer.question_id.in_(user_answers.keys())
                )
            )
            match_answers = {row[0]: row[1] for row in match_answers.all()}
            if not match_answers:
                continue
            # Считаем similarity по формуле
            total = 0
            dist_sum = 0
            for qid, uval in user_answers.items():
                if qid in match_answers:
                    mval = match_answers[qid]
                    total += 1
                    dist_sum += abs(uval - mval)
            if total < 3:
                continue  # слишком мало общих вопросов
            valid_users_count += 1
            similarity = 1 - (dist_sum / (max_distance * total))
            percent = int(similarity * 100)
            if percent > best_score:
                best_score = percent
                best_match = member
                best_common_questions = total
        if best_match:
            # Получаем ник и фото мэтча
            match_user = await session.execute(select(User).where(User.id == best_match.user_id))
            match_user = match_user.scalar()
            return {
                "user_id": best_match.user_id,
                "nickname": best_match.nickname,
                "photo_url": best_match.photo_url,
                "similarity": best_score,
                "common_questions": best_common_questions,
                "valid_users_count": valid_users_count,
                "telegram_user_id": match_user.telegram_user_id if match_user else None
            }
        return None

async def set_match_status(user_id: int, group_id: int, match_user_id: int, status: str):
    """Установить статус мэтча ('hidden' или 'postponed')."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            return
        obj = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == match_user_id
        ))
        obj = obj.scalar()
        if obj:
            obj.status = status
        else:
            obj = MatchStatus(user_id=user.id, group_id=group_id, match_user_id=match_user_id, status=status)
            session.add(obj)
        await session.commit() 