from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.services.public_api import fetch_history_db, fetch_independence_records
from app.services.rag import ingest_documents
import uuid

router = APIRouter()

class IngestRequest(BaseModel):
    keyword: str
    sources: list[str] = ["history_db", "independence"]  # 수집할 소스

@router.post("/fetch")
async def ingest_from_api(req: IngestRequest, background_tasks: BackgroundTasks):
    """공공API에서 데이터를 가져와 ChromaDB에 저장"""
    background_tasks.add_task(_do_ingest, req.keyword, req.sources)
    return {"message": f"'{req.keyword}' 데이터 수집을 시작합니다. 잠시 후 검색 가능합니다."}


async def _do_ingest(keyword: str, sources: list[str]):
    documents = []

    if "history_db" in sources:
        try:
            data = await fetch_history_db(keyword)
            items = data.get("items", data.get("data", []))
            for item in items:
                documents.append({
                    "id": f"hdb_{uuid.uuid4().hex[:8]}",
                    "text": f"{item.get('title', '')}\n{item.get('content', item.get('description', ''))}",
                    "source": "국사편찬위원회 한국사DB",
                    "year": str(item.get("year", item.get("date", ""))),
                    "url": item.get("url", ""),
                    "image_url": item.get("image_url", ""),
                    "category": "사료",
                })
        except Exception as e:
            print(f"한국사DB 수집 실패: {e}")

    if "independence" in sources:
        try:
            data = await fetch_independence_records(keyword)
            items = data.get("items", data.get("response", {}).get("body", {}).get("items", []))
            if isinstance(items, dict):
                items = [items]
            for item in items:
                documents.append({
                    "id": f"ind_{uuid.uuid4().hex[:8]}",
                    "text": f"{item.get('title', '')}\n{item.get('content', item.get('description', ''))}",
                    "source": "독립기념관 독립운동정보시스템",
                    "year": str(item.get("year", "")),
                    "url": item.get("url", ""),
                    "image_url": item.get("imageUrl", ""),
                    "category": "독립운동",
                })
        except Exception as e:
            print(f"독립기념관 수집 실패: {e}")

    if documents:
        count = await ingest_documents(documents)
        print(f"✅ {count}개 문서 ChromaDB 저장 완료")


@router.post("/manual")
async def ingest_manual(documents: list[dict]):
    """직접 JSON으로 문서 업로드 (텍스트 파일 붙여넣기 등)"""
    count = await ingest_documents(documents)
    return {"ingested": count}
