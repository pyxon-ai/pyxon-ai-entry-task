"""Optional LLM connector (Anthropic or any OpenAI-compatible endpoint).

Configured purely through environment variables so no key is ever committed:

* ``ANTHROPIC_API_KEY`` (+ optional ``PYXON_LLM_MODEL``, default ``claude-sonnet-4-5``)
* or ``OPENAI_API_KEY`` (+ optional ``OPENAI_BASE_URL``, ``PYXON_LLM_MODEL``)

If neither is set, :func:`get_llm` returns ``None`` and the system falls back
to extractive answers/summaries, so everything still runs offline.
"""
from __future__ import annotations

import os

import requests


class LLM:
    def __init__(self, provider: str, api_key: str, model: str, base_url: str | None = None):
        self.provider, self.api_key, self.model = provider, api_key, model
        self.base_url = base_url

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str:
        if self.provider == "anthropic":
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": self.model, "max_tokens": max_tokens, "system": system,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])
        r = requests.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def get_llm() -> LLM | None:
    model = os.getenv("PYXON_LLM_MODEL")
    if key := os.getenv("ANTHROPIC_API_KEY"):
        return LLM("anthropic", key, model or "claude-sonnet-4-5")
    if key := os.getenv("OPENAI_API_KEY"):
        return LLM("openai", key, model or "gpt-4o-mini", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    return None
