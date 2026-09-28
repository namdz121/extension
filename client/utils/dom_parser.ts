import type { AnalyzeRequestDTO } from '../models/analyze_dto';

export function extractPageMetadata(): AnalyzeRequestDTO {
  const url = window.location.href;

  // 1. Lấy tiêu đề chính
  const h1El = document.querySelector('h1');
  const rawTitle = h1El?.innerText?.trim() || document.title;

  // 2. Tìm kiếm giá hiển thị bằng Regex
  let rawPrice: number | undefined = undefined;
  const priceRegex = /([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]{1,3}(?:,[0-9]{3})+)\s*(?:₫|đ|VND|vnđ)/i;
  const bodyText = document.body.innerText;
  const match = bodyText.match(priceRegex);
  if (match && match[1]) {
    const cleanNum = match[1].replace(/[.,]/g, '');
    rawPrice = parseFloat(cleanNum);
  }

  // 3. Kiểm tra giá bị ẩn / flash sale
  const maskRegex = /(?:1xx|2xx|inbox|liên hệ|1\?\?\.k)/i;
  const isMasked = maskRegex.test(bodyText.slice(0, 4000));

  // 4. Lấy link ảnh minh họa
  const ogImg = document.querySelector('meta[property="og:image"]')?.getAttribute('content');
  const mainImg = document.querySelector('img')?.src;

  let platform = 'generic';
  if (url.includes('shopee.vn')) platform = 'shopee';
  else if (url.includes('lazada.vn')) platform = 'lazada';
  else if (url.includes('batdongsan.com.vn')) platform = 'batdongsan';

  return {
    page_url: url,
    raw_title: rawTitle,
    raw_price: rawPrice,
    is_price_masked: isMasked,
    image_data: ogImg || mainImg,
    platform
  };
}