"""
extractor_service.py
--------------------
Extractor LLM: Đọc snapshot DOM (URL, Title, Meta, JSON-LD, Clean Text),
áp dụng PROMPT NỀN DỰA TRÊN BẰNG CHỨNG (Evidence-Based Foundation Prompt)
để bóc tách 3 lớp danh tính sản phẩm và sinh bộ 3 truy vấn tìm kiếm nới lỏng cho Tavily.

Nguyên tắc:
1. Thấy tận mắt thì lấy, không thấy thì trả null hoặc NOT_FOUND, tuyệt đối không bịa.
2. Phân biệt rõ: Giá trị đang chọn (selected) vs Danh sách các tùy chọn có thể chọn (available options).
3. Giữ nguyên số tập sách, mã model, dung lượng, màu, size làm định danh phân biệt.
"""

import json
import re
import traceback
from google import genai
from google.genai import types
from app.config.settings import settings
from app.models.understand_dto import (
    UnderstandPageRequestDTO,
    ExtractedProduct,
    ExtractedEvidence,
    SuggestedSelectors,
    SearchQueries,
    EvidenceStatus,
)

FOUNDATION_EXTRACTOR_PROMPT = """
Bạn là hệ thống AI trích xuất thực thể sản phẩm dựa trên bằng chứng (Evidence-Based Entity Extractor) cho extension so sánh giá.

## MỤC TIÊU
Xác định chính xác sản phẩm và biến thể người dùng đang xem dựa trên dữ liệu thực tế từ trang web.
Đồng thời, tạo ra 3 câu truy vấn tìm kiếm nới lỏng theo bậc thang để hệ thống tìm kiếm nơi bán khác trên Tavily mà không bị rỗng kết quả.

## NGUYÊN TẮC BẰNG CHỨNG (BẮT BUỘC TUÂN THỦ)
1. CHỈ TRÍCH XUẤT THÔNG TIN ĐƯỢC HỖ TRỢ BỞI DỮ LIỆU ĐẦU VÀO. Không tự điền tác giả, model, mã sản phẩm, số tập sách, màu sắc hay size nếu trang không có. Nếu thiếu, trả về null.
2. PHÂN BIỆT GIÁ TRỊ ĐANG CHỌN (selected) VỚI DANH SÁCH LỰA CHỌN (available options):
   - Một danh sách size "39, 40, 41, 42" KHÔNG chứng minh người dùng đang chọn size nào nếu không có từ ngữ chỉ định (như "Đã chọn", "Size: 42", class selected, v.v.).
   - Nếu thấy danh sách nhiều option nhưng không rõ đang chọn cái nào -> điền vào available_options, đặt selected_size/selected_volume là null và variant_evidence_status là "AMBIGUOUS" hoặc "NOT_FOUND".
3. GIỮ NGUYÊN ĐỊNH DANH PHÂN BIỆT:
   - Với SÁCH: Bắt buộc tìm tên sách, tác giả và TẬP/QUYỂN (ví dụ "Tập 3", "Vol 10"). Không được bỏ rơi số tập!
   - Với ĐIỆN TỬ/CÔNG NGHỆ: Bắt buộc tìm Model chính xác và Dung lượng/Cấu hình (128GB, 256GB, RAM 16GB).
   - Với GIÀY/THỜI TRANG: Tìm Model/Dòng giày, Màu sắc và Size nếu có bằng chứng.
4. TẠO 3 CÂU TRUY VẤN TÌM KIẾM CHO TAVILY (SearchQueries):
   - strict_query (Tầng 1 - Đặc hiệu cao): Gồm [Tên cốt lõi] + [Số tập hoặc Dung lượng hoặc Mã model] + "giá bán". (Ví dụ: "Conan" "Tập 100" giá bán shopee tiki fahasa).
   - medium_query (Tầng 2 - Nới lỏng biến thể): Gồm [Tên cốt lõi] + [Hãng hoặc Tác giả] + "giá bán" (bỏ size hoặc bỏ số tập nếu tìm tầng 1 rỗng).
   - broad_query (Tầng 3 - Mở rộng tối đa): Tên gọi phổ thông thông dụng nhất của sản phẩm + "mua chính hãng".

## DỮ LIỆU ĐẦU VÀO TỪ TRANG WEB
- URL: {url}
- Tên miền: {domain}
- Tiêu đề trang (Title): {title}
- Meta Tags: {meta}
- JSON-LD Structured Data: {json_ld}
- Nội dung văn bản chính (Clean Text):
---
{clean_text}
---

## CẤU TRÚC JSON ĐẦU RA (NGHIÊM NGẶT)
Chỉ trả về JSON hợp lệ duy nhất, không thêm bất kỳ văn bản giải thích nào ngoài JSON:
{{
  "page_type": "product" | "listing" | "cart" | "unknown",
  "brand": "tên thương hiệu/hãng sản xuất hoặc null",
  "model": "tên model/tác phẩm chính hoặc null",
  "model_code": "mã model/SKU/ISBN/part number hoặc null",
  "category": "books" | "electronics" | "fashion" | "beauty" | "home_appliances" | "general",
  "author": "tác giả (nếu là sách/truyện) hoặc null",
  "variant": "chuỗi mô tả biến thể tổng hợp hoặc null",
  "selected_volume": "số tập/quyển (ví dụ 'Tập 3') nếu có bằng chứng, ngược lại null",
  "selected_size": "size đang chọn nếu có bằng chứng, ngược lại null",
  "selected_color": "màu đang chọn nếu có bằng chứng, ngược lại null",
  "selected_storage": "dung lượng/RAM đang chọn nếu có bằng chứng, ngược lại null",
  "available_options": ["danh sách các size/màu/tập nhìn thấy trên trang"],
  "variant_evidence_status": "CONFIRMED" | "AMBIGUOUS" | "NOT_FOUND",
  "condition": "new" | "used" | "refurbished" | "unknown",
  "price": giá_bán_hiện_tại_dạng_số_hoặc_null,
  "original_price": giá_gốc_trước_khi_giảm_hoặc_null,
  "currency": "VND",
  "seller": "tên gian hàng/người bán hoặc null",
  "evidence": {{
    "title_excerpt": "đoạn trích nguyên văn chứa tên sản phẩm",
    "price_excerpt": "đoạn trích nguyên văn chứa giá bán",
    "seller_excerpt": "đoạn trích nguyên văn chứa tên shop/người bán",
    "variant_excerpt": "đoạn trích nguyên văn chứng minh biến thể đang chọn"
  }},
  "suggested_selectors": {{
    "title": "CSS selector gợi ý cho tiêu đề hoặc null",
    "price": "CSS selector gợi ý cho giá hoặc null",
    "reviews_container": "CSS selector gợi ý cho khối bình luận hoặc null"
  }},
  "search_queries": {{
    "strict_query": "truy vấn tầng 1 có điều kiện biến thể cốt lõi",
    "medium_query": "truy vấn tầng 2 nới lỏng",
    "broad_query": "truy vấn tầng 3 mở rộng"
  }}
}}
"""


class ExtractorService:
    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.client = genai.Client(api_key=api_key) if api_key else None
        chosen_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        self.candidate_models = [chosen_model, "gemini-2.0-flash", "gemini-1.5-flash"]
        self.candidate_models = list(dict.fromkeys(self.candidate_models))

    def _clean_json(self, text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        return json.loads(text.strip())

    async def extract(self, snapshot: UnderstandPageRequestDTO) -> ExtractedProduct:
        if not self.client:
            print("[ExtractorService] Chưa cấu hình GEMINI_API_KEY, trả về fallback.")
            return ExtractedProduct(
                page_type=snapshot.page_type_hint,
                model=snapshot.title[:50] if snapshot.title else "Sản phẩm",
                search_queries=SearchQueries(
                    strict_query=f"{snapshot.title[:40]} giá",
                    medium_query=f"{snapshot.title[:40]} mua ở đâu",
                    broad_query=f"{snapshot.title[:40]}"
                )
            )

        prompt = FOUNDATION_EXTRACTOR_PROMPT.format(
            url=snapshot.url,
            domain=snapshot.domain,
            title=snapshot.title or "",
            meta=json.dumps(snapshot.meta or {}, ensure_ascii=False),
            json_ld=json.dumps((snapshot.json_ld or [])[:3], ensure_ascii=False),
            clean_text=(snapshot.clean_text or "")[:5500],
        )

        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                data = self._clean_json(response.text or "{}")

                # Parse search queries
                sq_data = data.get("search_queries") or {}
                search_queries = SearchQueries(
                    strict_query=sq_data.get("strict_query", ""),
                    medium_query=sq_data.get("medium_query", ""),
                    broad_query=sq_data.get("broad_query", "")
                )

                # Fallback nếu search_queries bị rỗng
                if not search_queries.strict_query:
                    core_name = data.get("model") or snapshot.title or "Sản phẩm"
                    search_queries.strict_query = f"{core_name} giá bán"
                    search_queries.medium_query = f"{core_name} mua ở đâu"
                    search_queries.broad_query = f"{core_name}"

                ev_status_raw = data.get("variant_evidence_status", "NOT_FOUND")
                try:
                    variant_ev_status = EvidenceStatus(ev_status_raw)
                except Exception:
                    variant_ev_status = EvidenceStatus.NOT_FOUND

                return ExtractedProduct(
                    page_type=data.get("page_type", "unknown"),
                    brand=data.get("brand"),
                    model=data.get("model") or snapshot.title[:50],
                    model_code=data.get("model_code"),
                    category=data.get("category", "general"),
                    author=data.get("author"),
                    variant=data.get("variant"),
                    selected_volume=data.get("selected_volume"),
                    selected_size=data.get("selected_size"),
                    selected_color=data.get("selected_color"),
                    selected_storage=data.get("selected_storage"),
                    available_options=data.get("available_options", []),
                    variant_evidence_status=variant_ev_status,
                    condition=data.get("condition", "unknown"),
                    price=data.get("price"),
                    original_price=data.get("original_price"),
                    currency=data.get("currency", "VND"),
                    seller=data.get("seller"),
                    evidence=ExtractedEvidence(**(data.get("evidence") or {})),
                    suggested_selectors=SuggestedSelectors(**(data.get("suggested_selectors") or {})),
                    search_queries=search_queries,
                )

            except Exception as e:
                print(f"[ExtractorService] Model {model_name} gặp lỗi: {e}. Thử tiếp...")
                traceback.print_exc()

        print("[ExtractorService] Tất cả model đều lỗi, dùng fallback cơ bản.")
        return ExtractedProduct(
            page_type=snapshot.page_type_hint,
            model=snapshot.title[:50] if snapshot.title else "Sản phẩm",
            search_queries=SearchQueries(
                strict_query=f"{snapshot.title[:40]} giá",
                medium_query=f"{snapshot.title[:40]} mua ở đâu",
                broad_query=f"{snapshot.title[:40]}"
            )
        )


extractor_service = ExtractorService()
