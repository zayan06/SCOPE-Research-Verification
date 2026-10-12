from __future__ import annotations

import pytest

from scopecheck.contracts import EvidenceChunk, RetrievalMethod
from scopecheck.retrieval import build_index


def chunk(identifier: str, text: str, document: str = "paper-a", **metadata) -> EvidenceChunk:
    return EvidenceChunk(
        id=identifier, document_id=document, text=text,
        page_number=2, start_offset=10, end_offset=10 + len(text),
        metadata=metadata,
    )


@pytest.fixture
def corpus() -> list[EvidenceChunk]:
    return [
        chunk("exact", "In MIMIC-IV, the intervention increased 30-day survival by 12%."),
        chunk("contradiction", "In MIMIC-IV, the intervention decreased 30-day survival by 12%."),
        chunk("method", "A randomized trial evaluated survival using Cox regression."),
        chunk("unrelated", "The authors collected soil samples in three locations.", "paper-b"),
    ]


def test_exact_keyword_scientific_term_and_provenance(corpus):
    hit = build_index(corpus).search("MIMIC-IV intervention increased 30-day survival", k=1)[0]
    assert hit.chunk.id == "exact"
    assert hit.chunk.document_id == "paper-a"
    assert hit.chunk.page_number == 2
    assert hit.chunk.start_offset == 10
    assert hit.chunk.metadata == {}
    assert hit.rank == 1
    assert hit.retrieval_method is RetrievalMethod.TFIDF


def test_relevant_contradictory_direction_is_retained(corpus):
    hits = build_index(corpus).search("MIMIC-IV intervention survival", k=4)
    assert "contradiction" in [hit.chunk.id for hit in hits]


def test_numeric_and_dataset_specific_evidence(corpus):
    index = build_index(corpus, rerank=True)
    hit = index.search("MIMIC-IV survival 12%", k=1)[0]
    assert hit.chunk.id in {"exact", "contradiction"}
    assert "MIMIC-IV" in hit.chunk.text


def test_allow_list_is_enforced_in_retrieval(corpus):
    hits = build_index(corpus).search(
        "soil samples MIMIC-IV", k=10, allowed_document_ids=["paper-a"]
    )
    assert hits
    assert all(hit.chunk.document_id == "paper-a" for hit in hits)


def test_duplicates_are_deduplicated_with_stable_source_identity():
    index = build_index([
        chunk("first", "Shared result on AUC 0.91."),
        chunk("second", "Shared result on AUC 0.91."),
    ])
    hits = index.search("AUC 0.91", k=5)
    assert len(hits) == 1
    assert hits[0].chunk.id == "first"


def test_empty_corpus_and_empty_query():
    index = build_index([])
    assert index.search("claim") == []
    assert index.search(" ") == []
    punctuation_hit = build_index([chunk("p", "... !!!")]).search("anything")
    assert len(punctuation_hit) == 1
    assert punctuation_hit[0].score == 0


def test_k_larger_than_corpus_and_nonpositive_k(corpus):
    hits = build_index(corpus).search("survival", k=100)
    assert len(hits) <= len(corpus)
    assert build_index(corpus).search("survival", k=0) == []


@pytest.mark.parametrize("method", ["tfidf", "bm25", "hybrid"])
def test_multiple_local_strategies_are_reproducible(corpus, method):
    index = build_index(corpus, method=method)
    first = index.search("randomized survival MIMIC-IV", k=4)
    second = index.search(" RANDOMIZED survival MIMIC-IV ", k=4)
    assert [h.chunk.id for h in first] == [h.chunk.id for h in second]
    assert all(h.retrieval_method.value == method for h in first)
    assert [h.rank for h in first] == list(range(1, len(first) + 1))


def test_per_call_strategy_override(corpus):
    hits = build_index(corpus).search("Cox regression", method="bm25")
    assert hits[0].retrieval_method is RetrievalMethod.BM25
    assert hits[0].chunk.id == "method"


def test_dense_retrieval_is_injected_and_optional():
    class TinyEncoder:
        def encode(self, texts):
            return [[1.0, 0.0] if "survival" in text.lower() else [0.0, 1.0] for text in texts]

    index = build_index(
        [chunk("surv", "survival outcome"), chunk("soil", "soil samples")],
        method="dense", dense_encoder=TinyEncoder(),
    )
    assert index.search("survival", k=1)[0].chunk.id == "surv"
    with pytest.raises(ValueError, match="dense_encoder"):
        build_index([chunk("a", "text")]).search("text", method="dense")


def test_reranker_is_direction_neutral():
    index = build_index([
        chunk("decrease", "Drug decreased mortality in the RCT dataset."),
        chunk("unrelated", "We measured soil moisture across fields."),
    ], rerank=True)
    hits = index.search("Drug increased mortality in the RCT dataset", k=1)
    assert hits[0].chunk.id == "decrease"
