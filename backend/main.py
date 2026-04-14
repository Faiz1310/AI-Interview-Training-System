import logging
import os
from contextlib import asynccontextmanager
from threading import Thread

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from database import init_db
from routes.auth_routes import router as auth_router
from routes.behavior_routes import router as behavior_router
from routes.dashboard_routes import router as dashboard_router
from routes.question_routes import router as question_router
from routes.resume_routes import router as resume_router
from routes.session_routes import router as session_router
from routes.feedback_routes import router as feedback_router


def _warm_load_models_background():
    """Warm-load heavy ML models in background thread after startup completes."""
    # Detect available Gemini models (network call, can be slow)
    try:
        logger.info("Background: Detecting Gemini available models...")
        from services.ai_service import _get_available_gemini_models
        _get_available_gemini_models()
        logger.info("Background: ✅ Gemini models listed successfully.")
    except Exception as e:
        logger.warning(f"Background: Gemini model listing failed (non-fatal): {e}")

    # Warm-load SBERT model to avoid first-call delay
    try:
        logger.info("Background: Warm-loading SBERT model (all-MiniLM-L6-v2)...")
        from ai_modules.correctness import _get_sbert
        _get_sbert()
        logger.info("Background: ✅ SBERT model loaded successfully.")
    except Exception as e:
        logger.warning(f"Background: SBERT warm-load failed (non-fatal): {e}")

    # Load Whisper audio transcription model
    try:
        logger.info("Background: Initializing Whisper audio transcription (base model)...")
        from ai_modules.audio_transcriber import transcriber
        transcriber.initialize()
        logger.info("Background: ✅ Whisper model loaded successfully")
    except Exception as e:
        logger.warning(f"Background: Whisper initialization failed (non-fatal, audio features unavailable): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initialising database...")
    init_db()

    # Initialize AI services and log available models
    try:
        from services.ai_service import initialize_ai_services
        initialize_ai_services()
    except Exception as e:
        logger.warning(f"AI service initialization failed (non-fatal): {e}")

    # Start background model warm-loading (non-blocking)
    logger.info("Starting background model warm-load thread...")
    warm_load_thread = Thread(target=_warm_load_models_background, daemon=True)
    warm_load_thread.start()
    logger.info("✅ Application startup complete")

    yield
    logger.info("Shutting down.")


app = FastAPI(title="AI Interview Prep API", version="2.0.0", lifespan=lifespan)

# ─── CORS ──────────────────────────────────────────────────────────────────────
# Must be added BEFORE routers are included
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,      tags=["auth"])
app.include_router(resume_router,    tags=["resume"])
app.include_router(question_router,  tags=["questions"])
app.include_router(session_router,   tags=["sessions"])
app.include_router(behavior_router,  tags=["behavior"])
app.include_router(dashboard_router, tags=["dashboard"])
app.include_router(feedback_router,  tags=["feedback"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
