"""Server-only configuration and lazy Firebase initialization."""

import json
import os
from functools import lru_cache

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()


@lru_cache
def settings():
    key = os.getenv("OPENAI_API_KEY", "")
    provider = os.getenv("AI_PROVIDER", "codyssey" if key.startswith("sk-cody-") else "openai").strip().lower()
    return {
        "origins": [v.strip() for v in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",") if v.strip()],
        "ai_provider": provider,
        "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://copa.codyssey.kr/v1" if provider == "codyssey" else "").strip(),
        "model": os.getenv("OPENAI_MODEL", "gpt-5.4-mini" if provider == "codyssey" else "gpt-4.1-mini"),
        "max_output_tokens": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "300")),
        "chat_daily_limit": int(os.getenv("CHAT_DAILY_LIMIT", "30")),
        "action_api_key": os.getenv("ACTION_API_KEY", ""),
    }


@lru_cache
def db():
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is required")
    certificate = json.loads(raw) if raw.startswith("{") else raw
    try:
        app = firebase_admin.get_app()
    except ValueError:
        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        options = {"projectId": project_id} if project_id else None
        app = firebase_admin.initialize_app(credentials.Certificate(certificate), options)
    return firestore.client(app)
