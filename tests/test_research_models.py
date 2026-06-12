from __future__ import annotations

import pytest

from model_trader.research import (
    Evidence,
    ReviewStatus,
    RuleKind,
    SourceDocument,
    SourceKind,
    StrategyRule,
    load_documents,
    load_rules,
    make_source_id,
    save_documents,
    save_rules,
)


def test_source_documents_round_trip_and_deduplicate(tmp_path):
    source_id = make_source_id(SourceKind.YOUTUBE, "https://youtu.be/example")
    document = SourceDocument(
        source_id=source_id,
        kind=SourceKind.YOUTUBE,
        url="https://youtu.be/example",
        title="Opening range setup",
        text="Wait for the opening range, then trade the retest.",
    )
    path = tmp_path / "sources.jsonl"

    save_documents(path, [document, document])

    assert load_documents(path) == [document]


def test_rule_requires_review_evidence_and_determinism():
    rule = StrategyRule(
        rule_id="opening-range-retest",
        name="Opening range retest",
        kind=RuleKind.TRIGGER,
        condition="Price closes outside the first 15-minute range.",
        pass_if="A later 5-minute candle retests and rejects the boundary.",
        fail_if="Price closes back inside the range.",
        confidence=0.9,
        deterministic=True,
        review_status=ReviewStatus.APPROVED,
    )

    assert not rule.is_implementation_ready()

    rule.evidence.append(Evidence("video-1", "I wait for the retest.", "12:41"))
    assert rule.is_implementation_ready()


def test_rules_round_trip(tmp_path):
    rule = StrategyRule(
        rule_id="avoid-open",
        name="Avoid the first five minutes",
        kind=RuleKind.NO_TRADE,
        condition="Current time is before 09:20 Asia/Kolkata.",
        pass_if="Current time is 09:20 or later.",
        fail_if="Current time is before 09:20.",
        evidence=[Evidence("video-2", "I never trade the first five minutes.", "03:12")],
        confidence=0.85,
        deterministic=True,
        review_status=ReviewStatus.APPROVED,
    )
    path = tmp_path / "rules.jsonl"

    save_rules(path, [rule])

    assert load_rules(path) == [rule]


def test_confidence_is_bounded():
    with pytest.raises(ValueError, match="confidence"):
        StrategyRule(
            rule_id="bad",
            name="Bad confidence",
            kind=RuleKind.RISK,
            condition="x",
            pass_if="y",
            fail_if="z",
            confidence=1.1,
        )
