"""
Notionのデータベースを自動作成するセットアップスクリプト。
初回のみ実行する。
"""
from notion_client import Client

key = input("Notionシークレットキー(secret_xxx...)を貼り付けてEnter: ").strip()

PAGE_ID = "34805645340480529859fe3999f35570"

print("\nデータベース作成中...")

try:
    notion = Client(auth=key)

    db = notion.databases.create(
        parent={"type": "page_id", "page_id": PAGE_ID},
        title=[{"text": {"content": "マーケットレポート"}}],
        properties={
            "タイトル": {"title": {}},
            "カテゴリ": {"select": {}},
            "公開日": {"date": {}},
            "ステータス": {"select": {}},
        },
    )

    db_id = db["id"]
    print(f"\n✅ 作成完了！")
    print(f"\nDatabase ID: {db_id}")
    print(f"\n以下を .env ファイルに追記してください：")
    print(f"NOTION_API_KEY={key}")
    print(f"NOTION_DATABASE_ID={db_id}")

except Exception as e:
    print(f"\n❌ エラー: {e}")
    print("シークレットキーが正しいか確認してください。")
