"""Validated and cached AI extraction of strategy rules from source documents."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable

from model_trader.ai import AIProvider

from .corpus import load_rules, save_rules
from .models import Evidence, ReviewStatus, RuleKind, SourceDocument, StrategyRule


PROMPT_VERSION = "strategy-rules-v1"

SYSTEM_PROMPT = """You are a trading-strategy research analyst. Extract only rules explicitly
supported by the supplied sources. Do not decide whether the strategy is profitable. Do not invent
missing thresholds. Every rule must cite a short exact excerpt and its source_id. Mark deterministic
false when a human judgment cannot yet be expressed mechanically. Report conflicts separately.
The output is a proposal for human review, never trading advice or an executable order."""


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "rules", "contradictions", "open_questions"],
    "properties": {
        "summary": {"type": "string"},
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "rule_id", "name", "kind", "condition", "pass_if", "fail_if",
                    "confidence", "deterministic", "tags", "notes", "evidence",
                ],
                "properties": {
                    "rule_id": {"type": "string"},
                    "name": {"type": "string"},
                    "kind": {"type": "string", "enum": [kind.value for kind in RuleKind]},
                    "condition": {"type": "string"},
                    "pass_if": {"type": "string"},
                    "fail_if": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "deterministic": {"type": "boolean"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["source_id", "excerpt", "locator", "notes"],
                            "properties": {
                                "source_id": {"type": "string"},
                                "excerpt": {"type": "string"},
                                "locator": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "contradictions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["contradiction_id", "rule_ids", "description", "resolution_hint"],
                "properties": {
                    "contradiction_id": {"type": "string"},
                    "rule_ids": {"type": "array", "minItems": 2, "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "resolution_hint": {"type": "string"},
                },
            },
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    rule_ids: list[str]
    description: str
    resolution_hint: str = ""


@dataclass
class ExtractionResult:
    summary: str
    rules: list[StrategyRule]
    contradictions: list[Contradiction] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    run_id: str = ""
    cached: bool = False


def build_user_prompt(documents: Iterable[SourceDocument], max_chars: int = 120_000) -> str:
    sections = [
        "Extract candidate rules for an Indian intraday paper-trading research project.",
        "Prefer setup context, trigger, confirmation, invalidation, exit, risk, no-trade, and option-selection rules.",
        "Use exact source excerpts. If a threshold is missing, preserve the ambiguity and mark deterministic false.",
    ]
    for document in documents:
        sections.append(
            "\n".join(
                [
                    f"=== SOURCE {document.source_id} ===",
                    f"kind: {document.kind.value}",
                    f"title: {document.title}",
                    f"url: {document.url}",
                    document.text,
                ]
            )
        )
    prompt = "\n\n".join(sections)
    if len(prompt) > max_chars:
        raise ValueError(
            f"Corpus prompt is {len(prompt):,} characters; limit is {max_chars:,}. "
            "Split the corpus into a smaller research batch."
        )
    return prompt


def extract_strategy_rules(
    provider: AIProvider,
    documents: list[SourceDocument],
    output_dir: str | Path,
    *,
    force: bool = False,
    max_chars: int = 120_000,
) -> ExtractionResult:
    if not documents:
        raise ValueError("At least one source document is required")

    user_prompt = build_user_prompt(documents, max_chars=max_chars)
    run_id = _make_run_id(provider.name, provider.model, documents, user_prompt)
    run_dir = Path(output_dir) / "runs" / run_id
    validated_path = run_dir / "validated.json"

    if validated_path.exists() and not force:
        return _result_from_dict(_load_json(validated_path), cached=True)

    response = provider.complete_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=EXTRACTION_SCHEMA,
    )
    raw_payload = _parse_json_object(response.text)
    result = validate_extraction(raw_payload, documents)
    result.run_id = run_id

    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "manifest.json",
        {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prompt_version": PROMPT_VERSION,
            "provider": provider.name,
            "model": provider.model,
            "source_ids": [document.source_id for document in documents],
            "response_id": response.response_id,
            "usage": response.usage,
        },
    )
    (run_dir / "raw_response.txt").write_text(response.text, encoding="utf-8")
    _write_json(validated_path, _result_to_dict(result))
    save_rules(Path(output_dir) / "candidate_rules.jsonl", result.rules)
    _write_json(
        Path(output_dir) / "contradictions.json",
        [asdict(item) for item in result.contradictions],
    )
    _write_summary(Path(output_dir) / "research_summary.md", result)
    return result


def validate_extraction(payload: dict[str, Any], documents: list[SourceDocument]) -> ExtractionResult:
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")

    sources = {document.source_id: document for document in documents}
    rules: list[StrategyRule] = []
    rule_ids: set[str] = set()

    for index, raw_rule in enumerate(payload.get("rules", []), start=1):
        try:
            rule_id = str(raw_rule["rule_id"]).strip()
            if rule_id in rule_ids:
                raise ValueError(f"duplicate rule_id {rule_id!r}")
            evidence = [Evidence.from_dict(item) for item in raw_rule["evidence"]]
            for citation in evidence:
                document = sources.get(citation.source_id)
                if document is None:
                    raise ValueError(f"unknown source_id {citation.source_id!r}")
                if _normalize_text(citation.excerpt) not in _normalize_text(document.text):
                    raise ValueError(
                        f"excerpt for source {citation.source_id!r} is not present in source text"
                    )

            rule = StrategyRule(
                rule_id=rule_id,
                name=str(raw_rule["name"]),
                kind=RuleKind(raw_rule["kind"]),
                condition=str(raw_rule["condition"]),
                pass_if=str(raw_rule["pass_if"]),
                fail_if=str(raw_rule["fail_if"]),
                evidence=evidence,
                confidence=float(raw_rule["confidence"]),
                deterministic=bool(raw_rule["deterministic"]),
                review_status=ReviewStatus.NEEDS_REVIEW,
                tags=[str(tag) for tag in raw_rule.get("tags", [])],
                notes=str(raw_rule.get("notes", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid rule {index}: {exc}") from exc
        rules.append(rule)
        rule_ids.add(rule.rule_id)

    contradictions: list[Contradiction] = []
    for index, raw_item in enumerate(payload.get("contradictions", []), start=1):
        referenced = [str(value) for value in raw_item.get("rule_ids", [])]
        unknown = [rule_id for rule_id in referenced if rule_id not in rule_ids]
        if unknown:
            raise ValueError(f"Contradiction {index} references unknown rules: {unknown}")
        if len(set(referenced)) < 2:
            raise ValueError(f"Contradiction {index} must reference at least two rules")
        contradictions.append(
            Contradiction(
                contradiction_id=str(raw_item["contradiction_id"]),
                rule_ids=referenced,
                description=str(raw_item["description"]),
                resolution_hint=str(raw_item.get("resolution_hint", "")),
            )
        )

    return ExtractionResult(
        summary=str(payload.get("summary", "")),
        rules=rules,
        contradictions=contradictions,
        open_questions=[str(item) for item in payload.get("open_questions", [])],
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, count=1)
        clean = re.sub(r"\s*```$", "", clean, count=1)
    try:
        value = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI provider returned invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("AI provider must return one JSON object")
    return value


def _make_run_id(
    provider_name: str,
    model: str,
    documents: list[SourceDocument],
    user_prompt: str,
) -> str:
    payload = {
        "prompt_version": PROMPT_VERSION,
        "provider": provider_name,
        "model": model,
        "source_ids": [document.source_id for document in documents],
        "prompt": user_prompt,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:20]


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _result_to_dict(result: ExtractionResult) -> dict[str, Any]:
    return {
        "summary": result.summary,
        "rules": [rule.to_dict() for rule in result.rules],
        "contradictions": [asdict(item) for item in result.contradictions],
        "open_questions": result.open_questions,
        "run_id": result.run_id,
    }


def _result_from_dict(data: dict[str, Any], cached: bool) -> ExtractionResult:
    return ExtractionResult(
        summary=data["summary"],
        rules=[StrategyRule.from_dict(item) for item in data.get("rules", [])],
        contradictions=[Contradiction(**item) for item in data.get("contradictions", [])],
        open_questions=data.get("open_questions", []),
        run_id=data.get("run_id", ""),
        cached=cached,
    )


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def _write_summary(path: Path, result: ExtractionResult) -> None:
    lines = ["# Research Summary", "", result.summary, "", "## Candidate Rules", ""]
    for rule in result.rules:
        lines.extend(
            [
                f"### {rule.name}",
                "",
                f"- ID: `{rule.rule_id}`",
                f"- Type: `{rule.kind.value}`",
                f"- Confidence: `{rule.confidence:.2f}`",
                f"- Deterministic: `{str(rule.deterministic).lower()}`",
                f"- Review: `{rule.review_status.value}`",
                f"- Condition: {rule.condition}",
                f"- Pass: {rule.pass_if}",
                f"- Fail: {rule.fail_if}",
                "",
            ]
        )
    lines.extend(["## Contradictions", ""])
    for item in result.contradictions:
        lines.append(f"- `{item.contradiction_id}` ({', '.join(item.rule_ids)}): {item.description}")
    lines.extend(["", "## Open Questions", ""])
    lines.extend(f"- {question}" for question in result.open_questions)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
