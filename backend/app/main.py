from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import search, ingest, photos, chat
from app.core.config import settings
from app.core.chroma import init_chroma

app = FastAPI(
    title="한국 근현대사 고증 AI",
    description="일제강점기 사료 기반 RAG 검색 시스템",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_chroma()

app.include_router(chat.router, prefix="/api/chat", tags=["채팅"])
app.include_router(search.router, prefix="/api/search", tags=["검색"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["데이터 수집"])
app.include_router(photos.router, prefix="/api/photos", tags=["사진"])

@app.get("/health")
async def health():
    return {"status": "ok"}
