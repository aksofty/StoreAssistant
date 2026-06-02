import os
from app.config import Config

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_DEFAULT_DATA_BASE = os.path.join(BASE_DIR, '_data')

CLIENT_DATA_DIR = os.path.join(_DEFAULT_DATA_BASE, Config.CLIENT_ID)


CLIENT_DB_DIR = os.path.join(CLIENT_DATA_DIR, 'db')
CLIENT_CACHE_DIR = os.path.join(CLIENT_DATA_DIR, 'cache')
CLIENT_FAISS_DIR = os.path.join(CLIENT_DATA_DIR, 'faiss_index')
CLIENT_TOOL_DIR = os.path.join(CLIENT_DATA_DIR, 'tools')
CLIENT_LOG_DIR = os.path.join(CLIENT_DATA_DIR, 'logs')

os.makedirs(CLIENT_DB_DIR, exist_ok=True)
os.makedirs(CLIENT_CACHE_DIR, exist_ok=True)
os.makedirs(CLIENT_FAISS_DIR, exist_ok=True)
os.makedirs(CLIENT_TOOL_DIR, exist_ok=True)
os.makedirs(CLIENT_LOG_DIR, exist_ok=True)

CLIENT_DB_FILE = os.path.join(CLIENT_DB_DIR, 'db.sqlite3')
CLIENT_LOG_FILE = os.path.join(CLIENT_LOG_DIR, 'main.log')