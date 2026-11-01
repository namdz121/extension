// ---- Legacy types (giữ để không break) ----
export interface CanonicalEntity {
  category: string;
  brand?: string;
  model?: string;
  key_specs: Record<string, any>;
  normalized_price?: number;
  search_keywords?: string;
}

export interface DealCandidate {
  title: string;
  price: number;
  url: string;
  match_type: 'EXACT_MATCH' | 'VARIANT_DIFF' | 'MARKET_COMP';
  composite_score: number;
}

export interface AnalyzeRequestDTO {
  page_url: string;
  raw_title?: string;
  raw_price?: number;
  is_price_masked?: boolean;
  image_data?: string;
  platform?: string;
}

export interface AnalyzeResponseDTO {
  canonical_entity: CanonicalEntity;
  deals: DealCandidate[];
  ai_verdict: string;
}

// ---- New pipeline types ----

/** Snapshot DOM được gửi lên backend từ content.ts */
export interface UnderstandPageRequestDTO {
  url: string;
  domain: string;
  title: string;
  meta: Record<string, string>;
  json_ld: object[];
  clean_text: string;
  reviews_raw: string[];
  image_url: string | null;
  page_type_hint: 'product' | 'listing' | 'cart' | 'unknown';
}

/** Kết quả Extractor LLM: thông tin sản phẩm + bằng chứng */
export interface ExtractedProduct {
  page_type: 'product' | 'listing' | 'cart' | 'unknown';
  brand: string | null;
  model: string | null;
  category: string | null;
  variant: string | null;          // màu, dung lượng, size...
  condition: 'new' | 'used' | 'refurbished' | 'unknown';
  price: number | null;
  original_price: number | null;
  currency: string;
  seller: string | null;
  // Bằng chứng nguyên văn từ nguồn
  evidence: {
    title_excerpt: string;
    price_excerpt: string;
    seller_excerpt: string;
  };
  // Selector LLM sinh ra để dùng lại lần sau
  suggested_selectors: {
    title: string | null;
    price: string | null;
    reviews_container: string | null;
  };
}

/** Kết quả Verifier LLM */
export interface VerifierResult {
  title_verified: 'yes' | 'no' | 'insufficient';
  price_verified: 'yes' | 'no' | 'insufficient';
  price_in_source: boolean;  // kiểm tra chuỗi số có trong nguồn không
  verdict: 'agree' | 'disagree' | 'partial';
  note: string;
}

/** Deal từ một sàn thương mại cụ thể */
export interface PlatformDeal {
  platform: string;            // 'Shopee', 'Lazada', 'Tiki'...
  title: string;
  price: number;
  url: string;
  seller: string | null;
  label: 'cheapest' | 'most_trusted' | 'best_overall' | 'normal';
  composite_score: number;     // 0-100
  evidence_excerpt: string;    // đoạn trích bằng chứng
}

/** Response từ /api/v1/understand-page */
export interface UnderstandPageResponseDTO {
  product: ExtractedProduct;
  verifier: VerifierResult;
  confidence_score: number;    // 0-100, tính từ đồng thuận
  price_range: {
    min: number | null;
    max: number | null;
    avg: number | null;
    currency: string;
  };
  platform_deals: PlatformDeal[];
  ai_verdict: string;
  suggested_selectors: ExtractedProduct['suggested_selectors'];
}