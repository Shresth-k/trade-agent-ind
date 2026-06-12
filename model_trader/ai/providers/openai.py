"""OpenAI Responses API adapter using Structured Outputs."""

from __future__ import annotations

import os
from typing import Any

from ..base import ProviderResponse


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str, api_key: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install the OpenAI provider with: pip install openai") from exc

        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.model = model
        self._client = OpenAI(api_key=key)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> ProviderResponse:
        response = self._client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "strategy_research",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        usage = getattr(response, "usage", None)
        return ProviderResponse(
            text=response.output_text,
            response_id=str(getattr(response, "id", "")),
            usage={
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            },
        )
