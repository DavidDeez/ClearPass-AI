"""
ClearPass — Main FastAPI Application (Layer 5: Orchestrator)
=============================================================
Portable KYC and AI trust-scoring API. Orchestrates biometric
face matching, financial feature extraction, three parallel ML
models, and a weighted trust-score assembler behind a single
POST /verify endpoint.

All models are trained/loaded at startup. Redis caching avoids
redundant re-computation within a 6-hour window.
"""

import asyncio
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("clearpass.main")

# ---------------------------------------------------------------------------
# Eagerly import service modules so models train at startup
# ---------------------------------------------------------------------------
logger.info("=== ClearPass startup: loading models ===")

from services.face_match import match_faces                     # noqa: E402
from services.feature_extractor import extract_features         # noqa: E402
from services.model_a_behavior import score_behavior            # noqa: E402
from services.model_b_anomaly import detect_anomaly             # noqa: E402
from services.model_c_graph import add_user_to_graph, score_graph  # noqa: E402
from services.score_assembler import assemble_trust_score       # noqa: E402
from services.cache import get_cached_verdict, cache_verdict    # noqa: E402

logger.info("=== All models loaded — ClearPass ready ===")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ClearPass AI",
    description="Portable KYC & AI Trust-Scoring Infrastructure",
    version="1.0.0",
)

# CORS — allow frontend on any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

_executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class Transaction(BaseModel):
    amount: float
    date: str
    status: str
    narration: str
    type: str = Field(..., pattern="^(credit|debit)$")


class VerifyRequest(BaseModel):
    bvn: str
    phone: str
    device_id: str
    address: str
    live_image_b64: str
    official_image_b64: str | None = None
    transactions: list[Transaction]


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception:\n%s", traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the ClearPass frontend UI."""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Liveness / readiness probe."""
    return {"status": "ok", "models": "loaded"}


@app.post("/verify")
async def verify(payload: VerifyRequest):
    """
    Full ClearPass KYC verification pipeline.

    1. Cache check
    2. Biometric face match (blocks on failure)
    3. Financial feature extraction
    4. Parallel ML scoring (Models A, B, C)
    5. Trust score assembly
    6. Cache result
    7. Return verdict
    """
    start = time.perf_counter()
    logger.info("=== /verify request for BVN %s ===", payload.bvn[:6] + "****")

    # ---- Step 1: Cache check ----
    cached = get_cached_verdict(payload.bvn)
    if cached is not None:
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.info("Returning cached verdict in %.2f ms", elapsed)
        return {**cached, "cached": True, "processing_time_ms": elapsed}

    # ---- Step 2: Biometric face match ----
    if payload.official_image_b64:
        try:
            face_result = match_faces(payload.live_image_b64, payload.official_image_b64)
        except ValueError as exc:
            logger.warning("Face match failed: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        if not face_result["pass"]:
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            logger.info("Biometric mismatch — blocking immediately")
            block_result = {
                "trust_score": 0,
                "verdict": "BLOCK",
                "reason": "biometric_mismatch",
                "face_match_score": face_result["score"],
                "cached": False,
                "processing_time_ms": elapsed,
            }
            cache_verdict(payload.bvn, block_result)
            return block_result
        face_match_score = face_result["score"]
    else:
        face_match_score = None

    # ---- Step 3: Feature extraction ----
    transactions_raw = [tx.model_dump() for tx in payload.transactions]
    features = extract_features(transactions_raw)

    # ---- Step 4: Parallel model scoring ----
    loop = asyncio.get_running_loop()

    # Add user to graph first (mutation, must complete before scoring)
    await loop.run_in_executor(
        _executor,
        add_user_to_graph,
        payload.bvn,
        payload.phone,
        payload.device_id,
        payload.address,
    )

    # Run all three models concurrently
    result_a, result_b, result_c = await asyncio.gather(
        loop.run_in_executor(_executor, score_behavior, features),
        loop.run_in_executor(_executor, detect_anomaly, features),
        loop.run_in_executor(_executor, score_graph, payload.bvn),
    )

    # ---- Step 5: Assemble trust score ----
    verdict = assemble_trust_score(result_a, result_b, result_c)

    # ---- Step 6: Build response ----
    elapsed = round((time.perf_counter() - start) * 1000, 2)

    response: dict[str, Any] = {
        **verdict,
        "face_match_score": face_match_score,
        "cached": False,
        "processing_time_ms": elapsed,
    }

    # ---- Step 7: Cache ----
    cache_verdict(payload.bvn, response)

    logger.info(
        "=== /verify complete — score: %d, verdict: %s, time: %.2f ms ===",
        verdict["trust_score"],
        verdict["verdict"],
        elapsed,
    )
    return response


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
