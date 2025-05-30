import random
import string
from src.db import AsyncSessionLocal
from src.models import Group
from sqlalchemy import select

CODE_LENGTH = 5
CODE_CHARS = string.ascii_uppercase + string.digits

async def generate_unique_invite_code():
    while True:
        code = ''.join(random.choices(CODE_CHARS, k=CODE_LENGTH))
        async with AsyncSessionLocal() as session:
            exists = await session.execute(select(Group).where(Group.invite_code == code))
            if not exists.scalar():
                return code 