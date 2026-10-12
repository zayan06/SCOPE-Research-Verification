"""Executable synthetic retrieval demo: ``python -m scopecheck.retrieval.demo``."""

from scopecheck.contracts import EvidenceChunk
from scopecheck.retrieval import build_index


def main() -> None:
    chunks = [
        EvidenceChunk(
            id="demo-support", document_id="demo-paper-1",
            text="On the MIMIC-IV cohort, the intervention increased survival by 12%.",
        ),
        EvidenceChunk(
            id="demo-contradiction", document_id="demo-paper-2",
            text="On the MIMIC-IV cohort, the intervention decreased survival by 12%.",
        ),
        EvidenceChunk(
            id="demo-unrelated", document_id="demo-paper-3",
            text="Soil samples were collected from three agricultural fields.",
        ),
    ]
    index = build_index(chunks, method="hybrid", rerank=True)
    for hit in index.search("MIMIC-IV intervention increased survival by 12%", k=3):
        print(
            f"rank={hit.rank} score={hit.score:.4f} "
            f"method={hit.retrieval_method.value} "
            f"document={hit.chunk.document_id} chunk={hit.chunk.id}\n"
            f"  {hit.chunk.text}"
        )


if __name__ == "__main__":
    main()
