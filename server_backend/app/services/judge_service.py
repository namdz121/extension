import json
import re
import traceback
from typing import List, Tuple
from urllib.parse import urlparse
from google import genai
from google.genai import types
from app.config.settings import settings
from app.models.entity import CanonicalEntity, DealCandidate
from app.services.search_service import is_same_product_or_page

def extract_clean_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

def is_valid_product_url(url: str, title: str = "") -> bool:
    """Kiểm tra xem URL có phải là trang sản phẩm cụ thể hay chỉ là trang chủ / trang danh mục chung chung."""
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


class JudgeService:
    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

        chosen_model = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.candidate_models = [chosen_model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.0-flash"]
        self.candidate_models = list(dict.fromkeys(self.candidate_models))

    def _extract_clean_json(self, text: str):
        """Lọc sạch chuỗi JSON và hỗ trợ cả khi mô hình trả về dict lẫn list"""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        return json.loads(cleaned.strip())

    async def evaluate(self, entity: CanonicalEntity, raw_deals: list, current_url: str = "") -> Tuple[List[DealCandidate], str]:
        if not self.client or not raw_deals:
            return [], "Không tìm thấy dữ liệu thị trường trực tuyến để đối soát."

        # Chuẩn bị danh sách tối đa 12 kết quả là trang sản phẩm hợp lệ
        cleaned_deals = []
        for d in raw_deals:
            if len(cleaned_deals) >= 12:
                break
            u = d.get("url", "")
            t = d.get("title", "")
            if not is_valid_product_url(u, t):
                continue
            if current_url and is_same_product_or_page(u, current_url):
                print(f"[JudgeService] Bỏ qua vì trùng với link đang xem: {u[:70]}")
                continue
            cleaned_deals.append({
                "title": t,
                "url": u,
                "snippet": d.get("content", "")[:700]
            })

        if not cleaned_deals:
            return [], "Các kết quả tìm kiếm không chứa trang chi tiết sản phẩm phù hợp để đối soát."

        user_price = entity.normalized_price or 0
        curr_lower = (current_url or "").lower()
        is_from_shopee = "shopee.vn" in curr_lower
        is_from_tiktok = "tiktok.com" in curr_lower

        prompt = f"""
Bạn là chuyên gia thẩm định giá và so sánh sản phẩm (LLM Judge).

SẢN PHẨM GỐC:
- Tên sản phẩm: {entity.brand or ''} {entity.model or ''}
- Ngành hàng: {entity.category}
- Đặc điểm chi tiết: {json.dumps(entity.key_specs, ensure_ascii=False) if entity.key_specs else 'Không có'}
- Từ khóa định danh: {entity.search_keywords or entity.model or ''}
- Mức giá người dùng đang xem: {user_price} VND
- Nền tảng người dùng đang duyệt: {'Shopee' if is_from_shopee else 'TikTok Shop' if is_from_tiktok else 'Nền tảng khác'}
- URL người dùng đang xem: {current_url}

DANH SÁCH CÁC KẾT QUẢ TÌM KIẾM WEB THỰC TẾ:
{json.dumps(cleaned_deals, ensure_ascii=False, indent=2)}

NHIỆM VỤ QUAN TRỌNG VỀ ĐỐI SOÁT & CHỌN DEAL:
1. TIÊU CHÍ CHẤT LƯỢNG & ĐỘ PHÙ HỢP LÀ TIÊN QUYẾT (TỐI ĐA 5 DEALS KHÁC WEBSITE):
   - Chọn tối đa 5 deals sản phẩm từ các WEBSITE / TÊN MIỀN HOÀN TOÀN KHÁC NHAU.
   - TUYỆT ĐỐI KHÔNG ÉP BUỘC ĐỦ 5 DEALS NẾU THIẾU KẾT QUẢ PHÙ HỢP! Nếu chỉ có 1-2 deals thực sự phù hợp, CHỈ TRẢ VỀ 1-2 deals. Nếu không có deal nào đạt chuẩn, trả về danh sách rỗng [].
   - CHẤT LƯỢNG QUAN TRỌNG HƠN SỐ LƯỢNG: Thà trả về ít deals nhưng đúng sản phẩm, tuyệt đối không chọn sản phẩm rác chỉ để đủ số lượng!

2. CÁC QUY TẮC LOẠI TRỪ BẮT BUỘC (LOẠI BỎ NGAY LẬP TỨC):
   - CHÍNH SẢN PHẨM ĐANG XEM: TUYỆT ĐỐI LOẠI BỎ bất kỳ link nào trỏ về chính sản phẩm mà người dùng đang xem (URL: {current_url}). Nhiệm vụ là tìm các điểm bán KHÁC trên thị trường để so sánh đối soát, không bao giờ lấy lại chính sản phẩm này để so sánh với chính nó!
   - SAI ĐỐI TƯỢNG / GIỚI TÍNH: Nếu sản phẩm gốc dành cho NỮ (giày nữ, thời trang nữ), TUYỆT ĐỐI LOẠI BỎ các sản phẩm ghi rõ là dành cho NAM (ví dụ "Giày Luyện Tập Nam", "Thời trang nam") và ngược lại! Chỉ chấp nhận UNISEX nếu kiểu dáng thực sự tương thích.
   - SAI CHỦNG LOẠI / CÔNG NĂNG: Nếu sản phẩm gốc là GIÀY THỂ THAO / SNEAKER, TUYỆT ĐỐI LOẠI BỎ guốc, dép, dép lê, sandal, giày cao gót, bốt (boots), túi xách, quần áo!
   - SAI PHÂN KHÚC QUÁ XA: Nếu người dùng đang xem giày thời trang phổ thông (~300k - 500k), TUYỆT ĐỐI KHÔNG ghép các mẫu giày thể thao chuyên nghiệp / auth cao cấp 2-4 triệu nếu không cùng model.
   - TRANG CHỦ / TRANG DANH MỤC: TUYỆT ĐỐI LOẠI BỎ các link chỉ là trang chủ cửa hàng (ví dụ "Sản phẩm thời trang Canifa", "Sneakers tại Footgear H") hoặc trang bộ sưu tập không có sản phẩm cụ thể.

3. QUY TẮC SO KHỚP VÀ PHÂN LOẠI MATCH_TYPE:
   - Với SÁCH / TRUYỆN TRANH: BẮT BUỘC ĐÚNG TÊN SÁCH, TÁC GIẢ VÀ ĐÚNG SỐ TẬP/QUYỂN.
   - Với ĐIỆN TỬ / CÔNG NGHỆ: Bắt buộc đúng Model và dung lượng/cấu hình.
   - Với GIÀY DÉP / THỜI TRANG: Đúng mẫu và chủng loại.
   - match_type:
     * "EXACT_MATCH": Cùng đúng model/tên sản phẩm, cùng thương hiệu, cùng đối tượng.
     * "VARIANT_DIFF": Cùng đúng mẫu sản phẩm nhưng khác size, khác màu, khác dung lượng hoặc khác tập.
     * "MARKET_COMP": Sản phẩm THỰC SỰ TƯƠNG ĐƯƠNG VỀ CÔNG NĂNG & ĐỐI TƯỢNG (Ví dụ: Cùng là giày thể thao nữ / sneaker nữ kiểu dáng tương tự trong tầm giá hợp lý). TUYỆT ĐỐI KHÔNG gán MARKET_COMP cho sản phẩm sai danh mục hay sai giới tính!
   - composite_score: Chấm điểm từ 70.0 đến 98.0 dựa trên độ tin cậy của sàn và mức độ tương đồng.

4. QUY TẮC ĐỐI TRỌNG SHOPEE & TIKTOK SHOP:
   - {'Người dùng đang xem ở Shopee: BẮT BUỘC ƯU TIÊN ĐỐI SOÁT VỚI TIKTOK SHOP (shop.tiktok.com) xếp vị trí đầu tiên (nếu có deal hợp lệ), sau đó đến các điểm bán khác.' if is_from_shopee else 'Người dùng đang xem ở TikTok Shop: BẮT BUỘC ƯU TIÊN ĐỐI SOÁT VỚI SHOPEE (shopee.vn) xếp vị trí đầu tiên (nếu có deal hợp lệ), sau đó đến các điểm bán khác.' if is_from_tiktok else 'Người dùng đang xem ở web khác: Cả Shopee (shopee.vn) và TikTok Shop (shop.tiktok.com) có độ ưu tiên cao nhất trong danh sách đối soát.'}

5. BÓC TÁCH GIÁ BÁN SẢN PHẨM:
   - Trích xuất giá dạng số nguyên VND (ví dụ: 320000).
   - Tuyệt đối không nhầm lẫn với phí ship (15k-40k) hay voucher giảm giá.

6. VIẾT AI VERDICT:
   - Viết 2-3 câu nhận xét chân thực, khách quan:
     * So sánh khách quan mức giá người dùng đang xem ({user_price} VND) với các điểm bán đối soát.
     * Nếu sản phẩm trên Shopee là hàng thời trang riêng biệt không có đúng mã model trên sàn khác: Giải thích rõ ràng cho người dùng biết trên thị trường các sàn khác có mẫu tương đương hay không và đưa ra lời khuyên mua sắm.

CHỈ TRẢ VỀ JSON OBJECT VỚI 2 TRƯỜNG "deals" VÀ "ai_verdict":
{{
  "deals": [
    {{
      "title": "Tên sản phẩm tại điểm bán",
      "price": 320000,
      "url": "https://...",
      "match_type": "EXACT_MATCH" | "VARIANT_DIFF" | "MARKET_COMP",
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

                raw_deals_list = []
                verdict = "Đã hoàn tất phân tích đối chiếu giá thị trường từ các điểm bán uy tín."

                if isinstance(data, list):
                    raw_deals_list = data
                elif isinstance(data, dict):
                    raw_deals_list = data.get("deals", [])
                    verdict = data.get("ai_verdict", verdict)

                deals_output: List[DealCandidate] = []
                domains_seen = set()

                for item in raw_deals_list:
                    if not isinstance(item, dict):
                        continue
                    url = item.get("url", "https://google.com")
                    title = item.get("title", entity.model or "Sản phẩm")
                    
                    # Bỏ qua nếu là URL không hợp lệ hoặc trùng với sản phẩm đang xem
                    if not is_valid_product_url(url, title):
                        continue
                    if current_url and is_same_product_or_page(url, current_url):
                        continue

                    domain = extract_clean_domain(url)
                    
                    # Đảm bảo mỗi website chỉ xuất hiện đúng 1 lần
                    if domain and domain in domains_seen:
                        continue
                    if domain:
                        domains_seen.add(domain)

                    price_val = float(item.get("price", 0) or 0)
                    if price_val <= 0 and user_price > 0:
                        price_val = float(user_price)

                    deals_output.append(
                        DealCandidate(
                            title=title,
                            price=price_val,
                            url=url,
                            match_type=item.get("match_type", "MARKET_COMP"),
                            composite_score=float(item.get("composite_score", 75.0))
                        )
                    )

                print(f"[JudgeService] Thẩm định thành công với {model_name}: Lọc được {len(deals_output)} deals chuẩn từ {len(domains_seen)} websites.")
                return deals_output[:5], verdict

            except Exception as err:
                print(f"[JudgeService] Model {model_name} gặp sự cố ({err}). Đang chuyển model dự phòng...")

        # Fallback an toàn nếu tất cả model LLM đều quá tải (chỉ lấy các URL sản phẩm hợp lệ, không nhồi nhét bừa)
        print("[JudgeService] Tất cả model đều tạm thời quá tải, trích xuất dữ liệu thô chọn lọc.")
        fallback_deals: List[DealCandidate] = []
        fb_domains_seen = set()

        for d in raw_deals:
            if len(fallback_deals) >= 5:
                break
            u = d.get("url", "https://google.com")
            t = d.get("title", "")
            if not is_valid_product_url(u, t):
                continue
            if current_url and is_same_product_or_page(u, current_url):
                continue

            dm = extract_clean_domain(u)
            if dm and dm in fb_domains_seen:
                continue
            if dm:
                fb_domains_seen.add(dm)

            fallback_deals.append(
                DealCandidate(
                    title=t or entity.model or "Điểm bán tham khảo",
                    price=float(user_price) if user_price > 0 else 0,
                    url=u,
                    match_type="MARKET_COMP",
                    composite_score=70.0
                )
            )

        return fallback_deals, "Hệ thống AI đang tạm thời chịu tải cao, gửi bạn các điểm bán tham khảo đa dạng từ thị trường."

judge_service = JudgeService()