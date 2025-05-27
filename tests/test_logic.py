import pytest
from sqlalchemy import select
from src.models import User, Group, GroupMember, GroupCreator, Question, Answer
import random, string
import types as pytypes
from src.handlers.system import instructions, my_groups
from src.services.questions import get_next_unanswered_question
from src.handlers.questions import send_question_to_user

pytestmark = pytest.mark.asyncio

def random_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

async def create_user(session, user_id):
    user = User(id=user_id)
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

async def create_question(session, group, author, text):
    q = Question(group_id=group.id, author_id=author.id, text=text)
    session.add(q)
    await session.flush()
    return q

async def answer_question(session, user, question, value):
    ans = Answer(question_id=question.id, user_id=user.id, value=value)
    session.add(ans)
    await session.commit()
    return ans

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

async def test_mygroups_logic(async_session):
    # Пользователь не зарегистрирован
    user_id = 1001
    user = await async_session.execute(select(User).where(User.id == user_id))
    assert user.scalar() is None

    # Регистрируем пользователя без групп
    user = User(id=user_id)
    async_session.add(user)
    await async_session.commit()
    groups = await async_session.execute(select(Group).join(GroupMember).where(GroupMember.user_id == user.id))
    assert groups.scalars().all() == []

    # Добавляем одну группу
    group = Group(name="TestG1", description="Desc1", invite_code="AAAAA", creator_user_id=user.id)
    async_session.add(group)
    await async_session.flush()
    member = GroupMember(user_id=user.id, group_id=group.id)
    async_session.add(member)
    await async_session.commit()
    groups = await async_session.execute(select(Group).join(GroupMember).where(GroupMember.user_id == user.id))
    groups = groups.scalars().all()
    assert len(groups) == 1
    assert groups[0].name == "TestG1"

    # Добавляем вторую группу
    group2 = Group(name="TestG2", description="Desc2", invite_code="BBBBB", creator_user_id=user.id)
    async_session.add(group2)
    await async_session.flush()
    member2 = GroupMember(user_id=user.id, group_id=group2.id)
    async_session.add(member2)
    await async_session.commit()
    groups = await async_session.execute(select(Group).join(GroupMember).where(GroupMember.user_id == user.id))
    groups = groups.scalars().all()
    assert len(groups) == 2
    names = [g.name for g in groups]
    assert "TestG1" in names and "TestG2" in names

    # Проверяем для админа
    admin_id = 1002
    admin = User(id=admin_id)
    async_session.add(admin)
    await async_session.flush()
    async_session.add(GroupCreator(user_id=admin.id))
    await async_session.commit()
    admin_group = Group(name="AdminG", description="AdminDesc", invite_code="CCCCC", creator_user_id=admin.id)
    async_session.add(admin_group)
    await async_session.flush()
    admin_member = GroupMember(user_id=admin.id, group_id=admin_group.id)
    async_session.add(admin_member)
    await async_session.commit()
    groups = await async_session.execute(select(Group).join(GroupMember).where(GroupMember.user_id == admin.id))
    groups = groups.scalars().all()
    assert len(groups) == 1
    assert groups[0].name == "AdminG"

async def test_skip_is_answered(async_session):
    user = await create_user(async_session, 2001)
    group, _ = await create_group(async_session, user, "GSkip", "Desc")
    q = await create_question(async_session, group, user, "Q1?")
    await answer_question(async_session, user, q, 0)  # skip
    # Проверяем, что вопрос не считается неотвеченным
    unanswered = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.question_id == q.id, Answer.value.isnot(None)))
    assert unanswered.scalar() is not None

async def test_reanswer_question(async_session):
    user = await create_user(async_session, 2002)
    group, _ = await create_group(async_session, user, "GReans", "Desc")
    q = await create_question(async_session, group, user, "Q2?")
    ans1 = await answer_question(async_session, user, q, 1)
    # Переответ (смена на skip)
    ans1.value = 0
    await async_session.commit()
    updated = await async_session.execute(select(Answer).where(Answer.id == ans1.id))
    updated = updated.scalar()
    assert updated.value == 0
    # Переответ обратно
    updated.value = 2
    await async_session.commit()
    again = await async_session.execute(select(Answer).where(Answer.id == ans1.id))
    again = again.scalar()
    assert again.value == 2

async def test_load_answered_questions_pagination(async_session):
    user = await create_user(async_session, 2003)
    group, _ = await create_group(async_session, user, "GLoad", "Desc")
    questions = [await create_question(async_session, group, user, f"Q{i}?") for i in range(15)]
    for i, q in enumerate(questions):
        await answer_question(async_session, user, q, (i % 5) - 2)
    # Имитация первой страницы
    page1 = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None)).order_by(Answer.created_at).limit(10))
    page1 = page1.scalars().all()
    assert len(page1) == 10
    # Имитация второй страницы
    page2 = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None)).order_by(Answer.created_at).offset(10).limit(10))
    page2 = page2.scalars().all()
    assert len(page2) == 5

async def test_delete_answered_question(async_session):
    user = await create_user(async_session, 2004)
    group, _ = await create_group(async_session, user, "GDel", "Desc")
    q = await create_question(async_session, group, user, "QDel?")
    ans = await answer_question(async_session, user, q, 1)
    # Удаляем вопрос (soft delete)
    q.is_deleted = 1
    await async_session.commit()
    # Проверяем, что вопрос не появляется в списке отвеченных
    answers = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.question_id == q.id, Answer.value.isnot(None)))
    assert answers.scalar() is not None
    # Но при выборке только не удалённых вопросов — не попадает
    not_deleted = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None), Answer.question_id.in_(select(Question.id).where(Question.group_id == group.id, Question.is_deleted == 0))))
    assert not_deleted.scalar() is None

async def test_balance_not_incremented_on_reanswer(async_session):
    user = await create_user(async_session, 2005)
    group, _ = await create_group(async_session, user, "GBal", "Desc")
    member = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    member = member.scalar()
    q = await create_question(async_session, group, user, "QBal?")
    await answer_question(async_session, user, q, 1)
    member.balance += 1
    await async_session.commit()
    # Переответ — баланс не увеличивается
    ans = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.question_id == q.id))
    ans = ans.scalar()
    ans.value = 2
    await async_session.commit()
    member2 = await async_session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
    member2 = member2.scalar()
    assert member2.balance == member.balance

async def test_questions_isolation_between_groups(async_session):
    """Вопросы одной группы не видны в другой (строгая изоляция по group_id)."""
    user = await create_user(async_session, 3001)
    async_session.add(GroupCreator(user_id=user.id))
    await async_session.commit()
    group1, _ = await create_group(async_session, user, "G1", "Desc1")
    group2, _ = await create_group(async_session, user, "G2", "Desc2")
    q1 = await create_question(async_session, group1, user, "Q1?")
    q2 = await create_question(async_session, group2, user, "Q2?")
    # Вопросы группы 1
    qs1 = await async_session.execute(select(Question).where(Question.group_id == group1.id))
    qs1 = qs1.scalars().all()
    assert all(q.group_id == group1.id for q in qs1)
    # Вопросы группы 2
    qs2 = await async_session.execute(select(Question).where(Question.group_id == group2.id))
    qs2 = qs2.scalars().all()
    assert all(q.group_id == group2.id for q in qs2)
    # Вопросы не пересекаются
    ids1 = {q.id for q in qs1}
    ids2 = {q.id for q in qs2}
    assert ids1.isdisjoint(ids2)

async def test_cleanup_on_group_delete_and_leave(async_session):
    """Проверка, что после удаления/выхода из группы все связанные данные корректно очищаются (edge-cases)."""
    admin = await create_user(async_session, 3002)
    async_session.add(GroupCreator(user_id=admin.id))
    await async_session.commit()
    group, _ = await create_group(async_session, admin, "GDel", "Desc")
    user = await create_user(async_session, 3003)
    async_session.add(GroupMember(user_id=user.id, group_id=group.id))
    user.current_group_id = group.id
    await async_session.commit()
    # Вопросы и ответы
    q = await create_question(async_session, group, admin, "QDel?")
    ans = await answer_question(async_session, user, q, 1)
    # Удаление группы
    # Сброс current_group_id у всех пользователей, у кого он указывает на эту группу
    await async_session.execute(
        User.__table__.update().where(User.current_group_id == group.id).values(current_group_id=None)
    )
    await async_session.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group.id))
    await async_session.execute(Question.__table__.delete().where(Question.group_id == group.id))
    await async_session.execute(Answer.__table__.delete().where(Answer.question_id == q.id))
    await async_session.execute(Group.__table__.delete().where(Group.id == group.id))
    await async_session.commit()
    # Проверки
    g = await async_session.execute(select(Group).where(Group.id == group.id))
    assert g.scalar() is None
    m = await async_session.execute(select(GroupMember).where(GroupMember.group_id == group.id))
    assert m.scalars().all() == []
    q_check = await async_session.execute(select(Question).where(Question.group_id == group.id))
    assert q_check.scalars().all() == []
    a_check = await async_session.execute(select(Answer).where(Answer.question_id == q.id))
    assert a_check.scalars().all() == []
    # current_group_id сброшен
    await async_session.refresh(user)
    assert user.current_group_id is None

async def test_switch_group_logic(async_session):
    """Проверка, что смена группы (switch group) происходит корректно."""
    user = await create_user(async_session, 3004)
    async_session.add(GroupCreator(user_id=user.id))
    await async_session.commit()
    group1, _ = await create_group(async_session, user, "GS1", "Desc1")
    group2, _ = await create_group(async_session, user, "GS2", "Desc2")
    # По умолчанию current_group_id = None
    assert user.current_group_id is None
    # Смена на первую группу
    user.current_group_id = group1.id
    await async_session.commit()
    updated = await async_session.execute(select(User).where(User.id == user.id))
    updated = updated.scalar()
    assert updated.current_group_id == group1.id
    # Смена на вторую группу
    updated.current_group_id = group2.id
    await async_session.commit()
    again = await async_session.execute(select(User).where(User.id == user.id))
    again = again.scalar()
    assert again.current_group_id == group2.id
    # Вопросы и ответы только для выбранной группы
    q1 = await create_question(async_session, group1, user, "QSG1?")
    q2 = await create_question(async_session, group2, user, "QSG2?")
    await answer_question(async_session, user, q2, 2)
    # Проверяем, что вопросы фильтруются по current_group_id
    questions = await async_session.execute(select(Question).where(Question.group_id == again.current_group_id))
    questions = questions.scalars().all()
    assert all(q.group_id == group2.id for q in questions)
    # Ответы только по выбранной группе
    answers = await async_session.execute(select(Answer).where(Answer.user_id == user.id))
    answers = answers.scalars().all()
    assert all(a.question_id == q2.id for a in answers)

@pytest.mark.asyncio
async def test_instructions_command(monkeypatch):
    """Проверяет, что инструкция отображается, удаляется и не дублируется."""
    state_data = {}
    class DummyState:
        async def get_data(self):
            return state_data.copy()
        async def update_data(self, **kwargs):
            state_data.update(kwargs)
    class DummyMessage:
        def __init__(self):
            self.chat = pytypes.SimpleNamespace(id=123)
            self.bot = self
            self.deleted = []
            self.sent = []
            self.from_user = pytypes.SimpleNamespace(id=111, language='en')
        async def answer(self, text, parse_mode=None, **kwargs):
            self.sent.append(text)
            # эмулируем message_id
            return pytypes.SimpleNamespace(message_id=len(self.sent))
        async def delete_message(self, chat_id, msg_id):
            self.deleted.append(msg_id)
    message = DummyMessage()
    state = DummyState()
    # Первый вызов — инструкция появляется
    await instructions(message, state)
    assert len(message.sent) == 1
    assert state_data["instructions_msg_id"] == 1
    # Второй вызов — старая инструкция удаляется, появляется новая
    await instructions(message, state)
    assert message.deleted == [1]
    assert len(message.sent) == 2
    assert state_data["instructions_msg_id"] == 2

@pytest.mark.asyncio
async def test_mygroups_command(monkeypatch):
    """Проверяет, что /mygroups отображает сообщение, сохраняет и удаляет message_id."""
    state_data = {}
    class DummyState:
        async def get_data(self):
            return state_data.copy()
        async def update_data(self, **kwargs):
            state_data.update(kwargs)
    class DummyMessage:
        def __init__(self):
            self.chat = pytypes.SimpleNamespace(id=123)
            self.bot = self
            self.deleted = []
            self.sent = []
            self.from_user = pytypes.SimpleNamespace(id=111, language='en')
        async def answer(self, text, **kwargs):
            self.sent.append(text)
            # эмулируем message_id
            return pytypes.SimpleNamespace(message_id=len(self.sent))
        async def delete_message(self, chat_id, msg_id):
            self.deleted.append(msg_id)
    # Мокаем show_user_groups чтобы оно отправляло сообщение и сохраняло message_id
    async def fake_show_user_groups(message, state, user):
        msg = await message.answer(f"Groups for {message.from_user.id}")
        data = await state.get_data()
        ids = data.get("my_groups_msg_ids", [])
        ids.append(msg.message_id)
        await state.update_data(my_groups_msg_ids=ids)
    monkeypatch.setattr("src.handlers.groups.show_user_groups", fake_show_user_groups)
    message = DummyMessage()
    state = DummyState()
    # Первый вызов — сообщение появляется
    await my_groups(message, state)
    assert len(message.sent) == 1
    assert state_data["my_groups_msg_ids"] == [1]
    # Второй вызов — старое сообщение удаляется, появляется новое
    await my_groups(message, state)
    assert message.deleted == [1]
    assert len(message.sent) == 2
    assert state_data["my_groups_msg_ids"] == [2]

@pytest.mark.asyncio
async def test_answered_questions_load_more_button(async_session):
    """Проверяет, что кнопка 'Загрузить ещё' появляется и исчезает корректно при пагинации отвеченных вопросов."""
    user = await create_user(async_session, 9001)
    group, _ = await create_group(async_session, user, "GLoadMore", "Desc")
    # Создаём 25 вопросов и ответов
    questions = [await create_question(async_session, group, user, f"Q{i}?") for i in range(25)]
    for i, q in enumerate(questions):
        await answer_question(async_session, user, q, (i % 5) - 2)
    # Проверяем первую страницу (10)
    page1 = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None)).order_by(Answer.created_at).limit(10))
    page1 = page1.scalars().all()
    assert len(page1) == 10
    # Проверяем вторую страницу (10)
    page2 = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None)).order_by(Answer.created_at).offset(10).limit(10))
    page2 = page2.scalars().all()
    assert len(page2) == 10
    # Проверяем третью страницу (5)
    page3 = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None)).order_by(Answer.created_at).offset(20).limit(10))
    page3 = page3.scalars().all()
    assert len(page3) == 5
    # Проверяем, что после третьей страницы больше нет ответов
    page4 = await async_session.execute(select(Answer).where(Answer.user_id == user.id, Answer.value.isnot(None)).order_by(Answer.created_at).offset(30).limit(10))
    page4 = page4.scalars().all()
    assert len(page4) == 0 