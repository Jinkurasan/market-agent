"""
market-agent Web UI
streamlit run app.py で起動
"""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="market-agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0f1117; }
[data-testid="stHeader"]           { background-color: #0f1117; }
[data-testid="stSidebar"]          { background-color: #0f1117; }
section[data-testid="stMain"]      { background-color: #0f1117; }

h1, h2, h3 { color: #e2e8f0; }
p, li       { color: #a0aec0; }

.title {
    font-size: 32px; font-weight: 800;
    color: #90cdf4; text-align: center;
    padding: 24px 0 6px;
}
.subtitle {
    color: #718096; text-align: center;
    font-size: 14px; margin-bottom: 36px;
}
.status-ok   { color: #68d391; font-size: 13px; }
.status-warn { color: #f6ad55; font-size: 13px; }
.status-err  { color: #fc8181; font-size: 13px; }

div[data-testid="stExpander"] {
    background: #1a202c;
    border: 1px solid #2d3748;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# ── ヘッダー ────────────────────────────────────────────────────────────────
st.markdown('<div class="title">📊 market-agent</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">金融情報収集・要約・配信システム</div>', unsafe_allow_html=True)
st.divider()


# ── ステータス確認 ───────────────────────────────────────────────────────────
def check_status() -> dict:
    from config import ANTHROPIC_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID, NOTE_EMAIL, LINE_CHANNEL_ACCESS_TOKEN
    return {
        "Anthropic API": bool(ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("ここに")),
        "Notion":        bool(NOTION_API_KEY and NOTION_DATABASE_ID),
        "note.com":      bool(NOTE_EMAIL),
        "LINE":          bool(LINE_CHANNEL_ACCESS_TOKEN),
    }

with st.container():
    st.markdown("#### システム状態")
    status = check_status()
    cols = st.columns(len(status))
    icons = {"Anthropic API": "🤖", "Notion": "📓", "note.com": "📝", "LINE": "💬"}
    for col, (name, ok) in zip(cols, status.items()):
        with col:
            label = "接続済み" if ok else "未設定"
            css = "status-ok" if ok else "status-warn"
            st.markdown(f'<p class="{css}">{icons[name]} {name}：{label}</p>', unsafe_allow_html=True)

st.divider()


# ── メインボタン ─────────────────────────────────────────────────────────────
st.markdown("#### 実行")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    dry_run = st.checkbox("テストモード（Notion/noteへの投稿をスキップ）", value=True)

with col2:
    run_btn = st.button("📥　情報収集 → 記事生成", use_container_width=True, type="primary")

with col3:
    strategy_btn = st.button("🎯　COO戦略レポート", use_container_width=True)


# ── パイプライン実行 ─────────────────────────────────────────────────────────
if run_btn:
    with st.status("パイプラインを実行中...", expanded=True) as status_box:
        try:
            from agents.collector_agent import create_collector_agent
            from agents.summarizer_agent import create_summarizer_agent
            from agents.marketer_agent import create_marketer_agent
            from agents.executor_agent import create_executor_agent
            from orchestrator import _save_output, _parse_formatted

            now = datetime.now()

            # Step 1
            st.write("🔍 情報収集エージェント 起動中...")
            collector = create_collector_agent()
            collected = collector.run(
                f"現在時刻: {now.strftime('%Y年%m月%d日 %H:%M')}\n"
                "すべての情報ソースから最新マーケット情報を収集してください。"
            )
            _save_output("1_collected", collected)
            st.write("✅ 情報収集 完了")

            # Step 2
            st.write("🧠 分析・要約エージェント 起動中...")
            summarizer = create_summarizer_agent()
            summary = summarizer.run(
                f"以下の収集データを分析して、マーケットレポートを作成してください。\n\n{collected}"
            )
            _save_output("2_summary", summary)
            st.write("✅ 要約・分析 完了")

            # Step 3
            st.write("✍️ マーケティングエージェント 起動中...")
            marketer = create_marketer_agent()
            formatted_raw = marketer.run(
                f"以下のマーケットレポートを各プラットフォーム向けに最適化してください。\n\n{summary}"
            )
            _save_output("3_formatted", formatted_raw)
            formatted = _parse_formatted(formatted_raw)
            st.write("✅ コンテンツ最適化 完了")

            # Step 4
            if dry_run:
                st.write("⚠️ テストモード：投稿をスキップしました")
            else:
                st.write("🚀 配信エージェント 起動中...")
                executor = create_executor_agent()
                executor.run(
                    f"Notionタイトル: {formatted.get('notion', {}).get('title', 'マーケットレポート')}\n"
                    f"Notion本文:\n{formatted.get('notion', {}).get('content', summary)}\n\n"
                    f"noteタイトル: {formatted.get('note', {}).get('title', 'マーケットレポート')}\n"
                    f"note本文:\n{formatted.get('note', {}).get('content', summary)}"
                )
                st.write("✅ Notion投稿 完了")

                # LINE自動配信
                line_content_auto = formatted.get("line", "")
                if line_content_auto:
                    from config import LINE_CHANNEL_ACCESS_TOKEN
                    if LINE_CHANNEL_ACCESS_TOKEN:
                        st.write("📱 LINE配信中...")
                        from tools.line_sender import send_line_broadcast
                        line_result = send_line_broadcast(line_content_auto)
                        if line_result["status"] == "success":
                            st.write("✅ LINE配信 完了")
                        else:
                            st.write(f"⚠️ LINE配信失敗: {line_result.get('error', '')}")

            status_box.update(label="✅ 完了！", state="complete")

            # 結果表示
            st.divider()
            st.markdown("#### 生成結果")

            note_title = formatted.get("note", {}).get("title", "")
            note_content = formatted.get("note", {}).get("content", summary)

            if note_title:
                st.success(f"記事タイトル：{note_title}")

            # noteコピーエリア
            with st.expander("📝 note投稿用（タイトル＋本文）", expanded=True):
                st.markdown("**タイトル**（コピーして貼り付け）")
                st.code(note_title, language=None)
                st.markdown("**本文**（コピーして貼り付け）")
                st.text_area("note本文", note_content, height=400, key="note_content_copy")
                st.caption("👆 上の本文をコピーして https://note.com/notes/new に貼り付けてください")

            with st.expander("📄 マーケットレポート全文", expanded=False):
                st.markdown(summary)

            line_content = formatted.get("line", "")
            if line_content:
                with st.expander("📱 LINE配信内容", expanded=True):
                    st.text_area("LINE本文", line_content, height=200, key="line_content_copy")
                    if dry_run:
                        from config import LINE_CHANNEL_ACCESS_TOKEN
                        if LINE_CHANNEL_ACCESS_TOKEN:
                            if st.button("💬 LINEに今すぐ配信", type="primary"):
                                from tools.line_sender import send_line_broadcast
                                result = send_line_broadcast(line_content)
                                if result["status"] == "success":
                                    st.success("✅ LINE配信完了！")
                                else:
                                    st.error(f"❌ LINE配信失敗: {result.get('error', '')}")
                        else:
                            st.caption("LINE未設定 — Streamlit Cloud SecretsにLINE_CHANNEL_ACCESS_TOKENを追加してください")
                    else:
                        st.caption("✅ 配信済み（テストモードOFFで自動送信されました）")

            tweets = formatted.get("tweets", [])
            if tweets:
                with st.expander(f"🐦 ツイート候補（{len(tweets)}件）"):
                    for i, tweet in enumerate(tweets, 1):
                        st.text_area(f"ツイート {i}", tweet, height=80, key=f"tweet_{i}")

        except Exception as e:
            status_box.update(label="❌ エラーが発生しました", state="error")
            st.error(f"エラー: {e}")


# ── COO戦略レポート ──────────────────────────────────────────────────────────
if strategy_btn:
    with st.status("COO戦略レポートを作成中...", expanded=True) as status_box:
        try:
            from agents.sns_strategy_agent import create_sns_strategy_agent
            from agents.content_planning_agent import create_content_planning_agent
            from agents.coo_agent import create_coo_agent
            from orchestrator import _save_output, _load_latest_output

            recent = _load_latest_output("2_summary")

            st.write("📣 SNS戦略部 起動中...")
            sns = create_sns_strategy_agent()
            sns_strategy = sns.run(
                f"現在の市場情報:\n{recent}\n\nX・noteでのSNS発信戦略を立案してください。"
            )
            _save_output("strategy_sns", sns_strategy)
            st.write("✅ SNS戦略 完了")

            st.write("📅 コンテンツ企画部 起動中...")
            planner = create_content_planning_agent()
            content_plan = planner.run(
                f"市場情報:\n{recent}\n\nSNS戦略:\n{sns_strategy}\n\n直近1週間のコンテンツカレンダーを作成してください。"
            )
            _save_output("strategy_content", content_plan)
            st.write("✅ コンテンツ企画 完了")

            st.write("🎯 COO 統合レポート作成中...")
            coo = create_coo_agent()
            coo_report = coo.run(
                f"【SNS戦略部】\n{sns_strategy}\n\n【コンテンツ企画部】\n{content_plan}"
            )
            _save_output("strategy_coo", coo_report)
            st.write("✅ COOレポート 完了")

            status_box.update(label="✅ 完了！", state="complete")

            st.divider()
            st.markdown("#### COOレポート")
            with st.expander("🎯 COOレポート全文", expanded=True):
                st.markdown(coo_report)
            with st.expander("📣 SNS戦略部レポート"):
                st.markdown(sns_strategy)
            with st.expander("📅 コンテンツ企画部レポート"):
                st.markdown(content_plan)

        except Exception as e:
            status_box.update(label="❌ エラーが発生しました", state="error")
            st.error(f"エラー: {e}")


# ── 過去の記事履歴 ───────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 過去の記事")

summaries = sorted(OUTPUT_DIR.glob("*_2_summary.txt"), reverse=True)[:5]
if summaries:
    for f in summaries:
        ts = f.stem[:15].replace("_", " ")
        with st.expander(f"📄 {ts}"):
            st.markdown(f.read_text(encoding="utf-8"))
else:
    st.caption("まだ記事がありません。「情報収集 → 記事生成」を実行してください。")
