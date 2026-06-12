"""Research provenance models for turning public content into testable rules."""

from .corpus import deduplicate_documents, load_documents, load_rules, save_documents, save_rules
from .models import (
    Evidence,
    ReviewStatus,
    RuleKind,
    SourceDocument,
    SourceKind,
    StrategyRule,
    make_source_id,
)
from .extraction import Contradiction, ExtractionResult, extract_strategy_rules, validate_extraction

__all__ = [
    "Evidence",
    "Contradiction",
    "ExtractionResult",
    "ReviewStatus",
    "RuleKind",
    "SourceDocument",
    "SourceKind",
    "StrategyRule",
    "deduplicate_documents",
    "extract_strategy_rules",
    "load_documents",
    "load_rules",
    "make_source_id",
    "save_documents",
    "save_rules",
    "validate_extraction",
]
