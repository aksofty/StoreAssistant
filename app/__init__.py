import os
from app.config import Config

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

CLIENT_DATA_DIR = os.path.join(BASE_DIR, '_data', f"{Config.CLIENT_ID}")
CLIENT_LOG_DIR = os.path.join(BASE_DIR, '_logs', f"{Config.CLIENT_ID}")

CLIENT_CACHE_DIR = os.path.join(CLIENT_DATA_DIR, 'cache')
CLIENT_FAISS_DIR = os.path.join(CLIENT_DATA_DIR, 'faiss_index')

os.makedirs(CLIENT_CACHE_DIR, exist_ok=True)
os.makedirs(CLIENT_FAISS_DIR, exist_ok=True)

CLIENT_DB_FILE = os.path.join(CLIENT_DATA_DIR, 'db.sqlite3')
CLIENT_LOG_FILE = os.path.join(CLIENT_LOG_DIR, 'main.log')







DB_RAG_DIR = os.path.join(BASE_DIR, '_data', 'RAG')
DB_PATH = os.path.join(BASE_DIR, '_data', 'db.sqlite3')
LOG_PATH = os.path.join(BASE_DIR, '_logs', 'main.log')