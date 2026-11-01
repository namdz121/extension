"""
verifier_service.py
-------------------
Verifier LLM: nhận bằng chứng từ Extractor, kiểm tra xem
bằng chứng đó có thực sự chứng minh kết luận không.

Nguyên tắc tách biệt:
  - Verifier KHÔNG nhận toàn bộ snapshot DOM
  - Verifier CHỈ thấy: đoạn bằng chứng nguyên văn + kết luận của Extractor
  - Verifier trả lời: "đồng ý / không đồng ý / không đủ bằng chứng"

Thêm: string-match đơn giản xem số giá có xuất hiện trong nguồn không
(mất vài ms, kết quả đưa vào Verifier như tín hiệu)
"""

import re
import json
import traceback
from google import genai
from google.genai import types
from app.config.settings import settings
from app.models.understand_dto import ExtractedProduct, VerifierResult

VERIFIER_PROMPT_TEMPLATE = """
Bạn là AI kiểm tra tính xác thực. Bạn KHÔNG phải là người trích xuất.

## Nhiệm vụ
Kiểm tra xem các bằng chứng nguyên văn bên dưới có thực sự chứng minh
kết luận của hệ thống trích xuất hay không.
Trả lời: "yes" (đồng ý), "no" (không đồng ý), hoặc "insufficient" (không đủ bằng chứng).

## Kết luận của Extractor
- Tên sản phẩm: "{model}" ({brand})
- Giá: {price} {currency}
- Người bán: "{seller}"

## Bằng chứng nguyên văn (Extractor cung cấp)
Bằng chứng cho tên:    "{title_excerpt}"
Bằng chứng cho giá:   "{price_excerpt}"
Bằng chứng cho người bán: "{seller_excerpt}"

## Tín hiệu string-match (tự động)
Chuỗi số giá "{price_str}" có xuất hiện trong bằng chứng: {price_in_source}

## Yêu cầu đầu ra (JSON nghiêm ngặt)
{{
  "title_verified": "yes" | "no" | "insufficient",
  "price_verified": "yes" | "no" | "insufficient",
  "verdict": "agree" | "disagree" | "partial",
  "note": "giải thích ngắn gọn (1 câu)"
}}
"""


class VerifierService:
    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.client = genai.Client(api_key=api_key) if api_key else None
        chosen_model = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite") or "gemini-3.1-flash-lite"
        self.model = chosen_model

    def _clean_json(self, text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        return json.loads(text.strip())

    def _price_in_source(self, price: float | None, evidence: str) -> bool:
        """String-match đơn giản: số giá có xuất hiện trong bằng chứng không."""
        if not price or not evidence:
            return False
        # Tạo các biến thể format của số (1234567 → "1.234.567", "1,234,567")
        price_int = int(price)
        candidates = [
            f"{price_int:,}".replace(",", "."),
            f"{price_int:,}".replace(",", ","),
            str(price_int),
        ]
        return any(c in evidence for c in candidates)

    async def verify(self, extracted: ExtractedProduct, raw_source: str) -> VerifierResult:
        """raw_source: đoạn text ngắn từ clean_text để Verifier cross-check."""
        if not self.client:
            return VerifierResult(verdict="partial", note="Verifier chưa cấu hình API key")

        ev = extracted.evidence
        price_in_src = self._price_in_source(
            extracted.price,
            ev.price_excerpt + " " + raw_source[:2000]
        )

        prompt = VERIFIER_PROMPT_TEMPLATE.format(
            model=extracted.model or "?",
            brand=extracted.brand or "?",
            price=extracted.price or "?",
            currency=extracted.currency,
            seller=extracted.seller or "?",
            title_excerpt=ev.title_excerpt[:300],
            price_excerpt=ev.price_excerpt[:300],
            seller_excerpt=ev.seller_excerpt[:300],
            price_str=str(int(extracted.price)) if extracted.price else "?",
            price_in_source=str(price_in_src),
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,   # Verifier cần ổn định tuyệt đối
                ),
            )
            data = self._clean_json(response.text or "{}")

            return VerifierResult(
                title_verified=data.get("title_verified", "insufficient"),
                price_verified=data.get("price_verified", "insufficient"),
                price_in_source=price_in_src,
                verdict=data.get("verdict", "partial"),
                note=data.get("note", ""),
            )

        except Exception as e:
            print(f"[VerifierService] LỖI: {e}")
            traceback.print_exc()
            return VerifierResult(
                price_in_source=price_in_src,
                verdict="partial",
                note=f"Verifier lỗi: {e}",
            )


verifier_service = VerifierService()
