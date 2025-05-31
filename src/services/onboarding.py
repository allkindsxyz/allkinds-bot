from src.db import AsyncSessionLocal
from src.models import User, GroupMember
from sqlalchemy import select
from typing import Optional

async def save_nickname_service(user_id: int, group_id: int, nickname: str) -> None:
    async with AsyncSessionLocal() as session:
        # Гарантируем, что пользователь существует
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not user:
            user = User()
            user.id = user_id
            session.add(user)
            await session.flush()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user_id, GroupMember.group_id == group_id))
        member = member.scalar()
        if not member:
            print(f"[save_nickname_service] member not found, creating new GroupMember for user_id={user_id}, group_id={group_id}, nickname={nickname}")
            exists = await session.execute(select(GroupMember).where(GroupMember.user_id == user_id, GroupMember.group_id == group_id))
            exists = exists.scalar()
            if not exists:
                member = GroupMember(user_id=user_id, group_id=group_id, nickname=nickname)
                session.add(member)
                await session.flush()
        else:
            member.nickname = nickname
        await session.commit()

async def save_photo_service(user_id: int, group_id: int, photo_url: str) -> None:
    async with AsyncSessionLocal() as session:
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user_id, GroupMember.group_id == group_id))
        member = member.scalar()
        if not member:
            print(f"[save_photo_service] ERROR: member not found for user_id={user_id}, group_id={group_id}")
            return
        member.photo_url = photo_url
        await session.commit()

async def save_location_service(user_id: int, group_id: int, lat: float = None, lon: float = None, city: str = None, country: str = None) -> None:
    async with AsyncSessionLocal() as session:
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user_id, GroupMember.group_id == group_id))
        member = member.scalar()
        print(f"[save_location_service] user_id={user_id}, group_id={group_id}, lat={lat}, lon={lon}, city={city}, country={country}")
        print(f"[save_location_service] member before: {member}")
        if member:
            if lat is not None and lon is not None:
                member.geolocation_lat = lat
                member.geolocation_lon = lon
            if city is not None:
                member.city = city
            if country is not None:
                member.country = country
            await session.commit()
            print(f"[save_location_service] member after: {member}")

async def is_onboarding_complete_service(user_id: int, group_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user_id, GroupMember.group_id == group_id))
        member = member.scalar()
        print(f"[is_onboarding_complete_service] member: {member}")
        if member:
            print(f"[is_onboarding_complete_service] nickname: {member.nickname}, photo_url: {member.photo_url}, lat: {member.geolocation_lat}, city: {member.city}")
        result = bool(member and member.nickname and member.photo_url and (member.geolocation_lat is not None or member.city))
        print(f"[is_onboarding_complete_service] result: {result}")
        if result:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
            if user and user.current_group_id != group_id:
                user.current_group_id = group_id
                await session.commit()
        return result 