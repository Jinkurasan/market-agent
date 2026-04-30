"""
各情報ソースからデータを収集するスクレイパー群。
各関数はCollectorAgentのツールとして呼び出される。
"""
import json
from pathlib import Path
from datetime import datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config import SESSION_DIR, BLOOMBERG_EMAIL, BLOOMBERG_PASSWORD, WSJ_EMAIL, WSJ_PASSWORD, HITSUJI_FX_URL


def _save_session(context, site_name: str):
    path = SESSION_DIR / f"{site_name}.json"
    context.storage_state(path=str(path))


def _load_context(playwright, site_name: str, headless: bool = True):
    browser = playwright.chromium.launch(headless=headless)
    session_file = SESSION_DIR / f"{site_name}.json"
    if session_file.exists():
        ctx = browser.new_context(storage_state=str(session_file))
    else:
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    return browser, ctx


# ─── Bloomberg ────────────────────────────────────────────────────────────────

def scrape_bloomberg(max_articles: int = 10) -> dict:
    """Bloomberg RSSから最新マーケットニュースを取得"""
    try:
        feed = feedparser.parse("https://feeds.bloomberg.com/markets/news.rss")
        if not feed.entries:
            feed = feedparser.parse("https://feeds.bloomberg.com/technology/news.rss")

        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return {"source": "Bloomberg", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "Bloomberg", "error": str(e), "status": "failed"}


# ─── WSJ ──────────────────────────────────────────────────────────────────────

def scrape_wsj(max_articles: int = 10) -> dict:
    """WSJ RSSから最新マーケットニュースを取得"""
    try:
        feed = feedparser.parse("https://feeds.a.dj.com/rss/RSSMarketsMain.xml")
        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return {"source": "WSJ", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "WSJ", "error": str(e), "status": "failed"}


# ─── investing.com ────────────────────────────────────────────────────────────

def scrape_investing_news(max_articles: int = 10) -> dict:
    """investing.com日本版から最新ニュースを取得"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "investing")
            page = ctx.new_page()
            page.goto("https://jp.investing.com/news/latest-news", timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            soup = BeautifulSoup(page.content(), "lxml")
            articles = []

            for item in soup.select("article.js-article-item, div[data-test='article-item']")[:max_articles]:
                title_el = item.select_one("a.title, h3 a, a[data-id]")
                if title_el:
                    articles.append({
                        "title": title_el.get_text(strip=True),
                        "link": "https://jp.investing.com" + title_el.get("href", ""),
                    })

            browser.close()
            return {"source": "investing.com", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "investing.com", "error": str(e), "status": "failed"}


def scrape_economic_calendar() -> dict:
    """investing.com経済指標カレンダーを取得（今日・明日分）"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "investing_cal")
            page = ctx.new_page()
            page.goto("https://jp.investing.com/economic-calendar/", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            soup = BeautifulSoup(page.content(), "lxml")
            events = []

            for row in soup.select("tr.js-event-item")[:20]:
                time_el = row.select_one("td.first.left.time")
                name_el = row.select_one("td.left.event a")
                impact_el = row.select_one("td.left.textNum.sentiment")
                actual_el = row.select_one("td.act")
                forecast_el = row.select_one("td.fore")
                prev_el = row.select_one("td.prev")

                if name_el:
                    events.append({
                        "time": time_el.get_text(strip=True) if time_el else "",
                        "event": name_el.get_text(strip=True),
                        "actual": actual_el.get_text(strip=True) if actual_el else "",
                        "forecast": forecast_el.get_text(strip=True) if forecast_el else "",
                        "previous": prev_el.get_text(strip=True) if prev_el else "",
                    })

            browser.close()
            return {"source": "Economic Calendar", "events": events, "status": "success"}
    except Exception as e:
        return {"source": "Economic Calendar", "error": str(e), "status": "failed"}


# ─── FedWatch ─────────────────────────────────────────────────────────────────

def scrape_fedwatch() -> dict:
    """CME FedWatchからFF金利の市場予測確率を取得"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "fedwatch")
            page = ctx.new_page()
            page.goto(
                "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
                timeout=30000,
            )
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            soup = BeautifulSoup(page.content(), "lxml")
            probabilities = []

            for row in soup.select("table tbody tr")[:10]:
                cells = row.find_all("td")
                if cells:
                    probabilities.append([c.get_text(strip=True) for c in cells])

            summary_el = soup.select_one("div.probability, div[class*='fedwatch']")
            summary = summary_el.get_text(strip=True)[:500] if summary_el else ""

            browser.close()
            return {
                "source": "FedWatch",
                "probabilities": probabilities,
                "summary": summary,
                "status": "success",
            }
    except Exception as e:
        return {"source": "FedWatch", "error": str(e), "status": "failed"}


# ─── OANDA 通貨強弱 ────────────────────────────────────────────────────────────

def scrape_oanda_currency_strength() -> dict:
    """OANDAの通貨強弱データを取得"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "oanda")
            page = ctx.new_page()
            # OANDA Japanの為替レートページ
            page.goto("https://www.oanda.jp/rate/", timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            soup = BeautifulSoup(page.content(), "lxml")
            rates = []

            for row in soup.select("table tr, div.rate-item")[:20]:
                text = row.get_text(separator=" ", strip=True)
                if text and any(c in text for c in ["USD", "EUR", "JPY", "GBP", "AUD"]):
                    rates.append(text[:100])

            browser.close()
            return {"source": "OANDA", "rates": rates, "status": "success"}
    except Exception as e:
        return {"source": "OANDA", "error": str(e), "status": "failed"}


# ─── 羊飼いFX ──────────────────────────────────────────────────────────────────

def scrape_hitsuji_fx() -> dict:
    """羊飼いFXから最新情報・指標スケジュールを取得"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "hitsuji")
            page = ctx.new_page()
            page.goto(HITSUJI_FX_URL, timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            soup = BeautifulSoup(page.content(), "lxml")
            posts = []

            for item in soup.select("article, .post, .entry")[:5]:
                title_el = item.select_one("h1, h2, h3, .entry-title")
                content_el = item.select_one(".entry-content, .post-content, p")
                if title_el:
                    posts.append({
                        "title": title_el.get_text(strip=True),
                        "content": content_el.get_text(strip=True)[:300] if content_el else "",
                    })

            browser.close()
            return {"source": "羊飼いFX", "posts": posts, "status": "success"}
    except Exception as e:
        return {"source": "羊飼いFX", "error": str(e), "status": "failed"}


# ─── FXi24 ────────────────────────────────────────────────────────────────────

def scrape_fxi24(max_articles: int = 10) -> dict:
    """FXi24から最新FX・マーケットニュースを取得"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "fxi24")
            page = ctx.new_page()
            page.goto("https://fxi24.com/", timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            soup = BeautifulSoup(page.content(), "lxml")
            articles = []

            for item in soup.select("article, .post, .entry, li.news-item")[:max_articles]:
                title_el = item.select_one("h1, h2, h3, a")
                content_el = item.select_one("p, .excerpt, .summary")
                if title_el and title_el.get_text(strip=True):
                    articles.append({
                        "title": title_el.get_text(strip=True),
                        "content": content_el.get_text(strip=True)[:200] if content_el else "",
                    })

            browser.close()
            return {"source": "FXi24", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "FXi24", "error": str(e), "status": "failed"}


# ─── MarketWin24 ───────────────────────────────────────────────────────────────

def scrape_marketwin24(max_articles: int = 10) -> dict:
    """MarketWin24から最新マーケットニュースを取得"""
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "marketwin24")
            page = ctx.new_page()
            page.goto("https://marketwin24.com/", timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            soup = BeautifulSoup(page.content(), "lxml")
            articles = []

            for item in soup.select("article, .post, .entry, li.news-item")[:max_articles]:
                title_el = item.select_one("h1, h2, h3, a")
                content_el = item.select_one("p, .excerpt, .summary")
                if title_el and title_el.get_text(strip=True):
                    articles.append({
                        "title": title_el.get_text(strip=True),
                        "content": content_el.get_text(strip=True)[:200] if content_el else "",
                    })

            browser.close()
            return {"source": "MarketWin24", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "MarketWin24", "error": str(e), "status": "failed"}


# ─── Reuters Japan ────────────────────────────────────────────────────────────

def scrape_reuters_japan(max_articles: int = 10) -> dict:
    """ロイター日本版からマーケット・経済ニュースをRSSで取得"""
    rss_urls = [
        "https://feeds.reuters.com/reuters/JPbusinessNews.xml",
        "https://feeds.reuters.com/reuters/JPTopNews.xml",
        "https://jp.reuters.com/tools/rss",
    ]
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                articles = []
                for entry in feed.entries[:max_articles]:
                    articles.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", "")[:300],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    })
                return {"source": "Reuters Japan", "articles": articles, "status": "success"}
        except Exception:
            continue
    return {"source": "Reuters Japan", "error": "全URLで取得失敗", "status": "failed"}


# ─── NHK 経済ニュース ──────────────────────────────────────────────────────────

def scrape_nhk_economy(max_articles: int = 10) -> dict:
    """NHKニュースの経済カテゴリからRSSで取得"""
    try:
        feed = feedparser.parse("https://www.nhk.or.jp/rss/news/cat6.xml")
        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:300],
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return {"source": "NHK経済ニュース", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "NHK経済ニュース", "error": str(e), "status": "failed"}


# ─── 東洋経済オンライン ────────────────────────────────────────────────────────

def scrape_toyo_keizai(max_articles: int = 10) -> dict:
    """東洋経済オンラインからビジネス・経済ニュースをRSSで取得"""
    try:
        feed = feedparser.parse("https://toyokeizai.net/list/feed/rss")
        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:300],
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return {"source": "東洋経済オンライン", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "東洋経済オンライン", "error": str(e), "status": "failed"}


# ─── Minkabu（株・FX情報）─────────────────────────────────────────────────────

def scrape_minkabu(max_articles: int = 10) -> dict:
    """みんかぶから株式・FX・マーケット情報をRSSで取得"""
    rss_urls = [
        "https://minkabu.jp/news/feed",
        "https://fx.minkabu.jp/news/feed",
    ]
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                articles = []
                for entry in feed.entries[:max_articles]:
                    articles.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", "")[:300],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    })
                return {"source": "みんかぶ", "articles": articles, "status": "success"}
        except Exception:
            continue
    return {"source": "みんかぶ", "error": "取得失敗", "status": "failed"}


# ─── Bloomberg/WSJ フルスクレイピング（ログイン後）────────────────────────────

def login_bloomberg() -> dict:
    """Bloombergにログインしてセッションを保存（初回のみ手動実行）"""
    if not BLOOMBERG_EMAIL or not BLOOMBERG_PASSWORD:
        return {"status": "skipped", "message": "Bloomberg認証情報が未設定"}
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "bloomberg", headless=False)
            page = ctx.new_page()
            page.goto("https://www.bloomberg.com/account/signin")
            page.fill("input[name='email']", BLOOMBERG_EMAIL)
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)
            page.fill("input[name='password']", BLOOMBERG_PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            _save_session(ctx, "bloomberg")
            browser.close()
            return {"status": "success", "message": "Bloombergセッション保存完了"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def login_wsj() -> dict:
    """WSJにログインしてセッションを保存（初回のみ手動実行）"""
    if not WSJ_EMAIL or not WSJ_PASSWORD:
        return {"status": "skipped", "message": "WSJ認証情報が未設定"}
    try:
        with sync_playwright() as p:
            browser, ctx = _load_context(p, "wsj", headless=False)
            page = ctx.new_page()
            page.goto("https://accounts.wsj.com/login")
            page.fill("input[name='username']", WSJ_EMAIL)
            page.fill("input[name='password']", WSJ_PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            _save_session(ctx, "wsj")
            browser.close()
            return {"status": "success", "message": "WSJセッション保存完了"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ツール定義 (CollectorAgentがClaudeに渡すスキーマ)
SCRAPER_TOOLS = [
    {
        "name": "scrape_bloomberg",
        "description": "BloombergのRSSフィードから最新マーケットニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_wsj",
        "description": "WSJ（ウォール・ストリート・ジャーナル）のRSSから最新ニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_investing_news",
        "description": "investing.com日本版から最新金融ニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_economic_calendar",
        "description": "investing.comの経済指標カレンダーから本日・明日の指標スケジュールを取得します",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "scrape_fedwatch",
        "description": "CME FedWatchツールからFRBの利上げ・利下げ確率を取得します",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "scrape_oanda_currency_strength",
        "description": "OANDAから各通貨の強弱・為替レートデータを取得します",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "scrape_hitsuji_fx",
        "description": "羊飼いFXサイトから最新の市場情報・指標スケジュールを取得します",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "scrape_fxi24",
        "description": "FXi24から最新FX・マーケットニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_marketwin24",
        "description": "MarketWin24から最新マーケットニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_reuters_japan",
        "description": "ロイター日本版から最新マーケット・経済ニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_nhk_economy",
        "description": "NHKニュース経済カテゴリから最新情報を取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_toyo_keizai",
        "description": "東洋経済オンラインからビジネス・経済ニュースを取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
    {
        "name": "scrape_minkabu",
        "description": "みんかぶから株式・FX・マーケット情報を取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "description": "取得する最大記事数", "default": 10}
            },
        },
    },
]

SCRAPER_EXECUTORS = {
    "scrape_bloomberg": scrape_bloomberg,
    "scrape_wsj": scrape_wsj,
    "scrape_investing_news": scrape_investing_news,
    "scrape_economic_calendar": scrape_economic_calendar,
    "scrape_fedwatch": scrape_fedwatch,
    "scrape_oanda_currency_strength": scrape_oanda_currency_strength,
    "scrape_hitsuji_fx": scrape_hitsuji_fx,
    "scrape_fxi24": scrape_fxi24,
    "scrape_marketwin24": scrape_marketwin24,
    "scrape_reuters_japan": scrape_reuters_japan,
    "scrape_nhk_economy": scrape_nhk_economy,
    "scrape_toyo_keizai": scrape_toyo_keizai,
    "scrape_minkabu": scrape_minkabu,
}
