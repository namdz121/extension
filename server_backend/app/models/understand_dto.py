from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field


# ---- Request: snapshot DOM từ content.ts ----

class UnderstandPageRequestDTO(BaseModel):
    url: str
    domain: str
    title: str
    meta: Dict[str, str] = {}
    json_ld: List[Any] = []
    clean_text: str = ""
    reviews_raw: List[str] = []
    image_url: Optional[str] = None
    page_type_hint: Literal["product", "listing", "cart", "unknown"] = "unknown"


# ---- Trạng thái bằng chứng & Trạng thái khớp ----

class EvidenceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"       # Có trích dẫn chữ nguyên văn trong trang
    AMBIGUOUS = "AMBIGUOUS"       # Có dữ liệu nhưng mâu thuẫn hoặc chưa chắc chắn
    NOT_FOUND = "NOT_FOUND"       # Trang web hoàn toàn không đề cập đến


class MatchStatus(str, Enum):
    EXACT_VARIANT = "EXACT_VARIANT"                     # Cùng sản phẩm, đúng biến thể -> Bảng chính
    SAME_PRODUCT_OTHER_VARIANT = "SAME_OTHER_VARIANT"   # Cùng sản phẩm, khác biến thể (size, màu, tập) -> Bảng phụ
    SIMILAR_ALTERNATIVE = "SIMILAR_ALTERNATIVE"         # Sản phẩm tương tự thay thế
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"     # Chưa đủ bằng chứng đối soát
    MISMATCH = "MISMATCH"                               # Sai sản phẩm hoàn toàn (loại bỏ)


# ---- Chiến lược truy vấn 3 tầng cho Search Engine (Chống rỗng) ----

class SearchQueries(BaseModel):
    strict_query: str = ""       # Tầng 1: Tên chuẩn + Mã định danh / Tập / Cấu hình (Đặc hiệu cao)
    medium_query: str = ""       # Tầng 2: Tên chuẩn + Hãng / Tác giả (Nới lỏng biến thể)
    broad_query: str = ""        # Tầng 3: Tên hiển thị thông dụng + sàn bán (Mở rộng)


# ---- Kết quả Extractor LLM ----

class ExtractedEvidence(BaseModel):
    title_excerpt: str = ""
    price_excerpt: str = ""
    seller_excerpt: str = ""
    variant_excerpt: str = ""


class SuggestedSelectors(BaseModel):
    title: Optional[str] = None
    price: Optional[str] = None
    reviews_container: Optional[str] = None


class ExtractedProduct(BaseModel):
    page_type: Literal["product", "listing", "cart", "unknown"] = "unknown"
    
    # Lớp 1: Danh tính sản phẩm (Product Identity)
    brand: Optional[str] = None
    model: Optional[str] = None
    model_code: Optional[str] = None                  # SKU, ISBN, Part number
    category: Optional[str] = None                    # books, electronics, fashion, beauty, general...
    author: Optional[str] = None                      # Cho sách/truyện
    
    # Lớp 2: Danh tính biến thể (Variant Identity)
    variant: Optional[str] = None                     # Chuỗi mô tả biến thể chung
    selected_volume: Optional[str] = None             # Tập 1, Tập 2, Tập 3...
    selected_size: Optional[str] = None               # Size 42, Size L...
    selected_color: Optional[str] = None              # Màu đen, trắng...
    selected_storage: Optional[str] = None            # 128GB, 256GB...
    available_options: List[str] = []                 # Danh sách các option nhìn thấy trên trang
    variant_evidence_status: EvidenceStatus = EvidenceStatus.NOT_FOUND
    
    # Lớp 3: Lựa chọn mua hàng (Offer Identity)
    condition: Literal["new", "used", "refurbished", "unknown"] = "unknown"
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "VND"
    seller: Optional[str] = None
    
    # Bằng chứng trích xuất & Selectors gợi ý
    evidence: ExtractedEvidence = ExtractedEvidence()
    suggested_selectors: SuggestedSelectors = SuggestedSelectors()
    
    # 3 câu truy vấn tìm kiếm sinh ra cho Tavily
    search_queries: SearchQueries = SearchQueries()


# ---- Kết quả Verifier LLM ----

class VerifierResult(BaseModel):
    title_verified: Literal["yes", "no", "insufficient"] = "insufficient"
    price_verified: Literal["yes", "no", "insufficient"] = "insufficient"
    price_in_source: bool = False    # string-match đơn giản
    verdict: Literal["agree", "disagree", "partial"] = "partial"
    note: str = ""


# ---- Deal từ một sàn thương mại ----

class PlatformDeal(BaseModel):
    platform: str                                       # "Shopee", "Lazada", "Tiki"...
    title: str
    price: float
    url: str
    seller: Optional[str] = None
    match_status: MatchStatus = MatchStatus.INSUFFICIENT_EVIDENCE
    matched_variant_note: Optional[str] = None          # Ví dụ: "Khác size: 41 thay vì 42"
    label: Literal["cheapest", "most_trusted", "best_overall", "normal"] = "normal"
    composite_score: float = 0.0                        # 0-100
    evidence_excerpt: str = ""


# ---- Price summary ----

class PriceRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    avg: Optional[float] = None
    currency: str = "VND"


# ---- Response trả về extension ----

class UnderstandPageResponseDTO(BaseModel):
    product: ExtractedProduct
    verifier: VerifierResult
    confidence_score: float                             # 0-100, tính từ mức đồng thuận
    price_range: PriceRange
    platform_deals: List[PlatformDeal] = []             # Toàn bộ deals
    exact_deals: List[PlatformDeal] = []                # Chỉ deals đúng sản phẩm & đúng biến thể
    other_variant_deals: List[PlatformDeal] = []        # Cùng sản phẩm nhưng khác biến thể
    similar_deals: List[PlatformDeal] = []              # Sản phẩm tương tự
    ai_verdict: str
    suggested_selectors: SuggestedSelectors
