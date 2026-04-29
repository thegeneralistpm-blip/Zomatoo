from __future__ import annotations

import json
import os
from typing import Any

from groq import Groq

from phase4.prompt_builder import build_messages


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise
        return json.loads(cleaned[start : end + 1])


def rank_with_groq(
    phase3_payload: dict[str, Any],
    top_k: int = 5,
    model: str = "llama-3.3-70b-versatile",
) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    messages = build_messages(phase3_payload=phase3_payload, top_k=top_k)
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )

    content = completion.choices[0].message.content or ""
    parsed = _extract_json_object(content)
    return {
        "raw_text": content,
        "parsed": parsed,
        "model": model,
    }
