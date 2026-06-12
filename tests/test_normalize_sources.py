import pytest

from model_trader.research import SourceKind, load_documents
from pipeline.normalize_sources import document_from_text, normalize_directory


def test_youtube_text_header_becomes_source_metadata(tmp_path):
    transcript = tmp_path / "abc123.txt"
    transcript.write_text(
        "# Video: https://youtube.com/watch?v=abc123\n\nTrade only after the retest.",
        encoding="utf-8",
    )

    document = document_from_text(transcript)

    assert document.kind == SourceKind.YOUTUBE
    assert document.url.endswith("abc123")
    assert document.text == "Trade only after the retest."


def test_normalize_directory_writes_jsonl(tmp_path):
    input_dir = tmp_path / "transcripts"
    input_dir.mkdir()
    (input_dir / "note.txt").write_text("Manual trading note", encoding="utf-8")
    output = tmp_path / "corpus" / "sources.jsonl"

    documents = normalize_directory(input_dir, output)

    assert len(documents) == 1
    assert load_documents(output)[0].metadata["original_file"] == "note.txt"


def test_missing_transcripts_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="No .txt files"):
        normalize_directory(tmp_path, tmp_path / "sources.jsonl")
