import base64
import json
import re
import traceback
from google import genai
from google.genai import types
from app.config.settings import settings
from app.models.entity import CanonicalEntity

class NormalizerService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if self.api_key:
            print(f"[Normalizer] Đã nạp GEMINI_API_KEY thành công (Độ dài: {len(self.api_key)})")
            self.client = genai.Client(api_key=self.api_key)
        else:
            print("[Normalizer] CẢNH BÁO: Chưa tìm thấy GEMINI_API_KEY trong settings!")
            self.client = None

        # Danh sách model chuẩn hiện hành
        self.candidate_models = ["gemini-3.8-flash", "gemini-3.6-flash"]

    def _clean_json_text(self, text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        data = json.loads(cleaned.strip())
        return data if isinstance(data, dict) else {}

    async def normalize(
        self,
        raw_title: str,
        raw_price: float = None,
        image_data: str = None
    ) -> CanonicalEntity:
        if not self.client:
            return CanonicalEntity(
                category="general",
                brand=None,
                model=(raw_title or "Unknown")[:40],
                key_specs={},
                normalized_price=raw_price
            )

        prompt = f"""
        Bạn là hệ thống AI trích xuất thực thể sản phẩm (Entity Normalization).
        Nhiệm vụ: Lọc sạch từ rác SEO (chính hãng, giá rẻ, freeship, flash sale, quà tặng kèm...).
        Bóc tách chính xác model, hãng, và các thông số kỹ thuật cốt lõi (key_specs).

        DỮ LIỆU ĐẦU VÀO:
        - Tiêu đề thô: "{raw_title}"
        - Mức giá bóc tách sơ bộ: {raw_price if raw_price is not None else "Chưa rõ"}

        QUY TẮC ĐỊNH DẠNG:
        - category: "electronics" | "fashion" | "real_estate" | "general"
        - brand: Tên thương hiệu chuẩn (hoặc null nếu không rõ)
        - model: Tên model cụ thể hoặc dự án BĐS
        - key_specs: Object chứa các thuộc tính thực tế (loại, kết nối, màu, dung lượng...)
        - normalized_price: Nếu 'Mức giá bóc tách sơ bộ' > 0, BẮT BUỘC giữ nguyên số đó.

        CHỈ TRẢ VỀ JSON DUY NHẤT:
        {{
          "category": "electronics",
          "brand": "SIDOTECH",
          "model": "LDK V4 Pro",
          "key_specs": {{"loại": "Bàn phím giả cơ", "kết_nối": "Có dây"}},
          "normalized_price": {raw_price if raw_price is not None else "null"}
        }}
        """

        contents: list = [prompt]

        if image_data and "base64," in image_data:
            try:
                header, encoded = image_data.split("base64,", 1)
                mime_type = "image/jpeg"
                if "image/png" in header:
                    mime_type = "image/png"
                elif "image/webp" in header:
                    mime_type = "image/webp"

                contents.append(
                    types.Part.from_bytes(
                        data=base64.b64decode(encoded),
                        mime_type=mime_type
                    )
                )
            except Exception as e:
                print(f"[Normalizer] Bỏ qua ảnh lỗi: {e}")

        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )

                parsed = self._clean_json_text(response.text or "{}")
                print(f"[Normalizer] Chuẩn hóa thành công qua model {model_name}")

                final_price = parsed.get("normalized_price")
                if final_price is None and raw_price is not None:
                    final_price = raw_price

                return CanonicalEntity(
                    category=parsed.get("category", "general"),
                    brand=parsed.get("brand"),
                    model=parsed.get("model", raw_title[:40]),
                    key_specs=parsed.get("key_specs", {}),
                    normalized_price=final_price
                )
            except Exception as err:
                print(f"[Normalizer] Model {model_name} gặp lỗi: {err}. Thử model tiếp theo...")

        print("[Normalizer] Toàn bộ model đều nghẽn, kích hoạt fallback cơ bản.")
        return CanonicalEntity(
            category="electronics" if any(k in (raw_title or "").lower() for k in ["bàn phím", "chuột", "laptop", "tai nghe"]) else "general",
            brand="SIDOTECH" if "sidotech" in (raw_title or "").lower() else None,
            model=(raw_title or "Sản phẩm")[:40],
            key_specs={},
            normalized_price=raw_price
        )

normalizer_service = NormalizerService()