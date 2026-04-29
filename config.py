import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTE_EMAIL = os.getenv("NOTE_EMAIL")
NOTE_PASSWORD = os.getenv("NOTE_PASSWORD")
BLOOMBERG_EMAIL = os.getenv("BLOOMBERG_EMAIL")
BLOOMBERG_PASSWORD = os.getenv("BLOOMBERG_PASSWORD")
WSJ_EMAIL = os.getenv("WSJ_EMAIL")
WSJ_PASSWORD = os.getenv("WSJ_PASSWORD")
HITSUJI_FX_URL = os.getenv("HITSUJI_FX_URL", "https://hitsujinofx.com/")

BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

# エージェントに使うモデル
MODEL_HEAVY = "claude-opus-4-7"    # 収集・要約など複雑なタスク
MODEL_LIGHT = "claude-sonnet-4-6"  # フォーマット・実行など軽量タスク
