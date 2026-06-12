"""JSONL persistence and deduplication for research records."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, TypeVar

from .models import SourceDocument, StrategyRule


Record = TypeVar("Record", SourceDocument, StrategyRule)


def deduplicate_documents(documents: Iterable[SourceDocument]) -> list[SourceDocument]:
    """Keep the first document for each source id while preserving input order."""
    unique: list[SourceDocument] = []
    seen: set[str] = set()
    for document in documents:
        if document.source_id in seen:
            continue
        seen.add(document.source_id)
        unique.append(document)
    return unique


def _save_jsonl(path: str | Path, records: Iterable[Record]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False, newline="\n"
    ) as handle:
        temp_path = Path(handle.name)
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temp_path, target)


def _load_jsonl(path: str | Path) -> list[dict]:
    source = Path(path)
    if not source.exists():
        return []

    rows: list[dict] = []
    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {source}:{line_number}: {exc.msg}") from exc
    return rows


def save_documents(path: str | Path, documents: Iterable[SourceDocument]) -> None:
    _save_jsonl(path, deduplicate_documents(documents))


def load_documents(path: str | Path) -> list[SourceDocument]:
    return [SourceDocument.from_dict(row) for row in _load_jsonl(path)]


def save_rules(path: str | Path, rules: Iterable[StrategyRule]) -> None:
    _save_jsonl(path, rules)


def load_rules(path: str | Path) -> list[StrategyRule]:
    return [StrategyRule.from_dict(row) for row in _load_jsonl(path)]
