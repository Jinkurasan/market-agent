"""
各情報ソースからデータを収集するスクレイパー群。
各関数はCollectorAgentのツールとして呼び出される。
"""
import feedparser
import httpx
from bs4 import BeautifulSoup

from config import HITSUJI_FX_URL

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _fetch_html(url: str) -> str:
    resp = httpx.get(url, headers=_HEADERS, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _fetch_rss(url: str):
    resp = httpx.get(url, headers=_HEADERS, timeout=15.0, follow_redirects=True)
    return feedparser.parse(resp.content)


# ─── Bloomberg ────────────────────────────────────────────────────────────────

def scrape_bloomberg(max_articles: int = 10) -> dict:
    """Bloomberg RSSから最新マーケットニュースを取得"""
    try:
        feed = _fetch_rss("https://feeds.bloomberg.com/markets/news.rss")
        if not feed.entries:
            feed = _fetch_rss("https://feeds.bloomberg.com/technology/news.rss")

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
        feed = _fetch_rss("https://feeds.a.dj.com/rss/RSSMarketsMain.xml")
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
        html = _fetch_html("https://jp.investing.com/news/latest-news")
        soup = BeautifulSoup(html, "lxml")
        articles = []
        for item in soup.select("article.js-article-item, div[data-test='article-item']")[:max_articles]:
            title_el = item.select_one("a.title, h3 a, a[data-id]")
            if title_el:
                href = title_el.get("href", "")
                link = href if href.startswith("http") else "https://jp.investing.com" + href
                articles.append({"title": title_el.get_text(strip=True), "link": link})
        return {"source": "investing.com", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "investing.com", "error": str(e), "status": "failed"}


def scrape_economic_calendar() -> dict:
    """investing.com経済指標カレンダーを取得"""
    try:
        html = _fetch_html("https://jp.investing.com/economic-calendar/")
        soup = BeautifulSoup(html, "lxml")
        events = []
        for row in soup.select("tr.js-event-item")[:20]:
            time_el = row.select_one("td.first.left.time")
            name_el = row.select_one("td.left.event a")
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
        return {"source": "Economic Calendar", "events": events, "status": "success"}
    except Exception as e:
        return {"source": "Economic Calendar", "error": str(e), "status": "failed"}


# ─── FedWatch ─────────────────────────────────────────────────────────────────

def scrape_fedwatch() -> dict:
    """CME FedWatchからFF金利の市場予測確率を取得"""
    try:
        html = _fetch_html("https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html")
        soup = BeautifulSoup(html, "lxml")
        probabilities = []
        for row in soup.select("table tbody tr")[:10]:
            cells = row.find_all("td")
            if cells:
                probabilities.append([c.get_text(strip=True) for c in cells])
        summary_el = soup.select_one("div.probability, div[class*='fedwatch']")
        summary = summary_el.get_text(strip=True)[:500] if summary_el else ""
        return {"source": "FedWatch", "probabilities": probabilities, "summary": summary, "status": "success"}
    except Exception as e:
        return {"source": "FedWatch", "error": str(e), "status": "failed"}


# ─── OANDA 通貨強弱 ────────────────────────────────────────────────────────────

def scrape_oanda_currency_strength() -> dict:
    """OANDAの通貨強弱データを取得"""
    try:
        html = _fetch_html("https://www.oanda.jp/rate/")
        soup = BeautifulSoup(html, "lxml")
        rates = []
        for row in soup.select("table tr, div.rate-item")[:20]:
            text = row.get_text(separator=" ", strip=True)
            if text and any(c in text for c in ["USD", "EUR", "JPY", "GBP", "AUD"]):
                rates.append(text[:100])
        return {"source": "OANDA", "rates": rates, "status": "success"}
    except Exception as e:
        return {"source": "OANDA", "error": str(e), "status": "failed"}


# ─── 羊飼いFX ──────────────────────────────────────────────────────────────────

def scrape_hitsuji_fx() -> dict:
    """羊飼いFXから最新情報・指標スケジュールを取得"""
    try:
        html = _fetch_html(HITSUJI_FX_URL)
        soup = BeautifulSoup(html, "lxml")
        posts = []
        for item in soup.select("article, .post, .entry")[:5]:
            title_el = item.select_one("h1, h2, h3, .entry-title")
            content_el = item.select_one(".entry-content, .post-content, p")
            if title_el:
                posts.append({
                    "title": title_el.get_text(strip=True),
                    "content": content_el.get_text(strip=True)[:300] if content_el else "",
                })
        return {"source": "羊飼いFX", "posts": posts, "status": "success"}
    except Exception as e:
        return {"source": "羊飼いFX", "error": str(e), "status": "failed"}


# ─── FXi24 ────────────────────────────────────────────────────────────────────

def scrape_fxi24(max_articles: int = 10) -> dict:
    """FXi24から最新FX・マーケットニュースを取得"""
    try:
        html = _fetch_html("https://fxi24.com/")
        soup = BeautifulSoup(html, "lxml")
        articles = []
        for item in soup.select("article, .post, .entry, li.news-item")[:max_articles]:
            title_el = item.select_one("h1, h2, h3, a")
            content_el = item.select_one("p, .excerpt, .summary")
            if title_el and title_el.get_text(strip=True):
                articles.append({
                    "title": title_el.get_text(strip=True),
                    "content": content_el.get_text(strip=True)[:200] if content_el else "",
                })
        return {"source": "FXi24", "articles": articles, "status": "success"}
    except Exception as e:
        return {"source": "FXi24", "error": str(e), "status": "failed"}


# ─── MarketWin24 ───────────────────────────────────────────────────────────────

def scrape_marketwin24(max_articles: int = 10) -> dict:
    """MarketWin24から最新マーケットニュースを取得"""
    try:
        html = _fetch_html("https://marketwin24.com/")
        soup = BeautifulSoup(html, "lxml")
        articles = []
        for item in soup.select("article, .post, .entry, li.news-item")[:max_articles]:
            title_el = item.select_one("h1, h2, h3, a")
            content_el = item.select_one("p, .excerpt, .summary")
            if title_el and title_el.get_text(strip=True):
                articles.append({
                    "title": title_el.get_text(strip=True),
                    "content": content_el.get_text(strip=True)[:200] if content_el else "",
                })
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
            feed = _fetch_rss(url)
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
        feed = _fetch_rss("https://www.nhk.or.jp/rss/news/cat6.xml")
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
        feed = _fetch_rss("https://toyokeizai.net/list/feed/rss")
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
            feed = _fetch_rss(url)
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
