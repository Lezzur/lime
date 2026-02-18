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
from backend.learning.scheduler import scheduler as consolidation_scheduler
from backend.api.routes import router
from backend.api.knowledge_routes import router as knowledge_router
from backend.api.websocket import ws_live_transcript
from backend.api.push_routes import router as push_router
from backend.api.crypto_routes import router as crypto_router
from backend.api.sync_routes import router as sync_router

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
    # Initialize knowledge graph (loads from JSON if exists)
    from backend.knowledge.graph import knowledge_graph  # noqa: F401
    logger.info(f"Knowledge graph: {knowledge_graph.stats()}")
    # Initialize ChromaDB vector store
    from backend.storage.vector_store import vector_store  # noqa: F401
    logger.info(f"Vector store: {vector_store.stats()}")
    compressor.start()
    consolidation_scheduler.start()
    # Initialize sync engine (if enabled)
    if settings.sync_enabled:
        from backend.sync.engine import sync_engine
        sync_engine.initialize()
        await sync_engine.start_auto_sync()
        logger.info("Sync engine initialized (device: %s)", sync_engine.device_id)
    logger.info(f"API ready at http://{settings.api_host}:{settings.api_port}")
    yield
    logger.info("LIME backend shutting down...")
    if settings.sync_enabled:
        from backend.sync.engine import sync_engine
        await sync_engine.stop_auto_sync()
    consolidation_scheduler.stop()
    compressor.stop()


app = FastAPI(
    title="LIME",
    description="Cognitive meeting companion — Phase 2: Intelligence & Memory",
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
app.include_router(knowledge_router)
app.include_router(push_router)
app.include_router(crypto_router)
app.include_router(sync_router)


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
