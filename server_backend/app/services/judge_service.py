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

        self.candidate_models = ["gemini-3.8-flash", "gemini-3.6-flash"]

    def _extract_clean_json(self, text: str):
        """Lọc sạch chuỗi JSON và hỗ trợ cả khi mô hình trả về dict lẫn list"""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        return json.loads(cleaned.strip())

    async def evaluate(self, entity: CanonicalEntity, raw_deals: list) -> Tuple[List[DealCandidate], str]:
        if not self.client or not raw_deals:
            return [], "Không tìm thấy dữ liệu thị trường trực tuyến để đối soát."

        cleaned_deals = []
        for d in raw_deals[:8]:
            cleaned_deals.append({
                "title": d.get("title", ""),
                "url": d.get("url", ""),
                "snippet": d.get("content", "")[:350]
            })

        prompt = f"""
                Bạn là chuyên gia thẩm định giá và so sánh sản phẩm (LLM Judge).

                SẢN PHẨM GỐC:
                - Tên: {entity.brand or ''} {entity.model or ''}
                - Danh mục: {entity.category}
                - Giá hiện tại người dùng đang xem: {entity.normalized_price} VND

                DANH SÁCH KẾT QUẢ TÌM KIẾM WEB THỰC TẾ:
                {json.dumps(cleaned_deals, ensure_ascii=False)}

                NHIỆM VỤ QUAN TRỌNG VỀ GIÁ BÁN (PRICE EXTRACTION):
                1. Tuyệt đối KHÔNG nhầm lẫn giá bán sản phẩm với:
                   - Phí vận chuyển (thường là 15k - 40k).
                   - Giá bán phụ kiện mua kèm hoặc voucher giảm giá (10k, 20k, 50k).
                   - Giá gạch ảo niêm yết (nếu có giá ưu đãi/khuyến mãi thực tế thì lấy giá ưu đãi).
                2. Nếu giá người dùng đang xem là {entity.normalized_price} VND:
                   - Các deal so sánh của đúng sản phẩm này thường sẽ dao động trong khoảng hợp lý quanh mức giá đó (thường trong biên độ chênh lệch từ 30% đến 200%).
                   - Bỏ qua các kết quả có giá quá vô lý (như vài nghìn đồng hoặc lệch hàng chục lần).
                3. Chọn từ 2 đến 4 deals có liên quan nhất:
                   - Trích xuất price dạng số nguyên VND (ví dụ: 139000, 145000).
                   - match_type: "EXACT_MATCH" (nếu đúng mã {entity.model}), "VARIANT_DIFF" (khác phiên bản/màu/led), hoặc "MARKET_COMP".
                   - composite_score: chấm từ 65.0 đến 98.0.
                4. Viết ai_verdict (2-3 câu): So sánh mức giá người dùng đang xem ({entity.normalized_price} VND) với mặt bằng các điểm bán đối thủ.

                CHỈ TRẢ VỀ JSON OBJECT VỚI 2 TRƯỜNG "deals" VÀ "ai_verdict":
                {{
                  "deals": [
                    {{
                      "title": "Tên sản phẩm tại điểm bán",
                      "price": 145000,
                      "url": "https://...",
                      "match_type": "EXACT_MATCH",
                      "composite_score": 90.0
                    }}
                  ],
                  "ai_verdict": "..."
                }}
                """

        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )

                data = self._extract_clean_json(response.text or "{}")

                # Xử lý an toàn: Nếu mô hình trả về list thay vì dict
                raw_deals_list = []
                verdict = "Đã hoàn tất phân tích đối chiếu giá thị trường."

                if isinstance(data, list):
                    raw_deals_list = data
                elif isinstance(data, dict):
                    raw_deals_list = data.get("deals", [])
                    verdict = data.get("ai_verdict", verdict)

                deals_output: List[DealCandidate] = []
                for item in raw_deals_list:
                    if not isinstance(item, dict):
                        continue
                    deals_output.append(
                        DealCandidate(
                            title=item.get("title", entity.model or "Sản phẩm"),
                            price=float(item.get("price", 0) or 0),
                            url=item.get("url", "https://google.com"),
                            match_type=item.get("match_type", "MARKET_COMP"),
                            composite_score=float(item.get("composite_score", 75.0))
                        )
                    )

                print(f"[JudgeService] Thẩm định thành công với {model_name}: Lấy được {len(deals_output)} deals.")
                return deals_output, verdict

            except Exception as err:
                print(f"[JudgeService] Model {model_name} gặp sự cố ({err}). Đang chuyển model dự phòng...")

        # Fallback an toàn nếu tất cả model LLM đều quá tải
        print("[JudgeService] Tất cả model đều tạm thời quá tải, trích xuất dữ liệu thô từ Tavily.")
        fallback_deals: List[DealCandidate] = []
        for d in raw_deals[:3]:
            fallback_deals.append(
                DealCandidate(
                    title=d.get("title", entity.model or "Điểm bán tham khảo"),
                    price=float(entity.normalized_price or 0),
                    url=d.get("url", "https://google.com"),
                    match_type="MARKET_COMP",
                    composite_score=70.0
                )
            )
        return fallback_deals, "Hệ thống AI đang tạm thời chịu tải cao, gửi bạn danh sách các link tìm kiếm tham khảo từ thị trường."

judge_service = JudgeService()