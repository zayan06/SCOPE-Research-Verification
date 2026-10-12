"""Pipeline integration point; orchestration will be implemented after adapters."""

from scopecheck.contracts import AnalyzeRequest, AnalyzeResponse


def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Orchestrate claim extraction, retrieval, and comparison for a draft."""
    raise NotImplementedError("analysis pipeline is not installed")
