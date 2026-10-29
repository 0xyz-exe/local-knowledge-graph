from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import CORS_ORIGINS
from backend.app.db.database import init_db
from backend.app.api.v1.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and tables on startup
    init_db()
    yield

app = FastAPI(
    title="Local Knowledge Graph API",
    description="Local-First Knowledge Management & Semantic Search Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok", "service": "Local Knowledge Graph API", "version": "1.0.0"}
