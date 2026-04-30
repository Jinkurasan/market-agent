"""
情報収集エージェント。
各情報ソースからツールを使って最新データを収集する。
"""
from agents.base_agent import BaseAgent
from tools.scrapers import SCRAPER_TOOLS, SCRAPER_EXECUTORS
from config import MODEL_HEAVY

SYSTEM_PROMPT = """あなたは金融マーケットの情報収集専門エージェントです。

担当ミッション:
Bloomberg、WSJ、Reuters Japan、NHK経済、東洋経済、みんかぶ、
investing.com、CME FedWatch、OANDA、羊飼いFX、経済指標カレンダーから
最新情報を収集し、構造化されたデータとして返してください。

手順:
1. 利用可能なすべてのスクレイピングツールを呼び出してください（全ツール必須）
2. 各ソースから得たデータを整理してください
3. エラーになったソースも記録してください（後工程に渡す）
4. 最終的に収集した全データをまとめて日本語で報告してください

注意:
- ツールは並行して呼び出してください（順番にこだわらず全部呼ぶ）
- 英語の記事タイトルは日本語要約も付けてください
- 日時は必ず記録してください
- 同じニュースが複数ソースに出ている場合は重複を排除して最も詳細なものを残す
"""


def create_collector_agent() -> BaseAgent:
    return BaseAgent(
        name="情報収集エージェント",
        system_prompt=SYSTEM_PROMPT,
        tools=SCRAPER_TOOLS,
        tool_executors=SCRAPER_EXECUTORS,
        model=MODEL_HEAVY,
    )
