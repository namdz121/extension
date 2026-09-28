from fastapi import APIRouter

router = APIRouter(tags=["System"])

@router.get("/health")
def check_health():
    return {"status": "ok", "service": "Smart Price Assistant Backend"}