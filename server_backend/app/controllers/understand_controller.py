"""
understand_controller.py
-------------------------
Endpoint mới: POST /api/v1/understand-page
Pipeline đầy đủ:
  1. Kiểm tra selector cache → nếu có, bỏ qua Extractor LLM
  2. Extractor LLM: đọc snapshot, trích xuất + bằng chứng + gợi ý selector
  3. Lưu selector vào cache cho domain đó
  4. Verifier LLM: kiểm tra bằng chứng độc lập
  5. Tính confidence_score từ mức đồng thuận
  6. MultiSearch: tìm song song trên nhiều sàn
  7. Trả về response đầy đủ
"""

import asyncio
from fastapi import APIRouter
from app.models.understand_dto import (
    UnderstandPageRequestDTO,
    UnderstandPageResponseDTO,
    ExtractedProduct,
    VerifierResult,
    PriceRange,
    MatchStatus,
)
from app.services.extractor_service import extractor_service
from app.services.verifier_service import verifier_service
from app.services.multi_search_service import multi_search_service
from app.services.selector_cache_service import selector_cache
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api/v1", tags=["Understand Page"])


def _calc_confidence(product: ExtractedProduct, verifier: VerifierResult) -> float:
    """
    Tính điểm tin cậy từ sự đồng thuận, KHÔNG phải từ self-report của LLM.
    Các yếu tố:
      - Extractor & Verifier có đồng ý không?   (+40 nếu agree)
      - Giá có khớp string trong nguồn không?   (+30 nếu yes)
      - Có bằng chứng cho tên sản phẩm?         (+15 nếu yes)
      - Có bằng chứng cho giá?                  (+15 nếu yes)
    """
    score = 0.0

    if verifier.verdict == "agree":
        score += 40
    elif verifier.verdict == "partial":
        score += 20

    if verifier.price_in_source:
        score += 30

    ev = product.evidence
    if ev.title_excerpt and len(ev.title_excerpt) > 5:
        score += 15
    if ev.price_excerpt and len(ev.price_excerpt) > 3:
        score += 15

    return min(score, 100.0)


@router.post("/understand-page", response_model=UnderstandPageResponseDTO)
async def understand_page(snapshot: UnderstandPageRequestDTO):
    # ---- Cache tổng thể theo URL ----
    cache_key = f"understand:{snapshot.url}"
    cached = cache_service.get(cache_key)
    if cached:
        print(f"[UnderstandCtrl] Cache hit: {snapshot.url[:60]}")
        return cached

    print(f"[UnderstandCtrl] Phân tích: {snapshot.url[:60]}")

    # ---- Bước 1: Extractor LLM ----
    # (kiểm tra selector cache để tăng tốc ở phiên bản sau)
    extracted: ExtractedProduct = await extractor_service.extract(snapshot)

    # Lưu selector LLM sinh ra vào cache cho domain này
    if extracted.suggested_selectors and snapshot.domain:
        selector_cache.save(snapshot.domain, extracted.suggested_selectors)

    # ---- Bước 2: Verifier LLM (song song với MultiSearch) ----
    verify_task = asyncio.create_task(
        verifier_service.verify(extracted, snapshot.clean_text)
    )
    search_task = asyncio.create_task(
        multi_search_service.search_all_platforms(extracted, current_url=snapshot.url)
    )

    verifier_result: VerifierResult
    deals, price_range, ai_verdict = await search_task
    verifier_result = await verify_task

    # ---- Bước 3: Tính confidence score từ đồng thuận ----
    confidence = _calc_confidence(extracted, verifier_result)
    print(f"[UnderstandCtrl] Confidence score: {confidence:.0f}/100 | Verdict: {verifier_result.verdict}")

    exact_deals = [d for d in deals if d.match_status == MatchStatus.EXACT_VARIANT]
    other_variant_deals = [d for d in deals if d.match_status == MatchStatus.SAME_PRODUCT_OTHER_VARIANT]
    similar_deals = [d for d in deals if d.match_status == MatchStatus.SIMILAR_ALTERNATIVE]

    response = UnderstandPageResponseDTO(
        product=extracted,
        verifier=verifier_result,
        confidence_score=confidence,
        price_range=price_range if price_range else PriceRange(),
        platform_deals=deals,
        exact_deals=exact_deals,
        other_variant_deals=other_variant_deals,
        similar_deals=similar_deals,
        ai_verdict=ai_verdict,
        suggested_selectors=extracted.suggested_selectors,
    )

    # Cache kết quả 15 phút
    cache_service.set(cache_key, response, ttl=900)
    return response
