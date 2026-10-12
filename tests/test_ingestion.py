from __future__ import annotations

import json
from pathlib import Path

import pytest

from scopecheck.ingestion import chunks_to_json, parse_document

FIXTURES = Path(__file__).parent / "fixtures" / "ingestion"


def test_txt_preserves_scientific_values_negation_and_traceability() -> None:
    path = FIXTURES / "sample.txt"
    text = path.read_text()
    chunks = parse_document(path, "txt-doc")

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.text == text.rstrip()
    assert "3.2 mg/L" in chunk.text and "22 °C" in chunk.text
    assert "no statistically significant increase" in chunk.text
    assert chunk.start_offset == 0
    assert chunk.end_offset == len(text.rstrip())
    assert text[chunk.start_offset : chunk.end_offset] == chunk.text
    assert chunk.document_id == "txt-doc"
    assert chunk.page_number is None


def test_markdown_structure_metadata_and_json() -> None:
    path = FIXTURES / "sample.md"
    chunks = parse_document(path, "md-doc")
    joined = "\n".join(chunk.text for chunk in chunks)

    assert "# Abstract" in joined and "## Methods" in joined
    assert "### Limitations" in joined and "## Results" in joined
    assert "12.4%" in joined and "95% CI 8.1–16.7%" in joined
    assert "did not improve" in joined
    assert "HELIOS" in joined and "ResNet-50" in joined
    assert "Figure 2:" in joined
    assert "| low light | 18.2% |" in joined
    assert any("Methods" in (chunk.section_name or "") for chunk in chunks)
    assert any("Limitations" in (chunk.section_name or "") for chunk in chunks)
    serialized = json.loads(chunks_to_json(chunks))
    assert serialized[0]["document_id"] == "md-doc"
    assert serialized[0]["metadata"]["parser"] == "markdown"


def test_chunk_boundaries_and_overlap_are_source_slices(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SCOPECHECK_CHUNK_TOKENS", "12")
    monkeypatch.setenv("SCOPECHECK_CHUNK_OVERLAP", "3")
    source = "\n\n".join(f"Paragraph {index} has several scientific words." for index in range(1, 9))
    path = tmp_path / "many-paragraphs.txt"
    path.write_text(source)
    chunks = parse_document(path, "chunk-doc")

    assert len(chunks) > 1
    for chunk in chunks:
        assert source[chunk.start_offset : chunk.end_offset] == chunk.text
        assert chunk.start_offset is not None and chunk.end_offset is not None
    assert any(set(first.text.split()) & set(second.text.split()) for first, second in zip(chunks, chunks[1:]))


def test_identifiers_are_stable_and_document_scoped() -> None:
    path = FIXTURES / "sample.md"
    first = parse_document(path, "stable-doc")
    second = parse_document(path, "stable-doc")
    other_document = parse_document(path, "other-doc")

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert [chunk.id for chunk in first] != [chunk.id for chunk in other_document]


def test_empty_file_returns_no_chunks(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text(" \n\n")
    assert parse_document(empty, "empty-doc") == []


def test_unsupported_format_and_invalid_utf8_are_clear(tmp_path: Path) -> None:
    unsupported = tmp_path / "data.csv"
    unsupported.write_text("a,b")
    with pytest.raises(ValueError, match="unsupported document format"):
        parse_document(unsupported, "csv-doc")

    invalid = tmp_path / "broken.txt"
    invalid.write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(ValueError, match="expected UTF-8 text"):
        parse_document(invalid, "bad-doc")


def test_missing_file_and_invalid_document_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot read document"):
        parse_document(tmp_path / "missing.txt", "missing-doc")
    with pytest.raises(ValueError, match="document_id"):
        parse_document(FIXTURES / "sample.txt", "  ")


def test_pdf_requires_valid_signature_and_optional_docling(tmp_path: Path) -> None:
    bad_pdf = tmp_path / "broken.pdf"
    bad_pdf.write_text("not a PDF")
    with pytest.raises(ValueError, match="valid PDF signature"):
        parse_document(bad_pdf, "pdf-doc")

    # The development environment may not have optional Docling installed.
    import importlib.util

    if importlib.util.find_spec("docling") is None:
        valid_header = tmp_path / "minimal.pdf"
        valid_header.write_bytes(b"%PDF-1.4\n")
        with pytest.raises(RuntimeError, match="optional Docling"):
            parse_document(valid_header, "pdf-doc")


def test_pdf_uses_docling_export_and_marks_canonical_offsets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    package = types.ModuleType("docling")
    package.__path__ = []  # type: ignore[attr-defined]
    converter_module = types.ModuleType("docling.document_converter")

    class FakeDocument:
        title = "A scientific title"

        def export_to_markdown(self) -> str:
            return "# Findings\n\nThere was no effect (p = 0.4)."

    class FakeConverter:
        def convert(self, _path: str) -> object:
            return types.SimpleNamespace(document=FakeDocument())

    converter_module.DocumentConverter = FakeConverter  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docling", package)
    monkeypatch.setitem(sys.modules, "docling.document_converter", converter_module)
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.7\nmock")

    chunks = parse_document(pdf, "pdf-doc")

    assert len(chunks) == 1
    assert "There was no effect (p = 0.4)." in chunks[0].text
    assert chunks[0].section_name == "Findings"
    assert chunks[0].page_number is None
    assert chunks[0].metadata["parser"] == "docling"
    assert chunks[0].metadata["document_metadata"]["title"] == "A scientific title"
