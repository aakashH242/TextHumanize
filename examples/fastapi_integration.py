"""Production-oriented TextHumanize + FastAPI example.

Install:
    pip install texthumanize fastapi uvicorn

Run:
    uvicorn examples.fastapi_integration:app --host 0.0.0.0 --port 8000

Environment:
    TEXTHUMANIZE_MAX_TEXT_CHARS=100000
    TEXTHUMANIZE_MAX_BATCH_ITEMS=16
    TEXTHUMANIZE_TIMEOUT_SECONDS=8
    TEXTHUMANIZE_MAX_BODY_BYTES=1000000
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from texthumanize import __version__, async_detect_ai, async_humanize

MAX_TEXT_CHARS = int(os.getenv("TEXTHUMANIZE_MAX_TEXT_CHARS", "100000"))
MAX_BATCH_ITEMS = int(os.getenv("TEXTHUMANIZE_MAX_BATCH_ITEMS", "16"))
TIMEOUT_SECONDS = float(os.getenv("TEXTHUMANIZE_TIMEOUT_SECONDS", "8"))
MAX_BODY_BYTES = int(os.getenv("TEXTHUMANIZE_MAX_BODY_BYTES", "1000000"))
BATCH_CONCURRENCY = int(os.getenv("TEXTHUMANIZE_BATCH_CONCURRENCY", "4"))

ERROR_SCHEMA_VERSION = "text-humanize.api_error.v1"

app = FastAPI(
    title="TextHumanize Production API",
    version=__version__,
    description=(
        "Production-oriented FastAPI wrapper with request limits, timeouts, "
        "structured errors, request ids, and batch endpoints."
    ),
)


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
    lang: str = Field("auto")
    profile: str = Field("web")
    intensity: int = Field(60, ge=0, le=100)
    seed: Optional[int] = None
    quality_gate: Optional[str] = Field(None, description='Use "strict" to rollback risky rewrites.')
    minimal: bool = False


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
    lang: str = Field("auto")


class BatchHumanizeRequest(BaseModel):
    texts: list[str] = Field(..., min_items=1, max_items=MAX_BATCH_ITEMS)
    lang: str = Field("auto")
    profile: str = Field("web")
    intensity: int = Field(60, ge=0, le=100)
    quality_gate: Optional[str] = None
    minimal: bool = False


class ApiError(Exception):
    """Application-level error with stable code and status."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _error_response(
    request: Request,
    *,
    code: str,
    message: str,
    status_code: int,
    details: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "schema_version": ERROR_SCHEMA_VERSION,
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
                "details": details or {},
            },
        },
    )


def _humanize_payload(result: Any, elapsed_seconds: float) -> dict[str, Any]:
    return {
        "text": result.text,
        "lang": result.lang,
        "profile": result.profile,
        "change_ratio": round(result.change_ratio, 4),
        "quality_score": round(getattr(result, "quality_score", 0.0), 4),
        "similarity": round(getattr(result, "similarity", 0.0), 4),
        "changes_count": len(result.changes),
        "elapsed_ms": round(elapsed_seconds * 1000, 1),
    }


async def _run_with_timeout(coro: Any, *, operation: str) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise ApiError(
            "timeout",
            f"{operation} exceeded {TIMEOUT_SECONDS:.1f}s timeout",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={"timeout_seconds": TIMEOUT_SECONDS},
        ) from exc


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Attach request id, enforce body size, and expose latency headers."""
    request.state.request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    content_length = int(request.headers.get("content-length") or 0)
    if content_length > MAX_BODY_BYTES:
        return _error_response(
            request,
            code="request_body_too_large",
            message="Request body exceeds configured limit",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"max_body_bytes": MAX_BODY_BYTES, "content_length": content_length},
        )

    started = time.perf_counter()
    response: Response = await call_next(request)
    response.headers["x-request-id"] = _request_id(request)
    response.headers["x-process-time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _error_response(
        request,
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        request,
        code="validation_error",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _error_response(
        request,
        code="http_error",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "limits": {
            "max_text_chars": MAX_TEXT_CHARS,
            "max_batch_items": MAX_BATCH_ITEMS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "max_body_bytes": MAX_BODY_BYTES,
        },
    }


@app.post("/v1/humanize")
async def humanize_endpoint(req: HumanizeRequest) -> dict[str, Any]:
    started = time.perf_counter()
    result = await _run_with_timeout(
        async_humanize(
            req.text,
            lang=req.lang,
            profile=req.profile,
            intensity=req.intensity,
            seed=req.seed,
            quality_gate=req.quality_gate,
            minimal=req.minimal,
        ),
        operation="humanize",
    )
    return _humanize_payload(result, time.perf_counter() - started)


@app.post("/v1/humanize/batch")
async def humanize_batch_endpoint(req: BatchHumanizeRequest) -> dict[str, Any]:
    if any(len(text) > MAX_TEXT_CHARS for text in req.texts):
        raise ApiError(
            "text_too_large",
            "One or more texts exceed max_text_chars",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"max_text_chars": MAX_TEXT_CHARS},
        )

    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def process_one(index: int, text: str) -> dict[str, Any]:
        async with semaphore:
            started = time.perf_counter()
            try:
                result = await _run_with_timeout(
                    async_humanize(
                        text,
                        lang=req.lang,
                        profile=req.profile,
                        intensity=req.intensity,
                        seed=index,
                        quality_gate=req.quality_gate,
                        minimal=req.minimal,
                    ),
                    operation=f"humanize[{index}]",
                )
                return {
                    "index": index,
                    "ok": True,
                    "result": _humanize_payload(result, time.perf_counter() - started),
                }
            except ApiError as exc:
                return {
                    "index": index,
                    "ok": False,
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    },
                }

    results = await asyncio.gather(
        *(process_one(index, text) for index, text in enumerate(req.texts))
    )
    return {
        "count": len(results),
        "ok_count": sum(1 for item in results if item["ok"]),
        "results": results,
    }


@app.post("/v1/detect-ai")
async def detect_ai_endpoint(req: DetectRequest) -> dict[str, Any]:
    result = await _run_with_timeout(
        async_detect_ai(req.text, lang=req.lang),
        operation="detect-ai",
    )
    return {
        "score": result["score"],
        "verdict": result["verdict"],
        "confidence": result["confidence"],
    }
