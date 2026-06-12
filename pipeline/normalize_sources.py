"""Convert existing transcript text files into a normalized research corpus.

Usage:
    python -m pipeline.normalize_sources <input_dir> <output_jsonl>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from model_trader.research import SourceDocument, SourceKind, make_source_id, save_documents


VIDEO_HEADER = re.compile(r"^# Video:\s*(?P<url>\S+)\s*$")


def document_from_text(path: Path) -> SourceDocument:
    raw = path.read_text(encoding="utf-8").strip()
    lines = raw.splitlines()
    url = ""
    text = raw
    kind = SourceKind.TRANSCRIPT

    if lines:
        match = VIDEO_HEADER.match(lines[0].strip())
        if match:
            url = match.group("url")
            text = "\n".join(lines[1:]).strip()
            kind = SourceKind.YOUTUBE

    canonical_url = url or path.resolve().as_uri()
    return SourceDocument(
        source_id=make_source_id(kind, canonical_url),
        kind=kind,
        url=canonical_url,
        title=path.stem,
        text=text,
        metadata={"original_file": path.name},
    )


def normalize_directory(input_dir: Path, output_path: Path) -> list[SourceDocument]:
    documents = [document_from_text(path) for path in sorted(input_dir.glob("*.txt"))]
    if not documents:
        raise ValueError(f"No .txt files found in {input_dir}")
    save_documents(output_path, documents)
    return documents


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m pipeline.normalize_sources <input_dir> <output_jsonl>")
        raise SystemExit(1)

    documents = normalize_directory(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"Normalized {len(documents)} source documents -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
