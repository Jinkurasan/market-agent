"""note.comへPlaywrightで自動投稿するツール"""
from playwright.sync_api import sync_playwright
from config import NOTE_EMAIL, NOTE_PASSWORD, SESSION_DIR


def post_to_note(title: str, content: str) -> dict:
    """note.comに記事を投稿・公開"""
    if not NOTE_EMAIL or not NOTE_PASSWORD:
        return {"status": "skipped", "message": "note.comの認証情報が未設定"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # note.comはheadlessだと弾かれる場合あり
            session_file = SESSION_DIR / "note.json"

            if session_file.exists():
                ctx = browser.new_context(storage_state=str(session_file))
            else:
                ctx = browser.new_context()

            page = ctx.new_page()

            # ログインチェック
            page.goto("https://note.com/", timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            if "login" in page.url or not _is_logged_in(page):
                _login_note(page, ctx)

            # 新規記事作成
            page.goto("https://note.com/notes/new", timeout=30000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # タイトル入力
            title_input = page.locator("textarea[placeholder*='タイトル'], input[placeholder*='タイトル']").first
            title_input.click()
            title_input.fill(title)

            # 本文入力
            body_input = page.locator("div[contenteditable='true'], textarea.o-noteEditable__textarea").first
            body_input.click()
            body_input.fill(content)
            page.wait_for_timeout(1000)

            # 公開ボタンをクリック
            publish_btn = page.locator("button:has-text('公開'), button:has-text('投稿')").first
            publish_btn.click()
            page.wait_for_timeout(2000)

            # 公開確認ダイアログ
            confirm_btn = page.locator("button:has-text('公開する'), button:has-text('投稿する')").first
            if confirm_btn.is_visible():
                confirm_btn.click()
                page.wait_for_load_state("networkidle")

            url = page.url
            ctx.storage_state(path=str(session_file))
            browser.close()

            return {"status": "success", "url": url, "message": f"note.comに投稿しました: {title}"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _is_logged_in(page) -> bool:
    return page.locator("a[href*='/notes/new'], button:has-text('投稿する')").is_visible()


def _login_note(page, ctx):
    page.goto("https://note.com/login", timeout=30000)
    page.wait_for_load_state("domcontentloaded")
    page.fill("input[name='email'], input[type='email']", NOTE_EMAIL)
    page.fill("input[name='password'], input[type='password']", NOTE_PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    ctx.storage_state(path=str(SESSION_DIR / "note.json"))


NOTE_TOOLS = [
    {
        "name": "post_to_note",
        "description": "note.comに記事を投稿・公開します",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "記事タイトル"},
                "content": {"type": "string", "description": "記事本文"},
            },
            "required": ["title", "content"],
        },
    }
]

NOTE_EXECUTORS = {"post_to_note": post_to_note}
