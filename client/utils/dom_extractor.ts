// ============================================================
// dom_extractor.ts - Smart DOM Extractor (Universal)
// Không dùng selector cứng theo sàn.
// Gửi: tiêu đề, JSON-LD, meta tags, text sạch, ảnh, reviews.
// ============================================================

export interface PageSnapshot {
  url: string;
  domain: string;
  title: string;
  meta: Record<string, string>;
  json_ld: object[];
  clean_text: string;       // Nội dung chính đã lọc noise
  reviews_raw: string[];    // Tối đa 30 đoạn review
  image_url: string | null;
  page_type_hint: 'product' | 'listing' | 'cart' | 'unknown';
}

// ---- Các thẻ/class là noise, loại bỏ trước khi lấy text ----
const NOISE_TAGS = [
  'script', 'style', 'noscript', 'iframe', 'svg',
  'header', 'footer', 'nav', 'aside',
];
const NOISE_CLASS_PATTERNS = [
  /menu/i, /navbar/i, /nav-bar/i, /breadcrumb/i,
  /advertisement/i, /advert/i, /sidebar/i,
  /footer/i, /cookie/i, /popup/i, /modal-backdrop/i,
  /social/i, /share/i, /related/i, /recommend/i,
];

function isNoiseElement(el: Element): boolean {
  const cls = el.className?.toString() || '';
  const id = el.id || '';
  return NOISE_CLASS_PATTERNS.some(p => p.test(cls) || p.test(id));
}

/** Lấy text sạch từ body, bỏ script/ads/nav */
function extractCleanText(maxChars = 6000): string {
  const clone = document.body.cloneNode(true) as HTMLElement;

  // Xóa thẻ noise
  NOISE_TAGS.forEach(tag => {
    clone.querySelectorAll(tag).forEach(el => el.remove());
  });

  // Xóa element có class/id là noise
  clone.querySelectorAll('*').forEach(el => {
    if (isNoiseElement(el)) el.remove();
  });

  const text = clone.innerText || clone.textContent || '';
  // Nén khoảng trắng thừa
  return text.replace(/\s{3,}/g, '\n\n').trim().slice(0, maxChars);
}

/** Lấy tất cả JSON-LD trên trang */
function extractJsonLd(): object[] {
  const results: object[] = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach(el => {
    try {
      const parsed = JSON.parse(el.textContent || '');
      results.push(parsed);
    } catch {
      // bỏ qua JSON lỗi
    }
  });
  return results;
}

/** Lấy meta tags quan trọng */
function extractMeta(): Record<string, string> {
  const meta: Record<string, string> = {};
  const selectors: Record<string, string> = {
    'og:title':       'meta[property="og:title"]',
    'og:description': 'meta[property="og:description"]',
    'og:image':       'meta[property="og:image"]',
    'og:url':         'meta[property="og:url"]',
    'og:price':       'meta[property="product:price:amount"]',
    'og:currency':    'meta[property="product:price:currency"]',
    'description':    'meta[name="description"]',
    'keywords':       'meta[name="keywords"]',
  };
  Object.entries(selectors).forEach(([key, sel]) => {
    const el = document.querySelector(sel);
    const val = el?.getAttribute('content') || '';
    if (val) meta[key] = val;
  });
  return meta;
}

/** Lấy danh sách text đánh giá người dùng (tối đa 30) */
function extractReviewsRaw(max = 30): string[] {
  // Các pattern class phổ biến của review block
  const reviewPatterns = [
    /review/i, /comment/i, /feedback/i,
    /rating/i, /nhan-xet/i, /danh-gia/i, /binh-luan/i,
  ];

  const candidates = Array.from(document.querySelectorAll('[class], [id]')).filter(el => {
    const cls = el.className?.toString() || '';
    const id  = el.id || '';
    return reviewPatterns.some(p => p.test(cls) || p.test(id));
  });

  const texts: string[] = [];
  for (const el of candidates) {
    const txt = (el as HTMLElement).innerText?.trim();
    if (txt && txt.length > 20 && txt.length < 1000) {
      texts.push(txt);
      if (texts.length >= max) break;
    }
  }
  return texts;
}

/** Lấy ảnh đại diện tốt nhất */
function extractBestImage(): string | null {
  // Ưu tiên: og:image > product image lớn nhất
  const og = document.querySelector('meta[property="og:image"]')?.getAttribute('content');
  if (og) return og;

  let best: HTMLImageElement | null = null;
  document.querySelectorAll('img').forEach(img => {
    if (!best || (img.naturalWidth * img.naturalHeight) > (best.naturalWidth * best.naturalHeight)) {
      if (img.src && !img.src.includes('data:') && img.naturalWidth > 100) {
        best = img;
      }
    }
  });
  return best ? (best as HTMLImageElement).src : null;
}

/** Đoán loại trang */
function guessPageType(): PageSnapshot['page_type_hint'] {
  const url = window.location.href;
  const bodyText = document.body.innerText.slice(0, 2000).toLowerCase();

  if (/cart|giỏ hàng|checkout|thanh toán/.test(bodyText)) return 'cart';

  // Trang sản phẩm: có JSON-LD Product, hoặc có giá + h1
  const hasProductLd = document.querySelector('script[type="application/ld+json"]')
    ?.textContent?.includes('"Product"');
  const hasPrice = /[0-9]{3,}[.,][0-9]{3}/.test(document.body.innerText.slice(0, 5000));
  const hasH1 = !!document.querySelector('h1');
  if (hasProductLd || (hasPrice && hasH1)) return 'product';

  // Trang danh sách: nhiều link sản phẩm
  const itemLinks = document.querySelectorAll('a[href]').length;
  if (itemLinks > 20) return 'listing';

  return 'unknown';
}

/** Hàm chính — gọi từ content.ts */
export function capturePageSnapshot(): PageSnapshot {
  const url    = window.location.href;
  const domain = window.location.hostname;

  return {
    url,
    domain,
    title:       document.title || '',
    meta:        extractMeta(),
    json_ld:     extractJsonLd(),
    clean_text:  extractCleanText(6000),
    reviews_raw: extractReviewsRaw(30),
    image_url:   extractBestImage(),
    page_type_hint: guessPageType(),
  };
}
