from __future__ import annotations

import json
from typing import Any, Sequence

from ..config import LLMConfig


def build_openai_client(llm_config: LLMConfig):
    from openai import OpenAI

    return OpenAI(
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        timeout=llm_config.timeout_seconds,
    )


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(raw_text[start : end + 1])


def _safe_message_content(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)
    return str(content)


def _choice_finish_reason(choice: Any) -> str | None:
    finish_reason = getattr(choice, "finish_reason", None)
    return str(finish_reason) if finish_reason is not None else None


def query_json_completion(
    *,
    client: Any,
    llm_config: LLMConfig,
    messages: Sequence[dict[str, str]],
    retry_messages: Sequence[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not llm_config.api_key:
        raise ValueError("missing LLM API key")
    max_tokens = llm_config.max_tokens
    active_messages = list(messages)
    last_error: Exception | None = None
    total_attempts = llm_config.max_retries + 1
    for attempt in range(total_attempts):
        response = client.chat.completions.create(
            model=llm_config.model,
            temperature=llm_config.temperature,
            max_tokens=max_tokens,
            messages=active_messages,
        )
        choice = response.choices[0]
        finish_reason = _choice_finish_reason(choice)
        raw_content = _safe_message_content(choice.message).strip()
        try:
            return _extract_json_object(raw_content)
        except Exception as exc:
            last_error = exc
            if finish_reason != "length" and raw_content:
                break
            if attempt >= total_attempts - 1:
                break
            max_tokens = min(max_tokens * 2, 2048)
            if retry_messages is not None:
                active_messages = list(retry_messages)
    raise ValueError(f"LLM output parse failed: {last_error}") from last_error
