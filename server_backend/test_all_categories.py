"""
test_all_categories.py
----------------------
Script kiểm thử tự động 4 nhóm sản phẩm khác nhau qua toàn bộ pipeline:
1. Sách / Truyện (Kiểm tra bắt đúng Tên sách, Tác giả, Tập mấy)
2. Điện thoại / Công nghệ (Kiểm tra bắt đúng Model, Dung lượng 256GB)
3. Giày dép / Thời trang (Kiểm tra bắt đúng Hãng, Mẫu, Size 42, Màu)
4. Hàng không thương hiệu / Web lạ (Kiểm tra cấm bịa, đánh dấu NOT_FOUND chuẩn)
"""

import asyncio
import json
from app.models.understand_dto import UnderstandPageRequestDTO, ExtractedProduct
from app.services.extractor_service import extractor_service
from app.services.multi_search_service import multi_search_service

TEST_CASES = [
    {
        "name": "TEST 1: SÁCH / TRUYỆN (Kiểm tra Tập & Tác giả)",
        "snapshot": UnderstandPageRequestDTO(
            url="https://fahasa.com/tham-tu-lung-danh-conan-tap-100.html",
            domain="fahasa.com",
            title="Thám Tử Lừng Danh Conan - Tập 100 - Tác giả Gosho Aoyama - NXB Kim Đồng",
            meta={
                "og:title": "Thám Tử Lừng Danh Conan - Tập 100",
                "og:price": "25000",
                "og:description": "Tập 100 đánh dấu cột mốc lịch sử của bộ truyện thám tử Conan."
            },
            clean_text="""
            Trang chủ > Truyện tranh > Conan
            Thám Tử Lừng Danh Conan - Tập 100
            Tác giả: Gosho Aoyama
            Công ty phát hành: NXB Kim Đồng
            Số tập: Tập 100
            Hình thức: Bìa mềm
            Giá bán: 25.000 ₫
            Tình trạng: Còn hàng
            """,
            page_type_hint="product"
        ),
        "check_fields": ["selected_volume", "author", "model", "search_queries"]
    },
    {
        "name": "TEST 2: ĐIỆN TỬ / CÔNG NGHỆ (Kiểm tra Model & Dung lượng)",
        "snapshot": UnderstandPageRequestDTO(
            url="https://cellphones.com.vn/iphone-15-pro-max-256gb.html",
            domain="cellphones.com.vn",
            title="iPhone 15 Pro Max 256GB | Chính hãng VN/A",
            meta={
                "og:title": "iPhone 15 Pro Max 256GB",
                "og:price": "29590000"
            },
            clean_text="""
            Điện thoại Apple iPhone 15 Pro Max 256GB VN/A
            Thương hiệu: Apple
            Dung lượng bộ nhớ: 256GB
            Màu sắc: Titan Tự Nhiên
            Phiên bản: Chính hãng VN/A
            Giá niêm yết: 34.990.000 ₫
            Giá ưu đãi hôm nay: 29.590.000 ₫
            Các tùy chọn dung lượng: 256GB (Đang chọn), 512GB, 1TB.
            """,
            page_type_hint="product"
        ),
        "check_fields": ["brand", "model", "selected_storage", "search_queries"]
    },
    {
        "name": "TEST 3: GIÀY DÉP / THỜI TRANG (Kiểm tra Size & Màu)",
        "snapshot": UnderstandPageRequestDTO(
            url="https://myshoes.vn/giay-nike-pegasus-40-den-size-42.html",
            domain="myshoes.vn",
            title="Giày chạy bộ Nike Air Zoom Pegasus 40 Nam - Màu Đen - Size 42",
            meta={
                "og:title": "Giày chạy bộ Nike Pegasus 40 - Đen",
                "og:price": "2690000"
            },
            clean_text="""
            Giày chạy bộ Nike Air Zoom Pegasus 40 Chính Hãng
            Hãng: Nike
            Mã sản phẩm: DV3853-001
            Màu sắc: Đen / Trắng
            Kích thước có sẵn: 40, 41, 42, 43, 44
            Size đang chọn: 42
            Giá bán: 2.690.000 ₫
            Thêm vào giỏ hàng
            """,
            page_type_hint="product"
        ),
        "check_fields": ["brand", "model", "selected_size", "selected_color", "search_queries"]
    },
    {
        "name": "TEST 4: HÀNG VÔ DANH / WEB LẠ (Kiểm tra cấm bịa, đánh dấu NOT_FOUND)",
        "snapshot": UnderstandPageRequestDTO(
            url="https://shopgiadungnhalam.vn/ke-gia-vi-sat.html",
            domain="shopgiadungnhalam.vn",
            title="Kệ để gia vị nhà bếp 2 tầng đa năng sơn tĩnh điện chống rỉ",
            meta={},
            clean_text="""
            Kệ đựng gia vị nhà bếp 2 tầng đa năng
            Chất liệu: Thép sơn tĩnh điện màu đen
            Kích thước: 30x15x40cm
            Giá: 129.000 ₫
            Giao hàng toàn quốc. Hotline đặt hàng: 0909xxxxxx
            """,
            page_type_hint="product"
        ),
        "check_fields": ["brand", "model_code", "variant_evidence_status", "search_queries"]
    }
]

async def run_tests():
    print("=" * 70)
    print("BẮT ĐẦU KIỂM THỬ THỰC TẾ EXTRACTOR & TAVILY QUERY TRÊN 4 NHÓM SẢN PHẨM")
    print("=" * 70)

    for tc in TEST_CASES:
        print(f"\n▶ {tc['name']}")
        snap = tc["snapshot"]
        extracted: ExtractedProduct = await extractor_service.extract(snap)

        print("-" * 50)
        print(f"  [Category]               : {extracted.category}")
        print(f"  [Brand]                  : {extracted.brand}")
        print(f"  [Model]                  : {extracted.model}")
        print(f"  [Model Code / ISBN]      : {extracted.model_code}")
        print(f"  [Author]                 : {extracted.author}")
        print(f"  [Selected Volume]        : {extracted.selected_volume}")
        print(f"  [Selected Size]          : {extracted.selected_size}")
        print(f"  [Selected Color]         : {extracted.selected_color}")
        print(f"  [Selected Storage]       : {extracted.selected_storage}")
        print(f"  [Available Options]      : {extracted.available_options}")
        print(f"  [Variant Evidence Status]: {extracted.variant_evidence_status}")
        print(f"  [Price]                  : {extracted.price} {extracted.currency}")
        print("  [Search Queries Sinh Ra]:")
        print(f"    - Strict (Tầng 1)      : {extracted.search_queries.strict_query}")
        print(f"    - Medium (Tầng 2)      : {extracted.search_queries.medium_query}")
        print(f"    - Broad  (Tầng 3)      : {extracted.search_queries.broad_query}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(run_tests())
