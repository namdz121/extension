import { extractPageMetadata } from '../utils/dom_parser';

export default defineContentScript({
  matches: ['<all_urls>'],
  main() {
    // Nhận thông điệp yêu cầu bóc tách từ SidePanel UI
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === 'EXTRACT_PAGE_DATA') {
        const data = extractPageMetadata();
        sendResponse(data);
      }
      return true;
    });
  },
});