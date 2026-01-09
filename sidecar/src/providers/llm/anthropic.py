from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, cast

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

if TYPE_CHECKING:
    from anthropic.types import MessageParam
else:
    MessageParam = Any

from ..base import LLMProvider


def _to_anthropic_messages(history: List[Dict[str, Any]], prompt: str) -> list[MessageParam]:
    messages: list[MessageParam] = []

    for msg in history[-10:]:
        role_raw = str(msg.get("role", "user")).lower()
        content = str(msg.get("content", ""))
        if not content:
            continue

        # Anthropic expects roles: "user" | "assistant".
        role = role_raw if role_raw in ("user", "assistant") else "user"
        messages.append(cast(MessageParam, {"role": role, "content": content}))

    messages.append(cast(MessageParam, {"role": "user", "content": prompt}))
    return messages


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude implementation of LLMProvider."""

    def __init__(self, api_key: str):
        if AsyncAnthropic is None:
            raise ImportError("anthropic package is not installed")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20240620"

    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
        system_prompt = (
            "You are a helpful interview assistant for a job candidate. "
            "Respond in first person as the candidate (use 'I'). "
            "Prefer facts supported by the provided context; do not invent schools, titles, companies, dates, or metrics. "
            "If a detail isn't in the context, omit it or say 'I can share details if helpful.' "
            "Be concise and do not repeat sentences or paragraphs. "
            "For intro questions (e.g., 'Tell me about yourself', 'Who are you?', 'Walk me through your background'), "
            "answer as a 30–60 second pitch: one-line headline (role + focus); one-line education; 2–3 bullets of experience highlights; one-line close tying to the role.\n\n"
            f"Context:\n{context}"
        )


        messages = _to_anthropic_messages(history=history, prompt=prompt)

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=cast(Any, messages),
        ) as stream:
            async for text in stream.text_stream:
                yield text

