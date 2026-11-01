import { capturePageSnapshot } from '../utils/dom_extractor';
import type { PageSnapshot } from '../utils/dom_extractor';

export default defineContentScript({
  matches: ['<all_urls>'],
  main() {
    // Nhận thông điệp từ SidePanel UI
    chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {

      // Lệnh mới: chụp snapshot toàn trang (dùng cho /understand-page)
      if (request.action === 'CAPTURE_PAGE_SNAPSHOT') {
        try {
          const snapshot: PageSnapshot = capturePageSnapshot();
          sendResponse({ ok: true, snapshot });
        } catch (err: any) {
          sendResponse({ ok: false, error: err?.message || 'DOM capture failed' });
        }
        return true;
      }

      // Giữ lại lệnh cũ để không break code cũ
      if (request.action === 'EXTRACT_PAGE_DATA') {
        try {
          const snapshot = capturePageSnapshot();
          sendResponse({
            page_url:        snapshot.url,
            raw_title:       snapshot.title,
            raw_price:       undefined,
            is_price_masked: false,
            image_data:      snapshot.image_url,
            platform:        snapshot.domain,
          });
        } catch {
          sendResponse(null);
        }
        return true;
      }

      return false;
    });
  },
});