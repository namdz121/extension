"""
selector_cache_service.py
--------------------------
Lưu và quản lý CSS selector cache theo domain.
Khi LLM đọc một trang và sinh ra selector, lưu vào đây.
Lần sau dùng selector, không cần gọi LLM nữa → nhanh gần như tức thì.

Tự động invalidate khi selector không còn hoạt động
(sàn đổi giao diện → hệ thống tự học lại từ đầu).
"""

import json
import time
from pathlib import Path
from typing import Optional
from app.models.understand_dto import SuggestedSelectors

# Lưu vào file JSON cạnh server_backend để persist qua restart
CACHE_DIR  = Path(__file__).resolve().parent.parent.parent
CACHE_FILE = CACHE_DIR / "selector_cache.json"

class SelectorCacheService:
    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            if CACHE_FILE.exists():
                self._cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                print(f"[SelectorCache] Đã nạp {len(self._cache)} domain từ cache.")
        except Exception as e:
            print(f"[SelectorCache] Không đọc được cache file: {e}")
            self._cache = {}

    def _save(self):
        try:
            CACHE_FILE.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[SelectorCache] Không ghi được cache: {e}")

    def get(self, domain: str) -> Optional[SuggestedSelectors]:
        """Lấy selector cho domain. Trả None nếu chưa có hoặc đã hết hạn (7 ngày)."""
        entry = self._cache.get(domain)
        if not entry:
            return None
        # Hết hạn sau 7 ngày (sàn thay đổi giao diện định kỳ)
        if time.time() - entry.get("ts", 0) > 7 * 86400:
            del self._cache[domain]
            return None
        return SuggestedSelectors(**entry.get("selectors", {}))

    def save(self, domain: str, selectors: SuggestedSelectors):
        """Lưu selector mới cho domain."""
        self._cache[domain] = {
            "selectors": selectors.model_dump(),
            "ts": time.time(),
        }
        self._save()
        print(f"[SelectorCache] Đã lưu selector cho domain: {domain}")

    def invalidate(self, domain: str):
        """Xoá selector khi phát hiện nó không còn hoạt động."""
        if domain in self._cache:
            del self._cache[domain]
            self._save()
            print(f"[SelectorCache] Đã xoá selector hỏng cho: {domain}")

    def stats(self) -> dict:
        return {"total_domains": len(self._cache), "domains": list(self._cache.keys())}


selector_cache = SelectorCacheService()
