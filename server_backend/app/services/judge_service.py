import json
import re
import traceback
from typing import List, Tuple
from google import genai
from google.genai import types
from app.config.settings import settings
from app.models.entity import CanonicalEntity, DealCandidate

class JudgeService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _extract_clean_json(self, text: str) -> dict:
        """Lọc bỏ markdown code blocks nếu có trước khi parse JSON"""
        text = text.strip()
        # Loại bỏ ```json và ``` nếu Gemini trả kèm
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return json.loads(text.strip())

    async def evaluate(self, entity: CanonicalEntity, raw_deals: list) -> Tuple[List[DealCandidate], str]:
        if not self.client or not raw_deals:
            return [], "Không tìm thấy dữ liệu thị trường trực tuyến để đối soát."

        # Rút gọn danh sách web từ Tavily đưa vào context
        cleaned_deals = []
        for d in raw_deals[:8]:
            cleaned_deals.append({
                "title": d.get("title", ""),
                "url": d.get("url", ""),
                "snippet": d.get("content", "")[:350]
            })

        prompt = f"""
        Bạn là chuyên gia thẩm định giá và so sánh hàng hóa thị trường (LLM as a Judge).

        SẢN PHẨM GỐC:
        - Tên/Model: {entity.brand or ''} {entity.model or ''}
        - Danh mục: {entity.category}
        - Thuộc tính chi tiết: {json.dumps(entity.key_specs, ensure_ascii=False)}
        - Giá người dùng đang xem: {entity.normalized_price} VND

        DANH SÁCH CÁC KẾT QUẢ TÌM KIẾM WEB THỰC TẾ:
        {json.dumps(cleaned_deals, ensure_ascii=False)}

        NHIỆM VỤ:
        1. Phân tích các kết quả web trên và bóc tách ra danh sách các điểm bán đối thủ.
        2. Chọn từ 2 đến 4 deals thực tế và liên quan nhất.
        3. Với mỗi deal:
           - Trích xuất giá bán dạng số nguyên (VND). Nếu bài viết là điểm bán sản phẩm này nhưng chưa nêu giá rõ trong đoạn trích, hãy ước lượng mức giá tham khảo hợp lý theo thị trường (tuyệt đối không để giá 0 hoặc null).
           - match_type: "EXACT_MATCH" (đúng model/mã SP), "VARIANT_DIFF" (khác màu/size/bản), hoặc "MARKET_COMP" (sản phẩm tương đương).
           - composite_score: chấm điểm từ 65.0 đến 98.0.
        4. Viết 1 đoạn nhận xét ai_verdict (2-3 câu): Đánh giá xem mức giá {entity.normalized_price} VND của người dùng đang xem là đắt, rẻ hay hợp lý so với các bên khác.

        CHỈ TRẢ VỀ JSON HỢP LỆ VỚI CẤU TRÚC SAU:
        {{
          "deals": [
            {{
              "title": "Tên sản phẩm tại điểm bán",
              "price": 2700000,
              "url": "link url từ kết quả tìm kiếm",
              "match_type": "EXACT_MATCH",
              "composite_score": 90.0
            }}
          ],
          "ai_verdict": "Nhận định ngắn gọn về mức giá..."
        }}
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

            raw_text = response.text or "{}"
            data = self._extract_clean_json(raw_text)

            deals_output: List[DealCandidate] = []
            for item in data.get("deals", []):
                price_val = float(item.get("price", 0) or 0)
                deals_output.append(
                    DealCandidate(
                        title=item.get("title", entity.model or "Sản phẩm"),
                        price=price_val,
                        url=item.get("url", "[https://google.com](https://google.com)"),
                        match_type=item.get("match_type", "MARKET_COMP"),
                        composite_score=float(item.get("composite_score", 75.0))
                    )
                )

            verdict = data.get("ai_verdict", "Đã hoàn tất phân tích đối chiếu giá thị trường.")
            print(f"[JudgeService] Thẩm định thành công: Lấy được {len(deals_output)} deals.")
            return deals_output, verdict

        except Exception as err:
            print(f"[JudgeService] LỖI THẨM ĐỊNH CHI TIẾT: {err}")
            traceback.print_exc()
            return [], "Hệ thống gặp lỗi khi đối soát giá thị trường."

judge_service = JudgeService()