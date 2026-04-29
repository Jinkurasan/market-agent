"""
エントリーポイント。手動トリガーでパイプラインを実行する。

使い方:
  python main.py              # 通常実行（Notion/noteに投稿）
  python main.py --dry-run    # ドライラン（投稿なし、内容確認のみ）
  python main.py --strategy   # COO戦略レポートを生成
  python main.py --login      # Bloomberg/WSJのセッション保存（初回のみ）
  python main.py --show       # 最後に生成した記事を表示
"""
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown

console = Console()


def main():
    parser = argparse.ArgumentParser(description="マーケット情報収集・配信パイプライン")
    parser.add_argument("--dry-run", action="store_true", help="投稿せず内容確認のみ")
    parser.add_argument("--strategy", action="store_true", help="COO戦略レポートを生成")
    parser.add_argument("--strategy-context", type=str, default="", help="COOへの追加指示")
    parser.add_argument("--login", choices=["bloomberg", "wsj", "all"], help="有料サイトのセッション保存")
    parser.add_argument("--show", action="store_true", help="最後に生成した要約を表示")
    args = parser.parse_args()

    if args.strategy:
        from orchestrator import run_strategy
        from rich.console import Console
        from rich.markdown import Markdown
        report = run_strategy(context=args.strategy_context)
        Console().print(Markdown(report))
        return

    if args.login:
        _run_login(args.login)
        return

    if args.show:
        _show_latest_output()
        return

    # メインパイプライン実行
    from orchestrator import run_pipeline
    run_pipeline(dry_run=args.dry_run)


def _run_login(target: str):
    from tools.scrapers import login_bloomberg, login_wsj
    if target in ("bloomberg", "all"):
        console.print("[cyan]Bloombergにログイン中...[/cyan]")
        result = login_bloomberg()
        console.print(result)
    if target in ("wsj", "all"):
        console.print("[cyan]WSJにログイン中...[/cyan]")
        result = login_wsj()
        console.print(result)


def _show_latest_output():
    output_dir = Path(__file__).parent / "output"
    summaries = sorted(output_dir.glob("*_2_summary.txt"), reverse=True)
    if not summaries:
        console.print("[yellow]まだ生成済みの要約がありません[/yellow]")
        return
    content = summaries[0].read_text(encoding="utf-8")
    console.print(Markdown(content))


if __name__ == "__main__":
    main()
