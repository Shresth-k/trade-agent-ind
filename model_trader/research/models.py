"""Typed, auditable records for content research and strategy extraction."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SourceKind(str, Enum):
    YOUTUBE = "youtube"
    X = "x"
    ARTICLE = "article"
    TRANSCRIPT = "transcript"
    MANUAL = "manual"


class RuleKind(str, Enum):
    CONTEXT = "context"
    TRIGGER = "trigger"
    CONFIRMATION = "confirmation"
    INVALIDATION = "invalidation"
    EXIT = "exit"
    RISK = "risk"
    NO_TRADE = "no_trade"
    INSTRUMENT_SELECTION = "instrument_selection"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_source_id(kind: SourceKind | str, url: str, text: str = "") -> str:
    """Create a stable short identifier from a source type and canonical content."""
    kind_value = kind.value if isinstance(kind, SourceKind) else str(kind)
    identity = f"{kind_value}\n{url.strip()}\n{text.strip()}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()[:16]


@dataclass
class SourceDocument:
    """One normalized piece of public research content."""

    source_id: str
    kind: SourceKind
    url: str
    text: str
    title: str = ""
    creator: str = ""
    published_at: str | None = None
    collected_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id cannot be empty")
        if not self.text.strip():
            raise ValueError("source text cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceDocument":
        payload = dict(data)
        payload["kind"] = SourceKind(payload["kind"])
        return cls(**payload)


@dataclass
class Evidence:
    """A source citation supporting one extracted strategy rule."""

    source_id: str
    excerpt: str
    locator: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("evidence source_id cannot be empty")
        if not self.excerpt.strip():
            raise ValueError("evidence excerpt cannot be empty")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        return cls(**data)


@dataclass
class StrategyRule:
    """A candidate trading rule that must be reviewed before implementation."""

    rule_id: str
    name: str
    kind: RuleKind
    condition: str
    pass_if: str
    fail_if: str
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 0.0
    deterministic: bool = False
    review_status: ReviewStatus = ReviewStatus.DRAFT
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or not self.name.strip():
            raise ValueError("rule_id and name cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def is_implementation_ready(self, minimum_confidence: float = 0.7) -> bool:
        """Return true only for approved, cited, mechanical rules."""
        return (
            self.review_status == ReviewStatus.APPROVED
            and self.deterministic
            and bool(self.evidence)
            and self.confidence >= minimum_confidence
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["review_status"] = self.review_status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyRule":
        payload = dict(data)
        payload["kind"] = RuleKind(payload["kind"])
        payload["review_status"] = ReviewStatus(payload["review_status"])
        payload["evidence"] = [Evidence.from_dict(item) for item in payload.get("evidence", [])]
        return cls(**payload)
