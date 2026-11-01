import asyncio
import re
from urllib.parse import urlparse
from tavily import TavilyClient
from app.config.settings import settings
from app.models.entity import CanonicalEntity

# Danh mục các website mua sắm & chuỗi bán lẻ chuyên dụng hàng đầu tại Việt Nam
VIETNAM_CATEGORY_DOMAINS = {
    # 1. Điện tử, điện thoại, máy tính bảng, laptop, phụ kiện công nghệ, âm thanh
    "electronics": [
        "thegioididong.com", "cellphones.com.vn", "fptshop.com.vn",
        "hoanghamobile.com", "didongviet.vn", "viettelstore.vn",
        "phongvu.vn", "gearvn.com", "hanoicomputer.vn",
        "shopee.vn", "shop.tiktok.com", "lazada.vn", "tiki.vn"
    ],
    # 2. Đồ gia dụng, điện máy, tivi, tủ lạnh, máy giặt, nồi chiên, bếp từ, quạt, máy lọc
    "home_appliances": [
        "dienmayxanh.com", "mediamart.vn", "nguyenkim.com",
        "dienmaycholon.vn", "meta.vn", "hc.com.vn", "pico.vn",
        "shopee.vn", "shop.tiktok.com", "lazada.vn", "tiki.vn"
    ],
    # 3. Mỹ phẩm, chăm sóc da, làm đẹp, son, kem chống nắng, nước hoa
    "beauty": [
        "hasaki.vn", "watsons.vn", "guardian.com.vn",
        "thegioiskinfood.com", "cocolux.com", "beautygarden.vn",
        "shopee.vn", "shop.tiktok.com", "lazada.vn", "tiki.vn"
    ],
    # 4. Thời trang, quần áo, giày dép, túi xách, balo, phụ kiện
    "fashion": [
        "supersports.com.vn", "myshoes.vn", "sneakerdaily.vn", "bitis.com.vn",
        "mwc.com.vn", "ananas.vn", "juno.vn", "routine.vn", "canifa.com", "coolmate.me",
        "shopee.vn", "shop.tiktok.com", "lazada.vn", "tiki.vn"
    ],
    # 5. Sách, văn phòng phẩm, giáo dục
    "books": [
        "fahasa.com", "nhasachtrithuc.vn", "vinabook.com", "phuongnambook.com",
        "tiki.vn", "shopee.vn", "shop.tiktok.com", "lazada.vn"
    ],
    # 6. Bất động sản, căn hộ, nhà đất
    "real_estate": [
        "batdongsan.com.vn", "homedy.com", "chotot.com",
        "alonhadat.com.vn", "nhadat24h.net", "meeyland.com"
    ],
    # 7. Mặc định / Tổng hợp
    "general": [
        "shopee.vn", "shop.tiktok.com", "lazada.vn", "tiki.vn",
        "thegioididong.com", "dienmayxanh.com", "cellphones.com.vn",
        "fptshop.com.vn", "mediamart.vn", "nguyenkim.com", "meta.vn"
    ]
}

# Các trang báo chí, mạng xã hội giải trí hoặc trang spam
DOMAIN_BLACKLIST = {
    "tradingkey.com", "coinmarketcap.com", "cafef.vn", "baomoi.com",
    "vietstock.vn", "vnexpress.net", "dantri.com.vn", "tuoitre.vn",
    "thanhnien.vn", "facebook.com", "youtube.com",
    "finance.yahoo.com", "pinterest.com", "instagram.com", "wikipedia.org",
    "znews.vn", "genk.vn", "tinhte.vn"
}

def extract_clean_domain(url: str) -> str:
    """Trích xuất tên miền sạch loại bỏ tiền tố www."""
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

        # 1. Loại bỏ trang chủ thuần túy (e.g. canifa.com, canifa.com/, site.vn/vi, site.vn/home)
        if not path or path.lower() in ["vi", "en", "vn", "home", "index", "index.html"]:
            return False

        # 2. Loại bỏ các path danh mục/collection chung chung nếu không có slug sản phẩm
        path_segments = [p.lower() for p in path.split("/") if p]
        if len(path_segments) == 1 and path_segments[0] in [
            "collections", "collection", "category", "categories", 
            "danh-muc", "san-pham", "products", "search", "tim-kiem", "shop"
        ]:
            return False

        if len(path_segments) == 2 and path_segments[0] in ["collections", "category", "danh-muc"]:
            return False

        # 3. Lọc tiêu đề danh mục / trang chủ
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


def normalize_url(url: str) -> str:
    """Loại bỏ protocol, www, query params (tracking, ref, sp_atk...), và trailing slashes."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.rstrip("/")
        return f"{netloc}{path}"
    except Exception:
        return (url or "").strip().lower()

def extract_shopee_ids(url: str) -> tuple[str, str]:
    """Trích xuất (shop_id, item_id) từ URL Shopee."""
    match = re.search(r"-i\.(\d+)\.(\d+)", url)
    if match:
        return match.group(1), match.group(2)
    match2 = re.search(r"/product/(\d+)/(\d+)", url)
    if match2:
        return match2.group(1), match2.group(2)
    return "", ""

def extract_tiktok_product_id(url: str) -> str:
    """Trích xuất product_id từ URL TikTok Shop."""
    match = re.search(r"/product/(\d+)", url)
    if match:
        return match.group(1)
    match2 = re.search(r"/pdp/(\d+)", url)
    if match2:
        return match2.group(1)
    return ""

def is_same_product_or_page(deal_url: str, current_url: str) -> bool:
    """Kiểm tra xem link ứng viên có trỏ về chính sản phẩm / bài đăng người dùng đang xem không."""
    if not deal_url or not current_url:
        return False

    norm_deal = normalize_url(deal_url)
    norm_curr = normalize_url(current_url)

    # 1. Trùng đường dẫn chuẩn hóa tuyệt đối (bỏ query parameters, www, protocol)
    if norm_deal == norm_curr:
        return True

    # 2. Cùng sàn Shopee: nếu trùng item_id -> chính là cùng một bài đăng sản phẩm
    if "shopee.vn" in norm_deal and "shopee.vn" in norm_curr:
        _, i1 = extract_shopee_ids(deal_url)
        _, i2 = extract_shopee_ids(current_url)
        if i1 and i2 and i1 == i2:
            return True

    # 3. Cùng sàn TikTok Shop: nếu trùng product_id -> chính là cùng sản phẩm
    if "tiktok.com" in norm_deal and "tiktok.com" in norm_curr:
        p1 = extract_tiktok_product_id(deal_url)
        p2 = extract_tiktok_product_id(current_url)
        if p1 and p2 and p1 == p2:
            return True

    # 4. Cùng sàn Tiki (-p<id>.html)
    tiki1 = re.search(r"-p(\d+)\.html", deal_url)
    tiki2 = re.search(r"-p(\d+)\.html", current_url)
    if tiki1 and tiki2 and tiki1.group(1) == tiki2.group(1):
        return True

    # 5. Cùng sàn Lazada (-i<id>)
    lzd1 = re.search(r"-i(\d+)", deal_url)
    lzd2 = re.search(r"-i(\d+)", current_url)
    if lzd1 and lzd2 and lzd1.group(1) == lzd2.group(1):
        return True

    return False


def is_domain_blacklisted(url: str, domain: str) -> bool:
    """Kiểm tra domain có bị cấm không, cho phép shop.tiktok.com nhưng loại bỏ tiktok video giải trí"""
    # Luôn cho phép link mua hàng TikTok Shop
    if "shop.tiktok.com" in domain or "tiktok.com/view/product" in url or "tiktok.com/pdp" in url:
        return False
    # Chặn video clip tiktok giải trí thuần túy
    if "tiktok.com" in domain:
        return True
    return any(b in domain for b in DOMAIN_BLACKLIST)

def rank_and_deduplicate_by_domain(raw_items: list, category: str, current_url: str = "") -> list:
    """
    1. Lọc bỏ các web spam / báo chí không bán hàng.
    2. Áp dụng quy tắc ưu tiên Shopee <-> TikTok Shop:
       - Nếu đang xem Shopee: TikTok Shop (shop.tiktok.com) có ưu tiên CAO NHẤT (+350đ).
       - Nếu đang xem TikTok Shop: Shopee (shopee.vn) có ưu tiên CAO NHẤT (+350đ).
       - Nếu đang xem tại các web khác: Cả Shopee và TikTok Shop đều có ưu tiên CAO NHẤT (+350đ).
    3. Nâng cao ưu tiên các web shop chuyên ngành Việt Nam (.vn).
    4. Đẩy link nước ngoài xuống mức ưu tiên thấp nhất.
    5. Gom nhóm: Mỗi tên miền (domain) CHỈ GIỮ LẠI ĐÚNG 1 KẾT QUẢ TỐT NHẤT.
    """
    cat_domains = VIETNAM_CATEGORY_DOMAINS.get(category, VIETNAM_CATEGORY_DOMAINS["general"])
    domain_to_best_item = {}

    curr_lower = (current_url or "").lower()
    is_from_shopee = "shopee.vn" in curr_lower
    is_from_tiktok = "tiktok.com" in curr_lower

    for item in raw_items:
        url = item.get("url", "")
        title = item.get("title", "")
        domain = extract_clean_domain(url)
        if not domain or is_domain_blacklisted(url, domain):
            continue

        # BẮT BUỘC 1: Không lấy chính link bài đăng sản phẩm người dùng đang xem!
        if current_url and is_same_product_or_page(url, current_url):
            print(f"[SearchService] Bỏ qua vì trùng với link đang xem: {url[:70]}")
            continue

        # BẮT BUỘC 2: Phải là trang sản phẩm cụ thể, loại bỏ trang chủ & trang danh mục
        if not is_valid_product_url(url, title):
            continue

        score = 0

        # === QUY TẮC ĐỐI TRỌNG SHOPEE <-> TIKTOK SHOP ===
        if is_from_shopee:
            if "shop.tiktok.com" in domain:
                score += 350  # Đang xem Shopee -> TikTok Shop là đối trọng ưu tiên số 1
            elif "shopee.vn" in domain:
                score += 30   # Trừ nhẹ để nhường vị trí cho sàn khác đối chiếu
            else:
                score += 150
        elif is_from_tiktok:
            if "shopee.vn" in domain:
                score += 350  # Đang xem TikTok -> Shopee là đối trọng ưu tiên số 1
            elif "tiktok.com" in domain:
                score += 30
            else:
                score += 150
        else:
            # Ở các web khác (CellphoneS, TGDĐ, Điện Máy Xanh, Lazada, Coolmate...):
            if "shopee.vn" in domain or "shop.tiktok.com" in domain:
                score += 350  # Cả Shopee và TikTok Shop có độ ưu tiên cao nhất!
            else:
                score += 150

        # Ưu tiên cấp 1: Nằm trong web chuyên ngành Việt Nam (+150đ)
        if any(d in domain for d in cat_domains):
            score += 150

        # Ưu tiên cấp 2: Sàn TMĐT lớn tại Việt Nam (+120đ)
        if any(d in domain for d in ["lazada.vn", "tiki.vn", "sendo.vn"]):
            score += 120

        # Ưu tiên cấp 3: Tên miền đuôi .vn hoặc .com.vn (+80đ)
        if domain.endswith(".vn") or ".com.vn" in domain:
            score += 80

        # Đơn vị tiền tệ Việt Nam có trong snippet (+25đ)
        content_lower = item.get("content", "").lower()
        if "₫" in content_lower or "vnd" in content_lower or "đ" in content_lower or "đồng" in content_lower:
            score += 25

        # Giảm sâu điểm đối với các link nước ngoài
        if any(c in domain for c in [".ph", ".th", ".my", ".sg", ".id", ".cn", ".us", "amazon", "aliexpress", "ebay", "walmart"]):
            score -= 100

        # Nếu domain này chưa có hoặc item này có điểm cao hơn
        if domain not in domain_to_best_item or score > domain_to_best_item[domain][0]:
            domain_to_best_item[domain] = (score, item)

    # Sắp xếp các domain theo điểm ưu tiên giảm dần
    sorted_items = sorted(domain_to_best_item.values(), key=lambda x: x[0], reverse=True)
    return [x[1] for x in sorted_items]


class SearchService:
    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        self.api_key = settings.TAVILY_API_KEY.strip() if settings.TAVILY_API_KEY else ""
        if self.api_key:
            print(f"[SearchService] Đã nạp TAVILY_API_KEY thành công.")
            self.client = TavilyClient(api_key=self.api_key)
        else:
            print("[SearchService] CẢNH BÁO: Chưa tìm thấy TAVILY_API_KEY trong settings!")
            self.client = None

    async def search_market(self, entity: CanonicalEntity, current_url: str = "") -> list:
        # Nếu chưa cấu hình key Tavily, trả về mock dự phòng
        if not self.client:
            return [
                {
                    "title": f"{entity.model} 128GB Chính hãng VN/A",
                    "price": 24990000.0,
                    "url": "https://shopee.vn/sample-item",
                    "snippet": "Dữ liệu mẫu do chưa điền TAVILY_API_KEY"
                }
            ]

        # 1. Tạo từ khóa tìm kiếm cốt lõi: Ưu tiên search_keywords từ AI Normalizer
        category = getattr(entity, "category", "general") or "general"
        search_kw = getattr(entity, "search_keywords", "") or ""
        if search_kw.strip():
            search_query = search_kw.strip()
        else:
            specs_str = " ".join(list(entity.key_specs.values())[:2]) if entity.key_specs else ""
            query_parts = [entity.brand or "", entity.model or "", specs_str]
            search_query = " ".join([p for p in query_parts if p]).strip()

        curr_lower = (current_url or "").lower()
        is_from_shopee = "shopee.vn" in curr_lower
        is_from_tiktok = "tiktok.com" in curr_lower

        # 2. Xây dựng 2 truy vấn song song có định hướng đối trọng Shopee <-> TikTok Shop
        if is_from_shopee:
            query_market = f"{search_query} giá bán mua tiktok shop shop.tiktok.com lazada tiki"
        elif is_from_tiktok:
            query_market = f"{search_query} giá bán chính hãng mua shopee lazada tiki"
        else:
            query_market = f"{search_query} giá bán shopee tiktok shop shop.tiktok.com lazada tiki"

        # Truy vấn 2: Các chuỗi bán lẻ chuyên dụng theo từng loại mặt hàng
        query_lower = search_query.lower()
        is_shoes = any(k in query_lower for k in ["giày", "sneaker", "dép", "sandal", "chạy bộ", "thể thao"])

        if category == "electronics":
            query_specialized = f"{search_query} giá bán thegioididong cellphones fptshop hoanghamobile didongviet viettelstore"
        elif category == "home_appliances":
            query_specialized = f"{search_query} giá bán dienmayxanh nguyenkim mediamart dienmaycholon meta hc"
        elif category == "beauty":
            query_specialized = f"{search_query} giá bán hasaki watsons guardian thegioiskinfood cocolux"
        elif category == "fashion":
            if is_shoes:
                query_specialized = f"{search_query} giá bán supersports myshoes sneakerdaily bitis mwc"
            else:
                query_specialized = f"{search_query} giá bán routine canifa shop thời trang online"
        elif category == "books":
            query_specialized = f"{search_query} giá bán fahasa vinabook nhasachtrithuc"
        elif category == "real_estate":
            query_specialized = f"{search_query} giá bán batdongsan homedy chotot"
        else:
            query_specialized = f"{search_query} giá bán chính hãng mua online"

        print(f"[SearchService] Tìm kiếm song song 2 kênh (Nguồn hiện tại: {'Shopee' if is_from_shopee else 'TikTok' if is_from_tiktok else 'Khác'}):")
        print(f"  - Q1 (Đối trọng TMĐT): '{query_market}'")
        print(f"  - Q2 (Web chuyên dụng): '{query_specialized}'")

        loop = asyncio.get_event_loop()

        def do_search(q: str):
            try:
                res = self.client.search(
                    query=q,
                    search_depth="basic",
                    max_results=10,
                    include_answer=False
                )
                return res.get("results", [])
            except Exception as e:
                print(f"[SearchService] Lỗi query '{q}': {e}")
                return []

        try:
            results_market, results_specialized = await asyncio.gather(
                loop.run_in_executor(None, do_search, query_market),
                loop.run_in_executor(None, do_search, query_specialized)
            )

            all_raw = results_market + results_specialized
            print(f"[SearchService] Tổng số kết quả thô thu được từ cả 2 kênh: {len(all_raw)}")

            # Lọc phân hạng ưu tiên Shopee <-> TikTok Shop & các web Việt Nam
            ranked_unique = rank_and_deduplicate_by_domain(all_raw, category, current_url=current_url)

            # Định dạng danh sách trả về cho JudgeService
            formatted = []
            for item in ranked_unique:
                formatted.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "raw_price": None
                })

            print(f"[SearchService] Sau khi ưu tiên & lọc trùng: {len(formatted)} website khác nhau.")
            return formatted

        except Exception as e:
            print(f"[SearchService] Lỗi khi xử lý tìm kiếm song song: {e}")
            return []


search_service = SearchService()