import type { AnalyzeRequestDTO } from '../models/analyze_dto';

export function extractPageMetadata(): AnalyzeRequestDTO {
  const url = window.location.href;
  let rawTitle = '';
  let rawPrice: number | undefined = undefined;

  // 1. Title extraction
  if (url.includes('shopee.vn')) {
    const titleEl = document.querySelector('h1, ._44qnta, [class*="product-briefing"] h1');
    rawTitle = (titleEl as HTMLElement | null)?.innerText?.trim() ?? '';
  } else if (url.includes('cellphones.com.vn')) {
    const cpsTitle = document.querySelector('.box-product-name h1, h1');
    rawTitle = (cpsTitle as HTMLElement | null)?.innerText?.trim() ?? '';
  } else if (url.includes('batdongsan.com.vn')) {
    const bdsTitle = document.querySelector('.re__pr-title, h1');
    rawTitle = (bdsTitle as HTMLElement | null)?.innerText?.trim() ?? '';
  }

  if (!rawTitle) {
    const h1 = document.querySelector('h1');
    const h1Text = (h1 as HTMLElement | null)?.innerText?.trim();
    if (h1Text) {
      rawTitle = h1Text;
    } else {
      const fullTitle = document.title || '';
      const pipeIndex = fullTitle.indexOf('|');
      const cleanTitle = pipeIndex !== -1 ? fullTitle.slice(0, pipeIndex) : fullTitle;
      const dashIndex = cleanTitle.indexOf('-');
      rawTitle = (dashIndex !== -1 ? cleanTitle.slice(0, dashIndex) : cleanTitle).trim();
    }
  }

  // 2. Price extraction without line-through elements
  if (url.includes('shopee.vn')) {
    const priceNodes = Array.from(document.querySelectorAll('.pqTWkA, .G274fP, [class*="product-price"]'));
    for (const node of priceNodes) {
      const el = node as HTMLElement;
      const style = window.getComputedStyle(el);
      const textDecor = style.textDecorationLine || '';
      if (textDecor.includes('line-through')) {
        continue;
      }

      const clean = el.innerText.replace(/[₫đ.,\s]/gi, '');
      const num = parseFloat(clean);
      if (!isNaN(num) && num > 1000) {
        rawPrice = num;
        break;
      }
    }
  } else if (url.includes('cellphones.com.vn')) {
    const priceEl = document.querySelector('.tpt---sale-price, .special-price');
    if (priceEl) {
      const clean = (priceEl as HTMLElement).innerText.replace(/[₫đ.,\s]/gi, '');
      const num = parseFloat(clean);
      if (!isNaN(num) && num > 1000) {
        rawPrice = num;
      }
    }
  }

  // 3. Fallback regex safe from undefined indexed access
  if (rawPrice === undefined) {
    const priceRegex = /([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]{1,3}(?:,[0-9]{3})+)\s*(?:₫|đ|VND|vnđ)/i;
    const topText = document.body.innerText.slice(0, 2500);
    const match = priceRegex.exec(topText);

    if (match) {
      const capturedGroup = match[1];
      if (typeof capturedGroup === 'string') {
        const cleanVal = capturedGroup.replace(/[.,]/g, '');
        const parsedNum = parseFloat(cleanVal);
        if (!isNaN(parsedNum) && parsedNum > 1000) {
          rawPrice = parsedNum;
        }
      }
    }
  }

  const ogImg = document.querySelector('meta[property="og:image"]')?.getAttribute('content');
  const mainImg = (document.querySelector('img') as HTMLImageElement | null)?.src;

  return {
    page_url: url,
    raw_title: rawTitle,
    raw_price: rawPrice,
    image_data: ogImg || mainImg
  };
}