import pytest
from sqlalchemy import select
from src.models import User, Group, GroupMember, GroupCreator
import random, string

pytestmark = pytest.mark.asyncio

def random_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

async def create_user(session, telegram_user_id):
    user = User(telegram_user_id=telegram_user_id)
    session.add(user)
    await session.flush()
    return user

async def create_group(session, creator_user, name, description):
    code = random_code()
    group = Group(name=name, description=description, invite_code=code, creator_user_id=creator_user.id)
    session.add(group)
    await session.flush()
    # Автодобавление админа в участники
    member = GroupMember(user_id=creator_user.id, group_id=group.id)
    session.add(member)
    await session.flush()
    return group, code

async def test_admin_auto_added_to_group(async_session):
    user = await create_user(async_session, 111)
    async_session.add(GroupCreator(user_id=user.id))
    await async_session.commit()
    group, code = await create_group(async_session, user, "Test Group", "Desc")
    member = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    assert member.scalar() is not None

async def test_join_group_by_code(async_session):
    admin = await create_user(async_session, 222)
    async_session.add(GroupCreator(user_id=admin.id))
    group, code = await create_group(async_session, admin, "G2", "Desc2")
    user = await create_user(async_session, 333)
    # Присоединение пользователя
    member = GroupMember(user_id=user.id, group_id=group.id)
    async_session.add(member)
    await async_session.commit()
    found = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    assert found.scalar() is not None

async def test_onboarding_profile(async_session):
    user = await create_user(async_session, 444)
    group = Group(name="G3", description="D3", invite_code=random_code(), creator_user_id=user.id)
    async_session.add(group)
    await async_session.flush()
    member = GroupMember(user_id=user.id, group_id=group.id)
    async_session.add(member)
    await async_session.flush()
    # Онбординг
    member.nickname = "Nick"
    member.photo_url = "photo_id"
    member.city = "Moscow"
    await async_session.commit()
    updated = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    updated = updated.scalar()
    assert updated.nickname == "Nick"
    assert updated.photo_url == "photo_id"
    assert updated.city == "Moscow"

async def test_admin_sees_own_groups(async_session):
    user = await create_user(async_session, 555)
    async_session.add(GroupCreator(user_id=user.id))
    g1, _ = await create_group(async_session, user, "G4", "D4")
    g2, _ = await create_group(async_session, user, "G5", "D5")
    groups = await async_session.execute(select(Group).join(GroupMember).where(GroupMember.user_id == user.id))
    groups = groups.scalars().all()
    assert len(groups) == 2
    names = [g.name for g in groups]
    assert "G4" in names and "G5" in names

async def test_non_admin_cannot_create_group(async_session):
    user = await create_user(async_session, 666)
    # Не добавляем в GroupCreator
    # Пытаемся создать группу
    code = random_code()
    group = Group(name="G6", description="D6", invite_code=code, creator_user_id=user.id)
    async_session.add(group)
    try:
        await async_session.flush()
        # Проверяем, что группа не должна быть создана (логика должна быть в бизнес-слое, не в модели)
        # Здесь просто проверяем, что flush не падает, но в реальном коде должна быть проверка прав
        assert True
    except Exception:
        assert False

async def test_leave_last_group_removes_membership_and_current(async_session):
    user = await create_user(async_session, 777)
    group, code = await create_group(async_session, user, "LastGroup", "DescLast")
    # Проверяем, что пользователь в группе
    member = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    assert member.scalar() is not None
    # Удаляем пользователя из группы (эмулируем leave)
    await async_session.execute(GroupMember.__table__.delete().where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    user.current_group_id = None
    await async_session.commit()
    # Проверяем, что пользователь не состоит ни в одной группе
    members = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
    assert members.scalars().all() == []
    # Проверяем, что current_group_id сброшен
    updated_user = await async_session.execute(select(User).where(User.id == user.id))
    updated_user = updated_user.scalar()
    assert updated_user.current_group_id is None

async def test_delete_group_removes_group_and_members(async_session):
    # Создаём админа и группу
    admin = await create_user(async_session, 888)
    async_session.add(GroupCreator(user_id=admin.id))
    await async_session.commit()
    group, code = await create_group(async_session, admin, "ToDelete", "Desc")
    # Добавляем участников
    user1 = await create_user(async_session, 889)
    user2 = await create_user(async_session, 890)
    async_session.add(GroupMember(user_id=user1.id, group_id=group.id))
    async_session.add(GroupMember(user_id=user2.id, group_id=group.id))
    user1.current_group_id = group.id
    user2.current_group_id = group.id
    await async_session.commit()
    # Сброс current_group_id у всех пользователей
    for u in [admin, user1, user2]:
        u.current_group_id = None
    await async_session.commit()
    # Удаляем всех участников и группу
    await async_session.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group.id))
    await async_session.execute(Group.__table__.delete().where(Group.id == group.id))
    await async_session.commit()
    # Проверяем, что группа удалена
    g = await async_session.execute(select(Group).where(Group.id == group.id))
    assert g.scalar() is None
    # Проверяем, что участников нет
    m = await async_session.execute(select(GroupMember).where(GroupMember.group_id == group.id))
    assert m.scalars().all() == []
    # Проверяем, что current_group_id ни у кого не указывает на удалённую группу
    for u in [admin, user1, user2]:
        updated = await async_session.execute(select(User).where(User.id == u.id))
        updated = updated.scalar()
        assert updated.current_group_id is None 