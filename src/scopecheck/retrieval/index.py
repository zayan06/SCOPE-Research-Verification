"""Local, scope-aware (but direction-neutral) evidence retrieval.

TF-IDF is the default baseline. BM25 and RRF are implemented locally; dense
search is opt-in and requires a caller-provided encoder or the optional
sentence-transformers package. No model or service is loaded by ``build_index``.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from scopecheck.contracts import EvidenceChunk, RetrievalHit, RetrievalMethod

_TOKEN_RE = re.compile(r"(?u)\b[\w]+(?:[.+/%-][\w]+)*\b")
_NUMBER_RE = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?%?(?!\w)")
_CATEGORY_TERMS = {
    "dataset": {"dataset", "cohort", "benchmark", "database", "registry", "biobank"},
    "method": {"method", "model", "algorithm", "regression", "randomized", "randomised", "trial", "assay"},
    "outcome": {"outcome", "endpoint", "mortality", "survival", "accuracy", "risk", "yield", "response"},
}


def normalize_query(query: str) -> str:
    """Normalize query whitespace and case while preserving scientific tokens."""
    return " ".join(query.casefold().split())


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


class DenseEncoder(Protocol):
    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class SentenceTransformerEncoder:
    """Lazy optional adapter; instantiate only when dense retrieval is desired."""

    def __init__(self, model_name: str, *, local_files_only: bool = True) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "Dense retrieval requires the optional 'retrieval' extra "
                "(sentence-transformers)."
            ) from exc
        self._model = SentenceTransformer(
            model_name, model_kwargs={"local_files_only": local_files_only}
        )

    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self._model.encode(list(texts), normalize_embeddings=True)


@dataclass(frozen=True)
class RetrievalSettings:
    """Reproducible strategy and reranking settings for an index."""

    method: RetrievalMethod = RetrievalMethod.TFIDF
    rrf_constant: int = 60
    rerank: bool = False


class LocalEvidenceIndex:
    """In-memory exact-text index with deterministic ranking and filtering."""

    def __init__(
        self,
        chunks: Sequence[EvidenceChunk],
        *,
        method: RetrievalMethod | str = RetrievalMethod.TFIDF,
        dense_encoder: DenseEncoder | None = None,
        rrf_constant: int = 60,
        rerank: bool = False,
    ) -> None:
        self.chunks = tuple(chunks)
        self.settings = RetrievalSettings(RetrievalMethod(method), rrf_constant, rerank)
        if rrf_constant < 1:
            raise ValueError("rrf_constant must be at least 1")
        self.dense_encoder = dense_encoder
        self._vectorizer = TfidfVectorizer(
            lowercase=True, token_pattern=r"(?u)\b\w+\b", ngram_range=(1, 2)
        )
        self._tfidf = None
        if self.chunks:
            try:
                self._tfidf = self._vectorizer.fit_transform([c.text for c in self.chunks])
            except ValueError:  # e.g. a corpus containing only punctuation
                self._tfidf = None
        self._tokenized = [_tokens(c.text) for c in self.chunks]
        self._avgdl = (
            sum(map(len, self._tokenized)) / len(self._tokenized)
            if self._tokenized else 0.0
        )
        self._doc_freq: Counter[str] = Counter(
            term for doc in self._tokenized for term in set(doc)
        )
        self._dense_vectors = None
        if dense_encoder is not None and self.chunks:
            self._dense_vectors = _normalize_rows(dense_encoder.encode([c.text for c in self.chunks]))

    def search(
        self,
        query: str,
        k: int = 5,
        allowed_document_ids: Sequence[str] | None = None,
        *,
        method: RetrievalMethod | str | None = None,
        rerank: bool | None = None,
    ) -> list[RetrievalHit]:
        """Return top-k passages, applying the document allow-list before ranking."""
        if k <= 0 or not self.chunks or not normalize_query(query):
            return []
        selected_method = RetrievalMethod(method) if method is not None else self.settings.method
        use_rerank = self.settings.rerank if rerank is None else rerank
        allowed = None if allowed_document_ids is None else set(allowed_document_ids)
        candidates = [
            i for i, chunk in enumerate(self.chunks)
            if allowed is None or chunk.document_id in allowed
        ]
        if not candidates:
            return []

        if selected_method is RetrievalMethod.TFIDF:
            scores = self._tfidf_scores(query, candidates)
            ranked = self._rank(scores)
        elif selected_method is RetrievalMethod.BM25:
            scores = self._bm25_scores(query, candidates)
            ranked = self._rank(scores)
        elif selected_method is RetrievalMethod.HYBRID:
            scores = self._hybrid_scores(query, candidates)
            ranked = self._rank(scores)
        elif selected_method is RetrievalMethod.DENSE:
            scores = self._dense_score(query, candidates)
            ranked = self._rank(scores)
        else:
            raise ValueError(f"Unsupported retrieval method: {selected_method}")

        if use_rerank:
            ranked = sorted(
                ranked,
                key=lambda i: (
                    -self._rerank_score(query, self.chunks[i].text),
                    -scores.get(i, 0.0),
                    self._stable_key(i),
                ),
            )

        # Exact repeated passages in one document are redundant candidates.
        # The first result in the ranking is retained with its original IDs.
        seen: set[tuple[str, str]] = set()
        hits: list[RetrievalHit] = []
        for i in ranked:
            chunk = self.chunks[i]
            dedupe_key = (chunk.document_id, chunk.text)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            score = scores.get(i, 0.0)
            hits.append(RetrievalHit(
                chunk=chunk, score=max(0.0, float(score)), rank=len(hits) + 1,
                retrieval_method=selected_method,
            ))
            if len(hits) >= k:
                break
        return hits

    def _stable_key(self, i: int) -> tuple[str, str, str, int]:
        c = self.chunks[i]
        return c.document_id, c.id, c.text, i

    def _rank(self, scores: dict[int, float]) -> list[int]:
        return sorted(scores, key=lambda i: (-scores[i], self._stable_key(i)))

    def _tfidf_scores(self, query: str, candidates: Sequence[int]) -> dict[int, float]:
        if self._tfidf is None:
            return {i: 0.0 for i in candidates}
        q = self._vectorizer.transform([normalize_query(query)])
        values = cosine_similarity(q, self._tfidf[candidates]).ravel()
        return {i: float(value) for i, value in zip(candidates, values)}

    def _bm25_scores(self, query: str, candidates: Sequence[int]) -> dict[int, float]:
        terms = _tokens(normalize_query(query))
        n = len(self._tokenized)
        result: dict[int, float] = {}
        k1, b = 1.5, 0.75
        for i in candidates:
            frequencies = Counter(self._tokenized[i])
            length = len(self._tokenized[i])
            total = 0.0
            for term in terms:
                df = self._doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                tf = frequencies[term]
                total += idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * length / (self._avgdl or 1.0))
                )
            result[i] = total
        return result

    def _hybrid_scores(self, query: str, candidates: Sequence[int]) -> dict[int, float]:
        tfidf_rank = self._rank(self._tfidf_scores(query, candidates))
        bm25_rank = self._rank(self._bm25_scores(query, candidates))
        fusion: dict[int, float] = {i: 0.0 for i in candidates}
        for ranking in (tfidf_rank, bm25_rank):
            for rank, i in enumerate(ranking, start=1):
                fusion[i] += 1.0 / (self.settings.rrf_constant + rank)
        return fusion

    def _dense_score(self, query: str, candidates: Sequence[int]) -> dict[int, float]:
        if self.dense_encoder is None or self._dense_vectors is None:
            raise ValueError("Dense search requires a configured dense_encoder")
        query_vector = _normalize_rows(self.dense_encoder.encode([normalize_query(query)]))[0]
        return {i: max(0.0, _dot(query_vector, self._dense_vectors[i])) for i in candidates}

    @staticmethod
    def _rerank_score(query: str, text: str) -> float:
        """Direction-neutral topical score from lexical, scope, and number cues."""
        qtokens, dtokens = set(_tokens(query)), set(_tokens(text))
        if not qtokens:
            return 0.0
        overlap = len(qtokens & dtokens) / len(qtokens)
        category = sum(
            bool(qtokens & terms) and bool(dtokens & terms)
            for terms in _CATEGORY_TERMS.values()
        )
        qnumbers, dnumbers = set(_NUMBER_RE.findall(query)), set(_NUMBER_RE.findall(text))
        numeric = bool(qnumbers & dnumbers)
        # Agreement in direction is deliberately absent: increases/decreases
        # are both valuable evidence for a query about the same outcome.
        return overlap + 0.15 * category + 0.2 * numeric


def _normalize_rows(vectors: Sequence[Sequence[float]]) -> list[list[float]]:
    normalized: list[list[float]] = []
    for vector in vectors:
        row = [float(x) for x in vector]
        norm = math.sqrt(sum(x * x for x in row))
        normalized.append([x / norm for x in row] if norm else row)
    return normalized


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("dense encoder returned vectors with inconsistent dimensions")
    return sum(a * b for a, b in zip(left, right))


def build_index(
    chunks: Sequence[EvidenceChunk],
    *,
    method: RetrievalMethod | str = RetrievalMethod.TFIDF,
    dense_encoder: DenseEncoder | None = None,
    rrf_constant: int = 60,
    rerank: bool = False,
) -> LocalEvidenceIndex:
    """Build an in-memory index; TF-IDF is default and needs no model download."""
    return LocalEvidenceIndex(
        chunks, method=method, dense_encoder=dense_encoder,
        rrf_constant=rrf_constant, rerank=rerank,
    )
