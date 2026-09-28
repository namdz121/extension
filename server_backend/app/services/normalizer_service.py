import json
import base64
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

    async def normalize(self, raw_title: str, image_data: str = None) -> CanonicalEntity:
        if not self.client:
            print("[Normalizer] Client chưa khởi tạo do thiếu key, chạy vào fallback.")
            return CanonicalEntity(
                category="general",
                brand=None,
                model=raw_title[:30] if raw_title else "Unknown",
                key_specs={}
            )

        prompt = f"""
        Bạn là hệ thống AI phân tích thông tin thương mại điện tử và bất động sản.
        Hãy đọc thông tin đầu vào, lọc sạch các từ khóa giật tít, rác SEO, mã giảm giá.
        Trích xuất thông tin thực thể cốt lõi dưới dạng JSON:
        {{
          "category": "electronics" | "fashion" | "real_estate" | "other",
          "brand": "tên hãng hoặc null",
          "model": "tên model cụ thể hoặc dự án BĐS",
          "key_specs": {{"thông số 1": "giá trị", "thông số 2": "giá trị"}},
          "normalized_price": số tiền dạng số (hoặc null)
        }}

        Tiêu đề thô từ web: "{raw_title}"
        """

        contents = [prompt]

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
                print(f"[Normalizer] Lỗi đọc ảnh: {e}")

        try:
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            print(f"[Normalizer] Phản hồi thành công từ Gemini:\n{response.text}")
            parsed = json.loads(response.text)
            return CanonicalEntity(**parsed)

        except Exception as err:
            print(f"[Normalizer] LỖI GỌI GEMINI CHI TIẾT:")
            traceback.print_exc()
            return CanonicalEntity(
                category="general",
                model=raw_title[:30] if raw_title else "Unknown",
                key_specs={}
            )

normalizer_service = NormalizerService()