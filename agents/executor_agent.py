"""
実行エージェント。
フォーマット済みコンテンツをNotion・noteに投稿する。
"""
from agents.base_agent import BaseAgent
from tools.notion_tool import NOTION_TOOLS, NOTION_EXECUTORS
from tools.note_tool import NOTE_TOOLS, NOTE_EXECUTORS
from config import MODEL_LIGHT

SYSTEM_PROMPT = """あなたはコンテンツ配信専門エージェントです。

担当ミッション:
マーケティングエージェントが準備したコンテンツを、NotionとNote.comに投稿してください。

手順:
1. まずNotionに投稿（APIが安定しているため優先）
2. 次にnote.comに投稿
3. 各投稿結果（成功/失敗、URL）を報告する

注意:
- ツールが返すエラーは記録して、成功したものだけ続行する
- 最終的にすべての投稿結果をまとめて日本語で報告する
"""

ALL_TOOLS = NOTION_TOOLS + NOTE_TOOLS
ALL_EXECUTORS = {**NOTION_EXECUTORS, **NOTE_EXECUTORS}


def create_executor_agent() -> BaseAgent:
    return BaseAgent(
        name="実行エージェント",
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
        tool_executors=ALL_EXECUTORS,
        model=MODEL_LIGHT,
    )
