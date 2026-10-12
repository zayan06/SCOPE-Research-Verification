# Retrieval workstream handoff

## Branch and implementation commit

- Branch: `feat/retrieval`
- Implementation commit: `399c6a1c09e81697249ebfb0c8e7151789098e57`
- Handoff record is committed immediately after the implementation commit.

## Files changed

- `src/scopecheck/retrieval/index.py`
- `src/scopecheck/retrieval/__init__.py`
- `src/scopecheck/retrieval/demo.py`
- `tests/test_retrieval.py`
- `docs/methodology/retrieval.md`
- `docs/handoffs/retrieval.md` (this file)

No shared contracts, ingestion, claim extraction, alignment, evaluation,
backend, or frontend files were changed.

## Implemented algorithms and behavior

- Scikit-learn TF-IDF cosine similarity is the default local baseline, using
  word unigrams and bigrams.
- Local BM25 implementation uses `k1=1.5`, `b=0.75`.
- Hybrid retrieval uses Reciprocal Rank Fusion over TF-IDF and BM25 ranked
  lists, with a configurable default constant of 60. Raw scores are not mixed.
- Dense retrieval is optional through an injected encoder, with a lazy
  Sentence Transformers adapter that defaults to local-only model loading.
- Optional reranking uses lexical overlap, dataset/method/outcome terminology,
  and number matches. It does not use factual direction as a relevance filter.
- Query filtering by `allowed_document_ids` is performed before retrieval.
  Identical passages in the same document are deduplicated while retaining the
  best-ranked chunk and its source identity.
- Results preserve the original `EvidenceChunk`, including source text,
  document/chunk IDs, offsets, page/section and metadata, plus score, rank, and
  the canonical `RetrievalMethod`.

## Public interfaces

```python
build_index(
    chunks: Sequence[EvidenceChunk],
    *, method="tfidf", dense_encoder=None, rrf_constant=60, rerank=False,
) -> LocalEvidenceIndex

LocalEvidenceIndex.search(
    query: str,
    k: int = 5,
    allowed_document_ids: Sequence[str] | None = None,
    *, method: RetrievalMethod | str | None = None,
    rerank: bool | None = None,
) -> list[RetrievalHit]
```

The first three `search` parameters preserve the shared `EvidenceIndex.search`
contract. Optional keyword settings allow reproducible strategy comparisons.
The index defaults to TF-IDF; BM25 and hybrid can be selected when building or
per call. Dense search requires a configured `DenseEncoder`.

## Dependencies

- Uses the repository's existing `scikit-learn>=1.4,<2` optional retrieval
  dependency for the mandatory TF-IDF implementation.
- BM25, RRF, and reranking use the Python standard library.
- Dense retrieval uses the existing optional `sentence-transformers` dependency
  only when the adapter is instantiated. No credentials or remote service are
  required; local-only loading is the default.
- No dependency or shared configuration files were changed.

## Test results

Executed with the bundled Python 3.12 runtime:

```text
21 passed, 1 warning in 2.51s
```

The one warning is the existing Starlette/httpx TestClient deprecation noted
in the foundation handoff. The 13 retrieval tests cover exact keywords,
scientific terms, contradictory evidence, numerical and dataset terms,
document allow-lists, duplicate chunks, empty corpus/query, oversized and
nonpositive `k`, deterministic TF-IDF/BM25/hybrid results, strategy override,
dense encoder injection, and direction-neutral reranking. The full repository
test suite was run; no performance claims were calculated.

The executable demo was run with a synthetic corpus:

```text
rank=1 score=0.0328 method=hybrid document=demo-paper-1 chunk=demo-support
  On the MIMIC-IV cohort, the intervention increased survival by 12%.
rank=2 score=0.0323 method=hybrid document=demo-paper-2 chunk=demo-contradiction
  On the MIMIC-IV cohort, the intervention decreased survival by 12%.
rank=3 score=0.0317 method=hybrid document=demo-paper-3 chunk=demo-unrelated
  Soil samples were collected from three agricultural fields.
```

These are synthetic demonstration values, not evaluation results.

## Integration instructions

1. Integrate this branch while preserving `src/scopecheck/contracts.py` as the
   canonical model boundary.
2. Install the local baseline with `python -m pip install -e '.[dev]'`
   and `python -m pip install 'scikit-learn>=1.4,<2'`. Dense adapter users can
   install the optional retrieval extra and place model weights locally.
3. Call `build_index(chunks)` and pass authorized document IDs to every
   `search` call. Strategy comparisons can use `method="tfidf"`, `"bm25"`,
   `"hybrid"`, or a configured `"dense"`.
4. Treat all returned passages as candidates for downstream alignment and
   researcher review. Retrieval similarity does not label evidence as support
   or contradiction.
5. Future remote adapters must enforce project/tenant namespaces and
   document-ID filters server-side before returning hits. The methodology
   document describes a Pinecone Serverless adapter design; it requires no
   Pinecone credentials for this implementation.

## Known limitations

- Lexical tokenization does not resolve paraphrases, synonymy, negation, or
  scientific notation consistently.
- BM25 defaults and reranking feature weights have not been tuned against a
  labeled corpus. Scores are relevance signals, not calibrated probabilities.
- Deduplication catches exact repeated text within one document only.
- Dense search quality and repeatability depend on encoder/model choice and
  local model version. It is not benchmarked here.
- The in-memory index is not a persistent or multi-tenant serving layer.
- The implementation returns both directionally aligned and contradictory
  passages when they rank as relevant; downstream components must assess their
  relationship to the claim.
