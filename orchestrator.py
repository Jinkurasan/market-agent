"""
オーケストレーター。
4つのエージェントを順番に呼び出して情報収集〜配信を完結させる。
"""
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.collector_agent import create_collector_agent
from agents.summarizer_agent import create_summarizer_agent
from agents.marketer_agent import create_marketer_agent
from agents.executor_agent import create_executor_agent
from agents.coo_agent import create_coo_agent
from agents.sns_strategy_agent import create_sns_strategy_agent
from agents.content_planning_agent import create_content_planning_agent

console = Console()
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_pipeline(dry_run: bool = False) -> dict:
    """
    メインパイプラインを実行する。
    dry_run=True の場合は実際の投稿をスキップする。
    """
    started_at = datetime.now()
    console.print(Panel.fit(
        f"[bold]マーケット情報収集パイプライン[/bold]\n{started_at.strftime('%Y-%m-%d %H:%M:%S')} 開始",
        border_style="blue",
    ))

    results = {}

    # ── Step 1: 情報収集 ────────────────────────────────────────────────────
    collector = create_collector_agent()
    collected_data = collector.run(
        f"現在時刻: {started_at.strftime('%Y年%m月%d日 %H:%M')}\n"
        "すべての情報ソースから最新マーケット情報を収集してください。"
    )
    results["collected"] = collected_data
    _save_output("1_collected", collected_data)

    # ── Step 2: 要約・分析 ──────────────────────────────────────────────────
    summarizer = create_summarizer_agent()
    summary = summarizer.run(
        f"以下の収集データを分析して、マーケットレポートを作成してください。\n\n{collected_data}"
    )
    results["summary"] = summary
    _save_output("2_summary", summary)

    # ── Step 3: マーケティング最適化 ────────────────────────────────────────
    marketer = create_marketer_agent()
    formatted_raw = marketer.run(
        f"以下のマーケットレポートを各プラットフォーム向けに最適化してください。\n\n{summary}"
    )
    results["formatted_raw"] = formatted_raw
    _save_output("3_formatted", formatted_raw)

    # JSONパース
    formatted = _parse_formatted(formatted_raw)
    results["formatted"] = formatted

    # ── Step 4: 配信 ────────────────────────────────────────────────────────
    if dry_run:
        console.print("\n[yellow]⚠ ドライランモード: 実際の投稿はスキップします[/yellow]")
        results["publish"] = {"status": "dry_run"}
    else:
        executor = create_executor_agent()
        publish_result = executor.run(
            f"以下のコンテンツをNotionとnote.comに投稿してください。\n\n"
            f"Notionタイトル: {formatted.get('notion', {}).get('title', 'マーケットレポート')}\n"
            f"Notion本文:\n{formatted.get('notion', {}).get('content', summary)}\n\n"
            f"noteタイトル: {formatted.get('note', {}).get('title', 'マーケットレポート')}\n"
            f"note本文:\n{formatted.get('note', {}).get('content', summary)}"
        )
        results["publish"] = publish_result
        _save_output("4_publish", publish_result)

    # ── 完了レポート ─────────────────────────────────────────────────────────
    elapsed = (datetime.now() - started_at).seconds
    console.print(Panel.fit(
        f"[bold green]✅ パイプライン完了[/bold green] ({elapsed}秒)\n"
        + _build_summary(results, formatted),
        border_style="green",
    ))

    return results


def run_strategy(context: str = "") -> str:
    """
    COO主導の戦略立案パイプライン。
    SNS戦略部・コンテンツ企画部に指示を出し、戦略レポートを生成する。
    """
    started_at = datetime.now()
    console.print(Panel.fit(
        f"[bold]COO戦略パイプライン[/bold]\n{started_at.strftime('%Y-%m-%d %H:%M:%S')} 開始",
        border_style="red",
    ))

    # 最新の市場レポートを参考情報として読み込む
    recent_summary = _load_latest_output("2_summary")

    # ── SNS戦略部 ────────────────────────────────────────────────────────────
    sns = create_sns_strategy_agent()
    sns_strategy = sns.run(
        f"現在の市場環境と情報:\n{recent_summary}\n\n"
        f"追加指示: {context}\n\n"
        "X（Twitter）・noteでの情報発信戦略を立案してください。"
    )
    _save_output("strategy_sns", sns_strategy)

    # ── コンテンツ企画部 ─────────────────────────────────────────────────────
    planner = create_content_planning_agent()
    content_plan = planner.run(
        f"現在の市場環境:\n{recent_summary}\n\n"
        f"SNS戦略部の方針:\n{sns_strategy}\n\n"
        "直近1週間のコンテンツカレンダーと企画案を作成してください。"
    )
    _save_output("strategy_content", content_plan)

    # ── COO統合レポート ──────────────────────────────────────────────────────
    coo = create_coo_agent()
    coo_report = coo.run(
        f"社長への報告を作成してください。\n\n"
        f"【SNS戦略部レポート】\n{sns_strategy}\n\n"
        f"【コンテンツ企画部レポート】\n{content_plan}\n\n"
        f"【社長からの追加指示】\n{context if context else 'なし'}"
    )
    _save_output("strategy_coo", coo_report)

    elapsed = (datetime.now() - started_at).seconds
    console.print(Panel.fit(
        f"[bold red]✅ COO戦略レポート完了[/bold red] ({elapsed}秒)",
        border_style="red",
    ))

    return coo_report


def _load_latest_output(step_suffix: str) -> str:
    """最新のステップ出力ファイルを読み込む"""
    files = sorted(OUTPUT_DIR.glob(f"*_{step_suffix}.txt"), reverse=True)
    if files:
        return files[0].read_text(encoding="utf-8")
    return "（まだ情報収集が実行されていません）"


def _parse_formatted(raw: str) -> dict:
    """マーケティングエージェントの出力からJSONを抽出"""
    import re
    text = raw.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            if "line" not in result:
                result["line"] = ""
            return result
    except json.JSONDecodeError:
        pass
    return {
        "note": {"title": "マーケットレポート", "content": raw},
        "notion": {"title": "マーケットレポート", "content": raw},
        "line": "",
        "tweets": [],
    }


def _save_output(step: str, content: str):
    """各ステップの出力をファイルに保存"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{ts}_{step}.txt"
    path.write_text(content, encoding="utf-8")


def _build_summary(results: dict, formatted: dict) -> str:
    lines = []
    note_title = formatted.get("note", {}).get("title", "")
    if note_title:
        lines.append(f"note: 「{note_title}」")
    tweets = formatted.get("tweets", [])
    if tweets:
        lines.append(f"ツイート候補: {len(tweets)}件")
    pub = results.get("publish", {})
    if isinstance(pub, str) and "成功" in pub:
        lines.append("投稿: 成功")
    return "\n".join(lines) if lines else "完了"
