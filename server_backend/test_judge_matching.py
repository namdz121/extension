"""
test_judge_matching.py
-----------------------
Kiểm thử bộ máy đối soát (Judge) xem có bị "lọt" hàng sai biến thể không:
- Sách Tập 100 vs Tập 99 vs Trọn bộ vs Móc khóa
- Giày Size 42 Đen vs Size 41 vs Màu trắng vs Dây giày
- Điện thoại 256GB vs 128GB vs Ốp lưng
"""

import asyncio
import json
import re
from google.genai import types
from app.models.understand_dto import ExtractedProduct, MatchStatus
from app.services.multi_search_service import multi_search_service, JUDGE_PROMPT_TEMPLATE

TEST_CASES = [
    {
        "name": "TEST 1: SÁCH (Gốc là Conan Tập 100, Giá 25.000 ₫)",
        "product": ExtractedProduct(
            model="Thám Tử Lừng Danh Conan",
            author="Gosho Aoyama",
            category="books",
            selected_volume="Tập 100",
            price=25000.0,
            currency="VND"
        ),
        "candidates": [
            {"title": "Truyện Tranh Conan Tập 100 - NXB Kim Đồng", "url": "https://tiki.vn/conan-100", "content": "Giá bán: 25.000 ₫. Tập 100 bản chuẩn bìa mềm."},
            {"title": "Truyện Tranh Conan Tập 99 - Gosho Aoyama", "url": "https://shopee.vn/conan-99", "content": "Giá bán: 22.000 ₫. Tập 99 mới 100%."},
            {"title": "Trọn bộ Conan từ tập 1 đến 100", "url": "https://fahasa.com/conan-tron-bo", "content": "Giá trọn bộ 100 tập: 2.500.000 ₫."},
            {"title": "Móc khóa mica Conan và Ran Mori", "url": "https://lazada.vn/moc-khoa-conan", "content": "Giá 15.000 ₫. Phụ kiện quà tặng."}
        ]
    },
    {
        "name": "TEST 2: GIÀY DÉP (Gốc là Nike Pegasus 40 - Màu Đen - Size 42, Giá 2.690.000 ₫)",
        "product": ExtractedProduct(
            brand="Nike",
            model="Nike Air Zoom Pegasus 40",
            category="fashion",
            selected_size="42",
            selected_color="Đen",
            price=2690000.0,
            currency="VND"
        ),
        "candidates": [
            {"title": "Giày chạy bộ Nike Air Zoom Pegasus 40 Đen Size 42", "url": "https://supersports.com.vn/pegasus-40-black-42", "content": "Hàng chính hãng Nike. Phối màu: Đen / Trắng. Size: 42. Giá: 2.590.000 ₫."},
            {"title": "Giày Nike Pegasus 40 Màu Đen Size 41", "url": "https://shopee.vn/pegasus-40-size-41", "content": "Thanh lý giày Nike Pegasus 40 màu đen nam size 41. Giá 2.100.000 ₫."},
            {"title": "Giày Nike Pegasus 40 Màu Trắng Size 42", "url": "https://tiki.vn/pegasus-40-trang-42", "content": "Phối màu trắng tinh khôi, size 42. Giá 2.750.000 ₫."},
            {"title": "Dây giày dẹt thay thế cho Nike Pegasus", "url": "https://shopee.vn/day-giay-nike", "content": "Dây giày thể thao cao cấp giá 35.000 ₫."}
        ]
    },
    {
        "name": "TEST 3: ĐIỆN TỬ (Gốc là iPhone 15 Pro Max 256GB, Giá 29.590.000 ₫)",
        "product": ExtractedProduct(
            brand="Apple",
            model="iPhone 15 Pro Max",
            category="electronics",
            selected_storage="256GB",
            price=29590000.0,
            currency="VND"
        ),
        "candidates": [
            {"title": "Apple iPhone 15 Pro Max 256GB Chính hãng VN/A", "url": "https://fptshop.com.vn/iphone-15-pro-max-256gb", "content": "Bản 256GB VN/A giá 29.490.000 ₫."},
            {"title": "iPhone 15 Pro Max 128GB VN/A", "url": "https://cellphones.com.vn/iphone-15-pro-max-128gb", "content": "Bản 128GB giá 26.990.000 ₫."},
            {"title": "Ốp lưng Magsafe cho iPhone 15 Pro Max", "url": "https://shopee.vn/op-lung-ip15pm", "content": "Ốp chống sốc giá 150.000 ₫."}
        ]
    }
]

async def run_judge_tests():
    print("=" * 70)
    print("BẮT ĐẦU KIỂM THỬ THẨM ĐỊNH ĐỐI SOÁT (JUDGE) XEM CÓ BỊ LỌT KHÔNG")
    print("=" * 70)

    for tc in TEST_CASES:
        print(f"\n▶ {tc['name']}")
        prod = tc["product"]
        candidates = tc["candidates"]

        search_text = ""
        for idx, item in enumerate(candidates, 1):
            search_text += f"\n--- [Ứng viên {idx}] ---\nTiêu đề: {item['title']}\nURL: {item['url']}\nNội dung: {item['content']}\n"

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            product_name=prod.model or "Chưa rõ",
            brand_or_author=prod.brand or prod.author or "Chưa rõ",
            model_code=prod.model_code or "Chưa rõ",
            category=prod.category or "general",
            volume=prod.selected_volume or "Không có số tập",
            size=prod.selected_size or "Không rõ size",
            color=prod.selected_color or "Không rõ màu",
            storage=prod.selected_storage or "Không rõ",
            user_price=prod.price or "Chưa rõ",
            currency=prod.currency or "VND",
            search_results=search_text
        )

        data = {}
        for m in multi_search_service.candidate_models:
            try:
                response = multi_search_service.gemini.models.generate_content(
                    model=m,
                    contents=[prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
                )
                raw = response.text or "{}"
                raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
                raw = re.sub(r"\n?```$", "", raw)
                data = json.loads(raw)
                if data:
                    break
            except Exception as err:
                print(f"Thử model {m} bị lỗi: {err}")

        deals = data.get("deals", [])
        print(f"  Kết quả: Có {len(deals)} deals được giữ lại:")
        for d in deals:
            st = d.get('match_status')
            title = d.get('title')
            price = d.get('price')
            note = d.get('matched_variant_note')
            badge = "✔ [BẢNG CHÍNH]" if st == "EXACT_VARIANT" else "⚠ [BẢNG PHỤ]"
            print(f"    {badge} [{st}] - {title}")
            print(f"       Giá: {price:,} ₫ | Ghi chú: {note}")

        # Kiểm tra xem phụ kiện có bị lọt không
        mismatches_leaked = [d for d in deals if "móc khóa" in d.get('title','').lower() or "dây giày" in d.get('title','').lower() or "ốp lưng" in d.get('title','').lower()]
        if mismatches_leaked:
            print("  ❌ CẢNH BÁO: Bị lọt phụ kiện rác vào kết quả!")
        else:
            print("  ✅ ĐÃ CHẶN SẠCH: Toàn bộ phụ kiện rác (móc khóa, dây giày, ốp lưng) bị LOẠI BỎ hoàn toàn!")

if __name__ == "__main__":
    asyncio.run(run_judge_tests())
