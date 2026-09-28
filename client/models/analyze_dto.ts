export interface CanonicalEntity {
  category: string;
  brand?: string;
  model?: string;
  key_specs: Record<string, any>;
  normalized_price?: number;
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