"""Q AI backend (FastAPI).

Start with:  python -m uvicorn app.main:app --reload --reload-dir app
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import SessionLocal, init_db
from app.routers import admin, chat, kb, review, settings as settings_router, trust
from app.services.knowledge_base import get_kb, sync_to_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("qai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("Loading knowledge base and building the vector store...")
    kb_obj = get_kb()  # loads once per process (a restart reloads the markdown files)
    with SessionLocal() as db:
        sync_to_db(db, kb_obj)
    log.info("Knowledge base ready: %d documents, %d conflict pair(s)", len(kb_obj.docs), len(kb_obj.conflicts))
    yield


app = FastAPI(title="Q AI by Quadrant (prototype)", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(kb.router)
app.include_router(review.router)
app.include_router(settings_router.router)
app.include_router(trust.router)


@app.get("/api/health")
def health():
    return {"ok": True, "note": "Prototype for OCBC Ignite. Synthetic data only. Not an OCBC product."}
