from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag import rag_search

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("")
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력하세요.")
    result = await rag_search(req.query, req.top_k)
    return result

@router.get("/ping")
async def ping():
    return {"ok": True}
