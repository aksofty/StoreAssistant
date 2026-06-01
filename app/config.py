import json
import os
from dotenv import load_dotenv

env_file = os.environ.get("DOTENV_PATH", ".env")
load_dotenv(dotenv_path=env_file)

class Config:
    
    CLIENT_ID = os.getenv("CLIENT_ID", "")

    GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
    GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET", "")

    GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")


    FAST_API_SECRET_KEYS = json.loads(os.getenv("FAST_API_SECRET_KEYS", "[]"))
    ALLOWED_ORIGINS = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))
    FAST_API_PORT = int(os.getenv("FAST_API_PORT", "8000"))
    FAST_API_ADDRESS = os.getenv("FAST_API_ADDRESS", "0.0.0.0")

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "very-secret-key")

    @classmethod
    def validate(cls):
        if not cls.GIGACHAT_CLIENT_ID:
            raise ValueError("Missing GIGACHAT_CLIENT_ID in environment variables")
        if not cls.GIGACHAT_CLIENT_SECRET:
            raise ValueError("Missing GIGACHAT_CLIENT_SECRET in environment variables")
        if not cls.FAST_API_SECRET_KEYS:
            raise ValueError("Missing FAST_API_SECRET_KEYS in environment variables")


Config.validate()