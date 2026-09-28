from tavily import TavilyClient
from app.config.settings import settings
from app.models.entity import CanonicalEntity

class SearchService:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY.strip() if settings.TAVILY_API_KEY else ""
        if self.api_key:
            print(f"[SearchService] Đã nạp TAVILY_API_KEY thành công.")
            self.client = TavilyClient(api_key=self.api_key)
        else:
            print("[SearchService] CẢNH BÁO: Chưa tìm thấy TAVILY_API_KEY trong settings!")
            self.client = None

    async def search_market(self, entity: CanonicalEntity) -> list:
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

        # 1. Tạo từ khóa tìm kiếm cô đọng từ thực thể chuẩn hóa
        specs_str = " ".join(list(entity.key_specs.values())[:2]) if entity.key_specs else ""
        query_parts = [entity.brand or "", entity.model or "", specs_str]
        search_query = " ".join([p for p in query_parts if p]).strip()

        # Thêm ngữ cảnh tìm kiếm tùy danh mục
        if entity.category == "real_estate":
            full_query = f"{search_query} giá bán batdongsan"
        else:
            full_query = f"{search_query} giá bán mua ở đâu shopee lazada thegioididong cellphones"

        print(f"[SearchService] Thực hiện tìm kiếm Tavily với từ khóa: '{full_query}'")

        try:
            # 2. Gọi Tavily Search API
            response = self.client.search(
                query=full_query,
                search_depth="basic",
                max_results=5,
                include_answer=False
            )

            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "raw_price": None  # Giá sẽ được LLM Judge bóc tách từ content ở Mốc 4
                })

            print(f"[SearchService] Tìm thấy {len(results)} kết quả từ web.")
            return results

        except Exception as e:
            print(f"[SearchService] Lỗi khi gọi Tavily API: {e}")
            return []

search_service = SearchService()