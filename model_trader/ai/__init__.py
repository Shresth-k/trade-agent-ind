"""Provider-neutral interfaces for model-assisted research."""

from .base import AIProvider, ProviderResponse
from .factory import create_provider

__all__ = ["AIProvider", "ProviderResponse", "create_provider"]
