"""Small provider contract used by deterministic research workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    response_id: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


class AIProvider(Protocol):
    name: str
    model: str

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> ProviderResponse:
        """Return one JSON object matching the requested schema."""
        ...
