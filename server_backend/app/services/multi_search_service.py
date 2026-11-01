"""
multi_search_service.py
-----------------------
Tìm kiếm ứng viên trên thị trường bằng Tavily theo CHIẾN LƯỢC 3 TẦNG NỚI LỎNG (Tiered Fallback)
và Thẩm định đối soát đa trạng thái (5-State Match Evaluation).

Các trạng thái khớp:
- EXACT_VARIANT: Đúng sản phẩm & đúng biến thể (Tập sách, Size, Dung lượng).
- SAME_OTHER_VARIANT: Cùng sản phẩm nhưng khác biến thể (khác size, khác tập, khác dung lượng).
- SIMILAR_ALTERNATIVE: Sản phẩm tương tự thay thế.
- INSUFFICIENT_EVIDENCE: Không đủ dữ liệu để kết luận.
- MISMATCH: Sai hoàn toàn (bị lọc bỏ).
"""

import asyncio
import json
import re
import traceback
from typing import List, Tuple
from urllib.parse import urlparse
from tavily import TavilyClient
from google import genai
from google.genai import types
from app.config.settings import settings
from app.models.understand_dto import (
    ExtractedProduct, PlatformDeal, PriceRange, MatchStatus
)
from app.services.search_service import is_same_product_or_page

# Danh sách nền tảng bán lẻ uy tín theo từng nhóm ngành tại Việt Nam
PLATFORM_HINTS = {
    "books": ["tiki.vn", "fahasa.com", "shopee.vn", "vinabook.com", "nhasachtrithuc.vn"],
    "electronics": ["cellphones.com.vn", "thegioididong.com", "fptshop.com.vn", "shopee.vn", "shop.tiktok.com"],
    "fashion": ["supersports.com.vn", "myshoes.vn", "bitis.com.vn", "sneakerdaily.vn", "mwc.com.vn", "shopee.vn", "shop.tiktok.com", "lazada.vn"],
    "beauty": ["hasaki.vn", "watsons.vn", "guardian.com.vn", "shopee.vn", "shop.tiktok.com"],
    "general": ["shopee.vn", "tiki.vn", "lazada.vn", "shop.tiktok.com"]
}

JUDGE_PROMPT_TEMPLATE = """
Bạn là AI Thẩm Định Đối Soát Giá Thị Trường (Multi-State Match Judge).

## SẢN PHẨM GỐC CẦN ĐỐI SOÁT:
- Tên sản phẩm: {product_name}
- Thương hiệu / Tác giả: {brand_or_author}
- Mã model / ISBN: {model_code}
- Ngành hàng: {category}
- Biến thể người dùng đang xem:
  * Số tập / quyển: {volume}
  * Kích cỡ (Size): {size}
  * Màu sắc: {color}
  * Dung lượng / Cấu hình: {storage}
- Giá người dùng đang xem: {user_price} {currency}

## DANH SÁCH KẾT QUẢ TÌM KIẾM TỪ CÁC SÀN / WEBSITE:
{search_results}

## NGUYÊN TẮC PHÂN LOẠI 5 TRẠNG THÁI (BẮT BUỘC TUÂN THỦ):
1. EXACT_VARIANT (Đúng sản phẩm & đúng biến thể):
   - Cùng tên/model, cùng tác giả.
   - NẾU LÀ SÁCH: Bắt buộc đúng số tập (Gốc là '{volume}' thì kết quả phải đúng '{volume}').
   - NẾU LÀ ĐIỆN TỬ: Bắt buộc đúng dung lượng (ví dụ 128GB vs 128GB).
   - NẾU LÀ GIÀY/DÉP: Bắt buộc cùng mẫu và đúng size nếu kết quả có ghi size.
   -> Đưa vào danh sách đối soát giá chính xác!

2. SAME_OTHER_VARIANT (Cùng sản phẩm nhưng khác biến thể):
   - Cùng mẫu giày nhưng khác size (ví dụ gốc 42, kết quả là 41).
   - Cùng sách nhưng khác tập (gốc là '{volume}', kết quả là tập khác hoặc trọn bộ).
   - Cùng điện thoại nhưng khác dung lượng (gốc 256GB, kết quả là 128GB hoặc 512GB).
   -> BẮT BUỘC ghi chú rõ sự khác biệt vào 'matched_variant_note' (Ví dụ: "Bán Tập 1 thay vì Tập 3", "Size 41 thay vì 42").

3. SIMILAR_ALTERNATIVE (Sản phẩm tương tự thay thế):
   - Khác model hoặc khác hãng nhưng cùng loại sản phẩm có công năng tương đương (ví dụ cùng là giày thể thao nữ).

4. INSUFFICIENT_EVIDENCE (Chưa đủ bằng chứng để xác minh):
   - Tiêu đề hoặc nội dung kết quả không ghi rõ tập sách, không ghi rõ dung lượng hoặc size để khẳng định.

5. MISMATCH (Sai hoàn toàn):
   - SAI ĐỐI TƯỢNG / GIỚI TÍNH: Sản phẩm gốc là NỮ (ví dụ giày nữ) nhưng kết quả là NAM (ví dụ giày nam) và ngược lại -> BẮT BUỘC ĐÁNH DẤU MISMATCH!
   - SAI CHỦNG LOẠI: Đang tìm giày thể thao / sneaker mà kết quả là guốc, dép, cao gót, sandal, quần áo -> BẮT BUỘC ĐÁNH DẤU MISMATCH!
   - TRANG CHỦ / DANH MỤC: Các trang chủ website, trang bộ sưu tập không phải trang chi tiết sản phẩm -> BẮT BUỘC ĐÁNH DẤU MISMATCH!
   - Bán phụ kiện (ốp lưng, dây sạc, bookmark thay vì sản phẩm chính).
   - Sách của tác giả hoàn toàn khác, sản phẩm không liên quan.
   -> LOẠI BỎ hoàn toàn, KHÔNG đưa vào JSON trả về!

## TRÍCH XUẤT GIÁ BÁN:
- Bóc tách giá bán dạng số nguyên VND (ví dụ: 85000, 15400000).
- Tuyệt đối không nhầm với phí ship (15k-40k) hay voucher giảm giá.
- Trích dẫn nguyên văn đoạn text chứa giá vào 'evidence_excerpt'.

## ĐẦU RA (JSON NGHIÊM NGẶT):
{{
  "deals": [
    {{
      "platform": "tên sàn hoặc website (ví dụ: Fahasa, Shopee, Tiki, CellphoneS)",
      "title": "tiêu đề bài bán hàng",
      "price": 85000,
      "url": "URL",
      "seller": "tên shop hoặc null",
      "match_status": "EXACT_VARIANT" | "SAME_OTHER_VARIANT" | "SIMILAR_ALTERNATIVE" | "INSUFFICIENT_EVIDENCE",
      "matched_variant_note": "ghi chú khác biệt nếu là SAME_OTHER_VARIANT hoặc null",
      "label": "cheapest" | "most_trusted" | "best_overall" | "normal",
      "composite_score": 90.0,
      "evidence_excerpt": "đoạn trích nguyên văn chứa giá"
    }}
  ],
  "price_summary": {{
    "min": giá_thấp_nhất,
    "max": giá_cao_nhất,
    "avg": giá_trung_bình,
    "currency": "VND"
  }},
  "ai_verdict": "nhận định khách quan 2-3 câu về tình trạng so sánh giá đối soát thị trường"
}}
"""


class MultiSearchService:
    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        tavily_key = settings.TAVILY_API_KEY.strip() if settings.TAVILY_API_KEY else ""
        gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        self.gemini = genai.Client(api_key=gemini_key) if gemini_key else None
        chosen_model = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite") or "gemini-3.1-flash-lite"
        self.candidate_models = [chosen_model, "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]
        self.candidate_models = list(dict.fromkeys(self.candidate_models))

    def _is_valid_product_url(self, url: str, title: str = "") -> bool:
        """Kiểm tra URL có phải là trang sản phẩm chi tiết hay chỉ là trang chủ / trang danh mục."""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            if not path or path.lower() in ["vi", "en", "vn", "home", "index", "index.html"]:
                return False

            path_segments = [p.lower() for p in path.split("/") if p]
            if len(path_segments) == 1 and path_segments[0] in [
                "collections", "collection", "category", "categories", 
                "danh-muc", "san-pham", "products", "search", "tim-kiem", "shop"
            ]:
                return False

            if len(path_segments) == 2 and path_segments[0] in ["collections", "category", "danh-muc"]:
                return False

            if title:
                title_lower = title.lower().strip()
                generic_title_patterns = [
                    r"^sản phẩm thời trang\b",
                    r"^trang chủ\b",
                    r"\btại footgear\b",
                    r"^tất cả sản phẩm\b",
                    r"^bộ sưu tập\b",
                    r"^chuyên mục\b",
                    r"^danh mục\b",
                    r"^bảng giá\b",
                    r"^hệ thống cửa hàng\b"
                ]
                for pat in generic_title_patterns:
                    if re.search(pat, title_lower):
                        return False

            return True
        except Exception:
            return True

    def _extract_domain_name(self, url: str) -> str:
        try:
            netloc = urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    def _tavily_search_sync(self, query: str, max_results: int = 6) -> list:
        if not self.tavily or not query.strip():
            return []
        try:
            res = self.tavily.search(
                query=query.strip(),
                search_depth="basic",
                max_results=max_results,
                include_answer=False
            )
            return res.get("results", [])
        except Exception as e:
            print(f"[MultiSearch] Lỗi query '{query[:40]}': {e}")
            return []

    async def _execute_tiered_search(self, product: ExtractedProduct, current_url: str = "") -> list:
        """Thực thi chiến lược tìm kiếm 3 tầng nới lỏng để chống rỗng"""
        loop = asyncio.get_event_loop()
        sq = product.search_queries
        all_results = []
        seen_urls = set()

        def add_valid_results(items: list):
            for r in items:
                u = r.get("url", "")
                t = r.get("title", "")
                if u and u not in seen_urls and self._is_valid_product_url(u, t):
                    if current_url and is_same_product_or_page(u, current_url):
                        continue
                    seen_urls.add(u)
                    all_results.append(r)

        # TẦNG 1: Truy vấn đặc hiệu cao (Chặt chẽ)
        q1 = sq.strict_query or f"{product.brand or ''} {product.model or ''} giá bán".strip()
        print(f"[MultiSearch] Tầng 1 (Chặt): '{q1}'")
        res1 = await loop.run_in_executor(None, self._tavily_search_sync, q1, 6)
        add_valid_results(res1)

        # TẦNG 2: Nếu chưa đủ 4 kết quả, kích hoạt Tầng 2 (Nới lỏng biến thể)
        if len(all_results) < 4 and sq.medium_query and sq.medium_query != q1:
            print(f"[MultiSearch] Tầng 1 ít kết quả ({len(all_results)}), kích hoạt Tầng 2 (Nới lỏng): '{sq.medium_query}'")
            res2 = await loop.run_in_executor(None, self._tavily_search_sync, sq.medium_query, 6)
            add_valid_results(res2)

        # TẦNG 3: Nếu vẫn chưa đủ 3 kết quả, kích hoạt Tầng 3 (Mở rộng tối đa)
        if len(all_results) < 3 and sq.broad_query and sq.broad_query not in (q1, sq.medium_query):
            print(f"[MultiSearch] Kích hoạt Tầng 3 (Mở rộng): '{sq.broad_query}'")
            res3 = await loop.run_in_executor(None, self._tavily_search_sync, sq.broad_query, 6)
            add_valid_results(res3)

        print(f"[MultiSearch] Tổng kết quả thu thập qua các tầng: {len(all_results)}")
        return all_results

    async def search_all_platforms(
        self, product: ExtractedProduct, current_url: str = ""
    ) -> tuple[List[PlatformDeal], PriceRange, str]:
        """
        Tìm kiếm song song và đối soát 5 trạng thái.
        Trả về: (deals, price_range, ai_verdict)
        """
        if not self.tavily:
            return self._mock_deals(product)

        # 1. Chạy tìm kiếm nới lỏng có kiểm soát
        raw_items = await self._execute_tiered_search(product, current_url=current_url)
        if not raw_items:
            return [], PriceRange(), "Không tìm thấy dữ liệu đối chiếu trên thị trường cho sản phẩm này."

        # 2. Định dạng danh sách kết quả gửi vào LLM Judge
        search_text = ""
        for idx, item in enumerate(raw_items[:12], 1):
            domain = self._extract_domain_name(item.get("url", ""))
            search_text += (
                f"\n--- [Ứng viên {idx} | Nguồn: {domain}] ---\n"
                f"Tiêu đề: {item.get('title', '')}\n"
                f"URL: {item.get('url', '')}\n"
                f"Nội dung trích đoạn: {item.get('content', '')[:500]}\n"
            )

        if not self.gemini:
            return self._mock_deals(product)

        # 3. Thẩm định qua LLM Judge
        try:
            prompt = JUDGE_PROMPT_TEMPLATE.format(
                product_name=product.model or "Chưa rõ",
                brand_or_author=product.brand or product.author or "Chưa rõ",
                model_code=product.model_code or "Chưa rõ",
                category=product.category or "general",
                volume=product.selected_volume or "Không có số tập",
                size=product.selected_size or "Không rõ size",
                color=product.selected_color or "Không rõ màu",
                storage=product.selected_storage or "Không rõ",
                user_price=product.price or "Chưa rõ",
                currency=product.currency or "VND",
                search_results=search_text[:9000]
            )

            data = {}
            for model_name in self.candidate_models:
                try:
                    response = self.gemini.models.generate_content(
                        model=model_name,
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )
                    raw = response.text or "{}"
                    raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
                    raw = re.sub(r"\n?```$", "", raw)
                    data = json.loads(raw)
                    if data:
                        break
                except Exception as model_err:
                    print(f"[MultiSearch] Model {model_name} gặp lỗi: {model_err}, thử model tiếp theo...")

            deals_output: List[PlatformDeal] = []
            for d in data.get("deals", []):
                if not isinstance(d, dict):
                    continue
                url_val = d.get("url", "")
                title_val = d.get("title", "")
                if not self._is_valid_product_url(url_val, title_val):
                    continue
                if current_url and is_same_product_or_page(url_val, current_url):
                    continue

                match_status_raw = d.get("match_status", "INSUFFICIENT_EVIDENCE")
                try:
                    m_status = MatchStatus(match_status_raw)
                except Exception:
                    m_status = MatchStatus.INSUFFICIENT_EVIDENCE

                # Bỏ qua các deal MISMATCH
                if m_status == MatchStatus.MISMATCH:
                    continue

                deals_output.append(
                    PlatformDeal(
                        platform=d.get("platform", "Điểm bán trực tuyến"),
                        title=d.get("title", ""),
                        price=float(d.get("price") or 0),
                        url=d.get("url", ""),
                        seller=d.get("seller"),
                        match_status=m_status,
                        matched_variant_note=d.get("matched_variant_note"),
                        label=d.get("label", "normal"),
                        composite_score=float(d.get("composite_score") or 0.0),
                        evidence_excerpt=d.get("evidence_excerpt", "")
                    )
                )

            ps = data.get("price_summary", {})
            price_range = PriceRange(
                min=ps.get("min"),
                max=ps.get("max"),
                avg=ps.get("avg"),
                currency=ps.get("currency", "VND"),
            )
            verdict = data.get("ai_verdict", "Đã hoàn tất đối soát giá thị trường.")
            print(f"[MultiSearch] Đã đối soát xong: {len(deals_output)} deals hợp lệ sau thẩm định.")
            return deals_output, price_range, verdict

        except Exception as e:
            print(f"[MultiSearch] Lỗi đối soát Judge: {e}")
            traceback.print_exc()
            return [], PriceRange(), "Gặp sự cố trong quá trình đối soát kết quả tìm kiếm."

    def _mock_deals(self, product: ExtractedProduct):
        """Fallback khi chưa có API key."""
        name = f"{product.brand or ''} {product.model or ''}".strip() or "Sản phẩm mẫu"
        mock = [
            PlatformDeal(
                platform="Shopee",
                title=f"{name} - Shopee Mall",
                price=product.price or 0,
                url="https://shopee.vn",
                match_status=MatchStatus.INSUFFICIENT_EVIDENCE,
                label="normal",
                composite_score=0,
                evidence_excerpt="Dữ liệu mẫu — chưa cấu hình TAVILY_API_KEY",
            )
        ]
        return mock, PriceRange(), "Chưa cấu hình API key để tìm giá thị trường."


multi_search_service = MultiSearchService()
