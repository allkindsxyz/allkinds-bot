import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.environ["USER_ID_SECRET_KEY"]
fernet = Fernet(FERNET_KEY)

def encrypt_user_id(user_id: str) -> str:
    return fernet.encrypt(user_id.encode()).decode()

def decrypt_user_id(encrypted_id: str) -> str:
    return fernet.decrypt(encrypted_id.encode()).decode()

def generate_user_id(telegram_id: int) -> str:
    """
    Генерирует шифрованный user_id на основе telegram_id (или любого уникального значения).
    Возвращает строку.
    """
    return fernet.encrypt(str(telegram_id).encode()).decode()

def decrypt_user_id(user_id: str) -> str:
    """
    Дешифрует user_id обратно в исходный telegram_id (строка).
    """
    return fernet.decrypt(user_id.encode()).decode() 