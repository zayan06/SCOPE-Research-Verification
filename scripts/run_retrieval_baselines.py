#!/usr/bin/env python3
"""Run deterministic TF-IDF and BM25 retrieval on supplied JSONL judgments.

Input documents: {"doc_id": str, "text": str}
Input queries: {"query_id": str, "text": str, "relevant_doc_ids": [str, ...]}
This is a lightweight experiment baseline, not the production retrieval index.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scopecheck.evaluation.metrics import retrieval_metrics

TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?", re.I)


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def tfidf_rank(documents: list[dict], query: str) -> list[tuple[str, float]]:
    doc_tokens = [tokens(doc["text"]) for doc in documents]
    n = len(documents)
    df = Counter(token for toks in doc_tokens for token in set(toks))
    qtf = Counter(tokens(query))
    qvec = {t: (1 + math.log(c)) * (math.log((n + 1) / (df[t] + 1)) + 1) for t, c in qtf.items()}
    qnorm = math.sqrt(sum(v * v for v in qvec.values()))
    output = []
    for doc, toks in zip(documents, doc_tokens):
        tf = Counter(toks)
        vec = {t: (1 + math.log(c)) * (math.log((n + 1) / (df[t] + 1)) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        score = sum(v * vec.get(t, 0) for t, v in qvec.items()) / (qnorm * norm) if qnorm and norm else 0.0
        output.append((doc["doc_id"], score))
    return sorted(output, key=lambda x: (-x[1], x[0]))


def bm25_rank(documents: list[dict], query: str, k1: float = 1.5, b: float = 0.75) -> list[tuple[str, float]]:
    doc_tokens = [tokens(doc["text"]) for doc in documents]
    n = len(documents)
    avgdl = sum(map(len, doc_tokens)) / n
    df = Counter(token for toks in doc_tokens for token in set(toks))
    qterms = set(tokens(query))
    output = []
    for doc, toks in zip(documents, doc_tokens):
        tf = Counter(toks); score = 0.0; dl = len(toks)
        for term in qterms:
            freq = tf[term]
            if freq:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * dl / avgdl))
        output.append((doc["doc_id"], score))
    return sorted(output, key=lambda x: (-x[1], x[0]))


def read_jsonl(path: Path) -> tuple[bytes, list[dict]]:
    raw = path.read_bytes()
    return raw, [json.loads(line) for line in raw.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    try:
        if args.k < 1: raise ValueError("--k must be positive")
        raw_docs, docs = read_jsonl(args.documents); raw_queries, queries = read_jsonl(args.queries)
        if not docs or not queries: raise ValueError("documents and queries must be non-empty")
        doc_ids = [d.get("doc_id") for d in docs]
        if any(not d or not isinstance(d.get("text"), str) or not d["text"].strip() for d in docs):
            raise ValueError("each document requires non-empty doc_id and text")
        if any(not tokens(d["text"]) for d in docs): raise ValueError("every document must contain at least one indexable token")
        if len(doc_ids) != len(set(doc_ids)): raise ValueError("duplicate document IDs")
        qids = [q.get("query_id") for q in queries]
        if len(qids) != len(set(qids)): raise ValueError("duplicate query IDs")
        for q in queries:
            if not q.get("query_id") or not isinstance(q.get("text"), str) or not q["text"].strip():
                raise ValueError("each query requires non-empty query_id and text")
            if not q.get("relevant_doc_ids"): raise ValueError(f"query {q.get('query_id')} has no relevant_doc_ids")
            missing = set(q["relevant_doc_ids"]) - set(doc_ids)
            if missing: raise ValueError(f"query {q['query_id']} references unknown docs: {sorted(missing)}")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        result = {}; pred_path = args.output_dir / "predictions.csv"
        with pred_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle); writer.writerow(["query_id", "method", "ranked_doc_ids"])
            for method, scorer in (("tfidf", tfidf_rank), ("bm25", bm25_rank)):
                rankings = {}
                for q in queries:
                    ranked = scorer(docs, q["text"])
                    rankings[q["query_id"]] = [doc_id for doc_id, _ in ranked[:args.k]]
                    writer.writerow([q["query_id"], method, " ".join(rankings[q["query_id"]])])
                relevant = {q["query_id"]: q["relevant_doc_ids"] for q in queries}
                result[method] = retrieval_metrics(relevant, rankings)
        try: commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path.cwd(), text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError): commit = None
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        metadata = {"experiment_id": "experiment-1-tfidf-vs-bm25", "dataset_version": args.dataset_version,
                    "document_count": len(docs), "query_count": len(queries), "k": args.k,
                    "sha256": {"documents": hashlib.sha256(raw_docs).hexdigest(),
                               "queries": hashlib.sha256(raw_queries).hexdigest()},
                    "algorithm_versions": {"tfidf": "scopecheck-eval-tfidf-v1", "bm25": "scopecheck-eval-bm25-k1.5-b0.75-v1"},
                    "random_seed": args.seed, "git_commit": commit,
                    "execution_timestamp_utc": datetime.now(timezone.utc).isoformat()}
        (args.output_dir / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"retrieval experiment error: {exc}", file=sys.stderr); return 2
    print(f"Retrieved for {len(queries)} queries with TF-IDF and BM25; wrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
