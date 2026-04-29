"""Notion APIを使って記事を保存するツール"""
from datetime import datetime
from notion_client import Client
from config import NOTION_API_KEY, NOTION_DATABASE_ID


def post_to_notion(title: str, content: str, category: str = "マーケット情報") -> dict:
    """Notionデータベースに記事を新規作成"""
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return {"status": "skipped", "message": "Notion APIキーまたはデータベースIDが未設定"}

    try:
        notion = Client(auth=NOTION_API_KEY)

        # ページを作成
        page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "タイトル": {"title": [{"text": {"content": title}}]},
                "カテゴリ": {"select": {"name": category}},
                "公開日": {"date": {"start": datetime.now().isoformat()}},
                "ステータス": {"select": {"name": "公開済み"}},
            },
            children=_markdown_to_notion_blocks(content),
        )

        return {
            "status": "success",
            "page_id": page["id"],
            "url": page.get("url", ""),
            "message": f"Notionに投稿しました: {title}",
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _markdown_to_notion_blocks(content: str) -> list:
    """マークダウンテキストをNotionブロックに変換（簡易版）"""
    blocks = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]},
            })
        elif line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]},
            })
        elif line.startswith("- "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        else:
            # 2000文字制限を考慮して分割
            for chunk in [line[i:i+2000] for i in range(0, len(line), 2000)]:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
                })

    return blocks[:100]  # Notionは1リクエスト100ブロックまで


NOTION_TOOLS = [
    {
        "name": "post_to_notion",
        "description": "Notionデータベースに記事を保存します",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "記事タイトル"},
                "content": {"type": "string", "description": "記事本文（マークダウン形式）"},
                "category": {"type": "string", "description": "カテゴリ名", "default": "マーケット情報"},
            },
            "required": ["title", "content"],
        },
    }
]

NOTION_EXECUTORS = {"post_to_notion": post_to_notion}
