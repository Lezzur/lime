"""
LIME Backend — FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.storage.database import init_db
from backend.audio.compressor import compressor
from backend.api.routes import router
from backend.api.websocket import ws_live_transcript

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("lime.log"),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LIME backend starting...")
    init_db()
    compressor.start()
    logger.info(f"API ready at http://{settings.api_host}:{settings.api_port}")
    yield
    logger.info("LIME backend shutting down...")
    compressor.stop()


app = FastAPI(
    title="LIME",
    description="Cognitive meeting companion — Phase 1: Audio Foundation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws/live/{meeting_id}")
async def websocket_live(websocket: WebSocket, meeting_id: str):
    await ws_live_transcript(websocket, meeting_id)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
