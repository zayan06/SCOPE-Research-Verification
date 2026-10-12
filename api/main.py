"""Minimal FastAPI app exposing the implemented foundation endpoint.

See docs/API.md for the complete versioned contract. Product routes remain
unimplemented and are not advertised as functional in this baseline.
"""

from fastapi import FastAPI

from scopecheck import __version__
from scopecheck.contracts import HealthResponse

app = FastAPI(
    title="SCOPE API",
    description="Local-first claim-evidence alignment research workspace.",
    version=__version__,
)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report process responsiveness; this is not a security check."""
    return HealthResponse(status="ok", version=__version__, mode="local_development")
