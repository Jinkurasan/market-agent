"""
全エージェントの基底クラス。
Claude APIのtool useループを管理する。
"""
import json
import anthropic
from rich.console import Console

console = Console()


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[dict],
        tool_executors: dict,
        model: str = "claude-opus-4-7",
    ):
        self.name = name
        self.client = anthropic.Anthropic()
        self.model = model
        self.tools = tools
        self.tool_executors = tool_executors

        # プロンプトキャッシュ対応のシステムプロンプト
        self.system = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def run(self, user_message: str, max_turns: int = 15) -> str:
        """エージェントを実行してテキスト結果を返す"""
        console.print(f"\n[bold cyan]▶ {self.name}[/bold cyan] 起動中...")
        messages = [{"role": "user", "content": user_message}]
        turns = 0

        while turns < max_turns:
            turns += 1
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8096,
                system=self.system,
                tools=self.tools if self.tools else anthropic.NOT_GIVEN,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                result = self._extract_text(response.content)
                console.print(f"[bold green]✓ {self.name}[/bold green] 完了")
                return result

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        console.print(f"  [yellow]→ ツール実行:[/yellow] {block.name}")
                        try:
                            result = self.tool_executors[block.name](**block.input)
                        except Exception as e:
                            result = {"error": str(e), "status": "failed"}
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                return self._extract_text(response.content)

        return self._extract_text(messages[-1].get("content", []) if isinstance(messages[-1].get("content"), list) else [])

    def _extract_text(self, content) -> str:
        return "\n".join(
            block.text for block in content if hasattr(block, "type") and block.type == "text"
        )
