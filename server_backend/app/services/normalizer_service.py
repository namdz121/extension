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
        self.reload_credentials()

    def reload_credentials(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if self.api_key:
            print(f"[Normalizer] Đã nạp GEMINI_API_KEY thành công (Độ dài: {len(self.api_key)})")
            self.client = genai.Client(api_key=self.api_key)
        else:
            print("[Normalizer] CẢNH BÁO: Chưa tìm thấy GEMINI_API_KEY trong settings!")
            self.client = None

        chosen_model = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.candidate_models = [chosen_model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]
        self.candidate_models = list(dict.fromkeys(self.candidate_models))

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
        Bạn là hệ thống AI trích xuất thực thể sản phẩm (Entity Normalization) và tối ưu hóa từ khóa tìm kiếm TMĐT.
        Nhiệm vụ: Lọc sạch toàn bộ từ rác SEO (chính hãng, giá rẻ, freeship, flash sale, quà tặng, hot trend 2026...).
        Bóc tách chính xác model, hãng, thông số cốt lõi và TẠO RA 'search_keywords' (Cụm từ khóa tìm kiếm vàng).

        DỮ LIỆU ĐẦU VÀO:
        - Tiêu đề thô: "{raw_title}"
        - Mức giá bóc tách sơ bộ: {raw_price if raw_price is not None else "Chưa rõ"}

        QUY TẮC ĐỊNH DẠNG:
        - category: "electronics" | "home_appliances" | "beauty" | "fashion" | "books" | "real_estate" | "general"
        - brand: Tên thương hiệu chuẩn (hoặc null nếu không rõ)
        - model: Tên model cụ thể hoặc dòng sản phẩm chính
        - key_specs: Object chứa các thuộc tính thực tế (đối_tượng, loại_sản_phẩm, chất_liệu, màu_sắc, kích_cỡ, dung_lượng...)
          * Với THỜI TRANG / GIÀY DÉP: BẮT BUỘC nhận diện rõ "đối_tượng" (Nữ, Nam, Unisex, Trẻ em) và "loại_sản_phẩm" (Giày thể thao, Sneaker, Guốc, Cao gót, Áo thun, Đầm...).
        - search_keywords: Cụm từ khóa cô đọng (3-6 từ đắt giá nhất) đại diện chính xác cho sản phẩm:
          * Với ĐIỆN TỬ: [Hãng] + [Tên máy/Model] + [Phiên bản/Bộ nhớ] (Ví dụ: "TECNO POVA Curve 2 5G 128GB")
          * Với THỜI TRANG / GIÀY DÉP: [Loại trang phục/giày] + [Đối tượng: nam/nữ/unisex] + [Kiểu dáng/Màu sắc đặc trưng]
            (Ví dụ: "giày thể thao nữ sneaker trắng", "giày chạy bộ nam", "áo thun nam oversize cotton", "váy hoa nhí dáng xòe")
          * Nếu có HÌNH ẢNH đính kèm, hãy quan sát màu sắc, hình in/họa tiết để bổ sung vào search_keywords.
        - normalized_price: Nếu 'Mức giá bóc tách sơ bộ' > 0, BẮT BUỘC giữ nguyên số đó.

        CHỈ TRẢ VỀ JSON DUY NHẤT:
        {{
          "category": "fashion",
          "brand": null,
          "model": "Giày thể thao nữ sneaker trắng",
          "search_keywords": "giày thể thao nữ sneaker trắng",
          "key_specs": {{"đối_tượng": "Nữ", "loại_sản_phẩm": "Giày thể thao", "màu": "Trắng"}},
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
                    normalized_price=final_price,
                    search_keywords=parsed.get("search_keywords")
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