from fastapi import APIRouter
from app.models.request_dto import AnalyzeRequestDTO
from app.models.response_dto import AnalyzeResponseDTO
from app.services.normalizer_service import normalizer_service
from app.services.search_service import search_service
from app.services.judge_service import judge_service
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponseDTO)
async def analyze_product(dto: AnalyzeRequestDTO):
    print("\n" + "=" * 50)
    print("[Controller] Nhận yêu cầu phân tích mới:")
    print(f"- URL: {dto.page_url}")
    print(f"- Tiêu đề: {dto.raw_title}")
    print(f"- Giá gốc: {dto.raw_price}")
    print("=" * 50)

    cache_key = f"{dto.page_url}_{dto.raw_title}_{dto.raw_price}"
    cached = cache_service.get(cache_key)
    if cached:
        print("[Controller] Trả kết quả từ In-Memory Cache.")
        return cached

    # 1. Normalizer (Gemini AI Vision & Text) - Truyền đủ raw_price
    canonical = await normalizer_service.normalize(
        raw_title=dto.raw_title or "",
        raw_price=dto.raw_price,
        image_data=dto.image_data
    )

    # Đảm bảo normalized_price không bị rỗng nếu DOM đã quét được giá
    if dto.raw_price and not canonical.normalized_price:
        canonical.normalized_price = dto.raw_price

    # 2. Search Orchestrator (Tavily Search API)
    raw_deals = await search_service.search_market(canonical)

    # 3. LLM as a Judge (Gemini AI Evaluation với cơ chế dự phòng model)
    deals, verdict = await judge_service.evaluate(canonical, raw_deals)

    response = AnalyzeResponseDTO(
        canonical_entity=canonical,
        deals=deals,
        ai_verdict=verdict
    )

    # Lưu cache (15 phút)
    cache_service.set(cache_key, response)
    return response