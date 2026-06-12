"""Construct optional AI providers without importing unused SDKs."""

from __future__ import annotations


def create_provider(name: str, model: str):
    provider = name.strip().lower()
    if not model.strip():
        raise ValueError("model cannot be empty")

    if provider == "anthropic":
        from .providers.anthropic import AnthropicProvider

        return AnthropicProvider(model=model)
    if provider == "openai":
        from .providers.openai import OpenAIProvider

        return OpenAIProvider(model=model)
    raise ValueError("provider must be 'anthropic' or 'openai'")
