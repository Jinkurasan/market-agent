import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _get(key: str, default: str = "") -> str:
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
NOTION_API_KEY = _get("NOTION_API_KEY")
NOTION_DATABASE_ID = _get("NOTION_DATABASE_ID")
NOTE_EMAIL = _get("NOTE_EMAIL")
NOTE_PASSWORD = _get("NOTE_PASSWORD")
BLOOMBERG_EMAIL = _get("BLOOMBERG_EMAIL")
BLOOMBERG_PASSWORD = _get("BLOOMBERG_PASSWORD")
WSJ_EMAIL = _get("WSJ_EMAIL")
WSJ_PASSWORD = _get("WSJ_PASSWORD")
HITSUJI_FX_URL = _get("HITSUJI_FX_URL", "https://hitsujinofx.com/")
LINE_CHANNEL_ACCESS_TOKEN = _get("LINE_CHANNEL_ACCESS_TOKEN")

BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

MODEL_HEAVY = "claude-opus-4-7"
MODEL_LIGHT = "claude-sonnet-4-6"
