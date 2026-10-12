"""FastAPI application for the local SCOPE backend."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from scopecheck import __version__
from scopecheck.contracts import HealthResponse
from api.database.session import initialize_database
from api.routes.analysis import router as analysis_router
from api.routes.documents import router as documents_router
from api.routes.projects import router as projects_router
from api.services.analysis import ScopePipelineAdapter

@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="SCOPE API",
    description="Local-first claim-evidence alignment research workspace.",
    version=__version__,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

origins = [item.strip() for item in os.getenv("SCOPE_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Content-Type", "Authorization"],
)
app.state.pipeline_adapter = ScopePipelineAdapter()


@app.exception_handler(404)
async def not_found_error(_request: Request, exc) -> JSONResponse:
    detail = getattr(exc, "detail", "Not found.")
    if isinstance(detail, dict) and "code" in detail:
        content = detail
    else:
        content = {"code": "not_found", "message": str(detail)}
    return JSONResponse(status_code=404, content=content)


app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(analysis_router)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report process responsiveness; this is not a security check."""
    return HealthResponse(status="ok", version=__version__, mode=os.getenv("SCOPE_MODE", "local_development"))
