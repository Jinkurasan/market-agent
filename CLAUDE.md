# market-agent

金融マーケット情報を自動収集・要約・配信するマルチエージェントアプリ。
将来的にはサービス化・自動化を予定しているが、現在は手動トリガーで運用中。

## 起動コマンド

```bash
python main.py              # 本番実行（Notion/noteに投稿）
python main.py --dry-run    # 動作確認（投稿しない）
python main.py --login bloomberg  # Bloomberg初回認証
python main.py --login wsj        # WSJ初回認証
python main.py --show       # 最後に生成した要約を表示
```

## ディレクトリ構成

```
market-agent/
├── agents/          # エージェント（1ファイル＝1エージェント）
├── tools/           # ツール実装（scrapers/notion/note）
├── sessions/        # ブラウザセッション保存（gitignore対象）
├── output/          # 各ステップの出力ログ（gitignore対象）
├── orchestrator.py  # パイプライン制御
├── main.py          # CLIエントリーポイント
└── config.py        # 環境変数・定数の一元管理
```

## アーキテクチャ

パイプラインは4エージェントが順番に実行される：

```
情報収集 → 要約・分析 → マーケティング最適化 → 配信実行
```

各エージェントは `BaseAgent` を継承し、Claude APIのtool useループで動く。
エージェント間のデータ受け渡しは**プレーンテキスト**（構造化JSONではない）。
これは将来的にエージェントを並列化・分岐させる際も変えない方針。

## エージェントを追加するとき

1. `agents/` に新しいファイルを作り `BaseAgent` を継承する
2. `system_prompt` は日本語で書く（オーナーが日本語話者のため）
3. モデルは `config.py` の定数を使う（直書き禁止）：
   - `MODEL_HEAVY` (claude-opus-4-7) — 収集・分析・長文生成など複雑なタスク
   - `MODEL_LIGHT` (claude-sonnet-4-6) — フォーマット・投稿など軽量タスク
4. `create_xxx_agent()` ファクトリ関数を公開する（`orchestrator.py` から呼ぶ形）

## スクレイパーを追加するとき

`tools/scrapers.py` に以下3点をセットで追加する：

```python
# 1. 関数実装
def scrape_xxx(...) -> dict:
    # 必ず {"source": "名前", "status": "success"|"failed", ...} を返す

# 2. ツール定義（Claudeに渡すスキーマ）
SCRAPER_TOOLS.append({
    "name": "scrape_xxx",
    "description": "...",
    "input_schema": {...}
})

# 3. エグゼキューター登録
SCRAPER_EXECUTORS["scrape_xxx"] = scrape_xxx
```

スクレイパーは失敗しても例外を外に出さない。必ず `{"status": "failed", "error": "..."}` を返すこと。

## 情報ソース一覧

| ソース | 方式 | 認証 |
|--------|------|------|
| Bloomberg | RSS | 不要（有料記事は sessions/bloomberg.json） |
| WSJ | RSS | 不要（有料記事は sessions/wsj.json） |
| investing.com | Playwright | 不要 |
| CME FedWatch | Playwright | 不要 |
| OANDA | Playwright | 不要 |
| 羊飼いFX | Playwright | 不要 |
| X（未実装） | Twitter API v2 Basic | $100/月のAPI契約が必要 |

監視予定のXアカウント（実装時に参照）:
Trump, Reuters, WSJ, YENZO, ユーちぇる監督, USANEWS, たけぞう, パウエル, 井口喜雄, Nick Timiraos

## 配信先

| 配信先 | 方式 | 状態 |
|--------|------|------|
| Notion | Notion API | 要：API key + database ID |
| note.com | Playwright | 要：メール/パスワード |
| X | Twitter API v2 | 未実装（後回し） |

## セキュリティルール

- `.env` / `sessions/` / `output/` はコミットしない（.gitignoreに追加済みであること）
- APIキー・パスワードは必ず `.env` 経由で `config.py` から参照する
- コード中にシークレットを直書きしない（レビュー時に即修正）

## 開発ルール

- **本番投稿前は必ず `--dry-run` で確認する**
- 型ヒントを書く（`dict`, `str`, `list[dict]` など基本的なもので十分）
- コメントは「なぜそうしたか」だけ書く。コードを説明するコメントは書かない
- Playwright を使うスクレイパーは `with sync_playwright() as p:` ブロックで書き、必ず `browser.close()` する
- 新機能は小さく作って `--dry-run` で動作確認してから本番に繋ぐ

## 将来の自動化に向けた設計方針

- `orchestrator.run_pipeline()` はステートレス（何度呼んでも副作用は外部への投稿のみ）
- スケジュール実行化する際は `main.py` にオプションを追加するだけでよい構造にする
- エージェントの並列化（収集と別タスクを同時実行）は `orchestrator.py` だけを変更して対応できる
- 将来のWebサービス化時は `orchestrator.run_pipeline()` をそのままAPIエンドポイントから呼べる

## 環境セットアップ（初回）

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# .env を編集して各APIキーを設定
```
