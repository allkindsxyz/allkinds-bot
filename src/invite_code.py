import random
import string
from src.db import AsyncSessionLocal
from src.models import Group
from sqlalchemy import select

async def generate_unique_invite_code():
    chars = string.ascii_uppercase + string.digits
    async with AsyncSessionLocal() as session:
        while True:
            code = ''.join(random.choices(chars, k=5))
            result = await session.execute(select(Group).where(Group.invite_code == code))
            if not result.scalar():
                return code 