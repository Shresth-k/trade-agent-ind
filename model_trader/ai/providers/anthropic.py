"""Anthropic Messages API adapter for the research provider contract."""

from __future__ import annotations

import json
import os
from typing import Any

from ..base import ProviderResponse


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None = None, max_tokens: int = 12000):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("Install the Anthropic provider with: pip install anthropic") from exc

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=key)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> ProviderResponse:
        schema_prompt = (
            f"{user_prompt}\n\nReturn only one JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema, sort_keys=True)}"
        )
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": schema_prompt}],
        )
        text = next(
            (block.text for block in response.content if getattr(block, "type", None) == "text"),
            "",
        )
        usage = getattr(response, "usage", None)
        return ProviderResponse(
            text=text,
            response_id=str(getattr(response, "id", "")),
            usage={
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
        )
