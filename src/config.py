import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.getenv('POSTGRES_USER', 'allkinds')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'allkinds')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'allkinds')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
ALLKINDS_CHAT_BOT_USERNAME = os.getenv("ALLKINDS_CHAT_BOT_USERNAME", "AllkindsChatBot") 