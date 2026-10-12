# Scientific evidence retrieval

## Architecture and interfaces

`build_index(chunks)` constructs an in-memory `LocalEvidenceIndex` from the
canonical `EvidenceChunk` contract. `EvidenceIndex.search(query, k=5,
allowed_document_ids=None)` returns canonical `RetrievalHit` objects containing
the unchanged chunk (passage, IDs, offsets, page, section, and metadata), a
nonnegative score, rank, and `RetrievalMethod`. Query normalization folds case
and whitespace; passage text is never rewritten. The allow-list is applied
before candidate ranking, so an excluded document cannot appear in results.
Exact repeated text within the same document is deduplicated, retaining the
highest-ranked chunk and its original provenance.

The default retrieval strategy is TF-IDF. Pass `method="bm25"` or
`method="hybrid"` to select another local strategy; `method=` may also be
provided per search for comparisons on the same index. `RetrievalSettings`
captures default method, RRF constant, and reranking setting. A method override
does not alter the configured default.

## TF-IDF baseline

Scikit-learn's `TfidfVectorizer` builds corpus inverse-document-frequency
weights with word unigrams and bigrams. Query and passage vectors are ranked by
cosine similarity. Ties use document ID, chunk ID, passage text, and stable
input order. An all-empty vocabulary yields zero scores and deterministic
results rather than an exception. This is the mandatory local baseline.

## BM25

The index contains a small BM25 implementation with conventional `k1=1.5` and
`b=0.75`; document frequency is computed over the whole corpus. It uses no
additional dependency. Term matching is useful for exact biomedical names,
abbreviations, numbers, and dataset identifiers, but does not understand
synonyms or paraphrases.

## Hybrid ranking

Hybrid retrieval runs TF-IDF and BM25 independently and combines their ordered
lists with Reciprocal Rank Fusion: `sum(1 / (rrf_constant + rank))`. The
default constant is 60 and can be configured at index construction. Raw TF-IDF
and BM25 scores are never mixed because they have different scales. Stable
tie-breaking makes repeated searches reproducible.

## Optional dense retrieval

Dense retrieval is opt-in through `build_index(..., method="dense",
dense_encoder=encoder)`. Any object implementing `encode(texts)` can act as an
encoder. `SentenceTransformerEncoder(model_name)` is an optional adapter and
defaults to `local_files_only=True`; it therefore uses a pre-existing local
model and does not download weights. Install the existing `retrieval` extra to
use this adapter. TF-IDF, BM25, and hybrid do not import or initialize a model
and work without model weights or network access.

## Optional reranking

`rerank=True` applies a lightweight, direction-neutral second-stage score using
lexical overlap, dataset/method/outcome vocabulary, and matching numerical
strings. It is intended to prioritize topical candidates for human review, not
to decide claim truth. Polarity terms are not used as a filter or agreement
signal: passages saying “decreases” remain candidates for claims saying
“increases.”

## Why similarity is not support

Retrieval estimates topical relevance. It does not establish that a passage
supports a claim. A retrieved passage can contradict, qualify, or narrowly
scope a claim; high similarity is not a factual judgment. Preserve both
directionally consistent and inconsistent evidence for downstream alignment
and researcher review. Retrieval scores are not calibrated probabilities.

## Executable demo

From the repository root, install the development dependencies and run:

```sh
python -m pip install -e '.[dev]' 'scikit-learn>=1.4,<2'
python -m scopecheck.retrieval.demo
```

The example corpus is synthetic and deliberately includes both increasing and
decreasing outcomes. It prints ranks, scores, method, document/chunk IDs, and
the original passage. It is not a benchmark or a performance claim.

## Evaluation support

To compare strategies, build one index and call `search(..., method=...)` for
`tfidf`, `bm25`, `hybrid`, and (when configured) `dense`. The deterministic
rank and chunk IDs can be passed to downstream Recall@K and MRR calculations.
The retrieval module does not assign relevance labels or manufacture evaluation
results.

## Privacy and future Pinecone adapter

Callers must pass the authorized document IDs as `allowed_document_ids` for
each search. This implementation enforces that allow-list in candidate
selection. Future persisted indexes must bind every vector and metadata record
to a project/tenant namespace and apply server-side tenant and document filters
before returning candidates; UI-only filtering is insufficient. Authorization
must be revalidated at query time and during reindexing.

A Pinecone Serverless adapter can implement the same `search` contract: embed
chunks at ingestion, upsert vectors with `document_id`, `chunk_id`, and source
metadata, query in the caller's project/tenant namespace with a server-side
document-ID filter, then rebuild `EvidenceChunk` and `RetrievalHit` objects
from stored payloads. Keep the current local `build_index` as the offline
adapter. Pinecone credentials, index creation, embedding choice, data residency,
and namespace lifecycle belong in optional deployment configuration and are
not required here.

## Known limitations

- The TF-IDF tokenizer and BM25 tokenization are lexical and language agnostic
  but not domain aware; tokenization of hyphenated notation can vary.
- BM25 parameters and reranking weights are fixed defaults, not tuned on a
  benchmark.
- Exact-text deduplication is limited to identical strings within a document;
  overlapping or near-duplicate chunks remain.
- Dense quality depends on the encoder and local model availability. The
  adapter does not manage model download, versioning, or embeddings cache.
- The in-memory index is intended for local research corpora, not large-scale
  persistence or concurrent multi-tenant serving.
