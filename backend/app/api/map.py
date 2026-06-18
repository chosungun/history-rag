from fastapi import APIRouter
from fastapi.responses import Response
import httpx
from app.core.config import settings

router = APIRouter()

_HGIS_BASE = "https://hgis.history.go.kr/openapi/get.do"


@router.get("/tile/{layer}/{z}/{x}/{y}")
async def get_map_tile(layer: str, z: int, x: int, y: int):
    """역사지리정보 WMTS 타일 프록시 — API 키를 백엔드에서 관리"""
    if not settings.hgis_api_key:
        return Response(status_code=204)
    if layer not in ("map1919", "map1919_index", "map1970", "map1970_index"):
        return Response(status_code=400)

    params = {
        "Service": "WMTS",
        "Request": "GetTile",
        "Version": "1.0.0",
        "apiKey": settings.hgis_api_key,
        "Layer": layer,
        "Style": "default",
        "TileMatrixSet": "GoogleMapsCompatible",
        "TileMatrix": str(z),
        "TileRow": str(y),
        "TileCol": str(x),
        "Format": "image/png",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(_HGIS_BASE, params=params)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                return Response(content=r.content, media_type="image/png",
                                headers={"Cache-Control": "public, max-age=86400"})
        except Exception as e:
            print(f"지도 타일 오류 ({layer}/{z}/{x}/{y}): {e}")
    return Response(status_code=204)


@router.get("/capabilities")
async def get_capabilities():
    """GetCapabilities — 지원 TileMatrixSet 확인용"""
    if not settings.hgis_api_key:
        return {"error": "HGIS_API_KEY 미설정"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(_HGIS_BASE, params={
            "Service": "WMTS", "Request": "GetCapabilities",
            "apiKey": settings.hgis_api_key,
        })
    return Response(content=r.content, media_type="application/xml")
