import json
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings


class DeepSeekStreamClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.llm_api_key

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        reasoning_mode: str,
    ) -> AsyncGenerator[dict[str, str], None]:
        if not self.api_key:
            yield {"type": "error", "content": "LLM_API_KEY is not configured."}
            return

        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if reasoning_mode == "disabled":
            payload["thinking"] = {"type": "disabled"}
        else:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = reasoning_mode

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                if response.status_code >= 400:
                    error_body = await response.aread()
                    yield {"type": "error", "content": error_body.decode("utf-8", errors="ignore")}
                    return
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        yield {"type": "done", "content": ""}
                        return
                    chunk = json.loads(data)
                    usage = chunk.get("usage")
                    if usage:
                        yield {
                            "type": "usage",
                            "content": json.dumps(
                                {
                                    "prompt_cache_hit_tokens": usage.get("prompt_cache_hit_tokens", 0),
                                    "prompt_cache_miss_tokens": usage.get("prompt_cache_miss_tokens", 0),
                                }
                            ),
                        }
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    reasoning_content = delta.get("reasoning_content")
                    content = delta.get("content")
                    if reasoning_content:
                        yield {"type": "reasoning", "content": reasoning_content}
                    if content:
                        yield {"type": "content", "content": content}
