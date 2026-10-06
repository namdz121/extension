import React from 'react';
import type { DealCandidate } from '../models/analyze_dto';

export interface DealCardItemProps {
  deal: DealCandidate;
  basePrice?: number;
}

export const DealCardItem: React.FC<DealCardItemProps> = ({ deal, basePrice }) => {
  const getDomainLabel = (urlStr: string) => {
    try {
      const hostname = new URL(urlStr).hostname.replace('www.', '');
      if (hostname.includes('shopee')) return 'Shopee';
      if (hostname.includes('lazada')) return 'Lazada';
      if (hostname.includes('cellphones')) return 'CellphoneS';
      if (hostname.includes('tiki')) return 'Tiki';
      if (hostname.includes('thegioididong')) return 'TGDD';
      return hostname.split('.')[0];
    } catch {
      return 'Nơi bán';
    }
  };

  const priceDiff = basePrice && deal.price > 0 ? deal.price - basePrice : null;
  const isCheaper = priceDiff !== null && priceDiff < 0;

  return (
    <div className="spa-deal-card">
      <div className="spa-deal-top">
        <span className="spa-deal-source">🛒 {getDomainLabel(deal.url)}</span>
        <span className={`spa-deal-badge ${deal.match_type === 'EXACT_MATCH' ? 'exact' : ''}`}>
          {deal.match_type === 'EXACT_MATCH' ? 'Chuẩn model' : 'Tham khảo'}
        </span>
      </div>

      <h4 className="spa-deal-title" title={deal.title}>
        {deal.title}
      </h4>

      <div className="spa-deal-bottom">
        <div>
          <div className="spa-deal-price">
            {deal.price > 0 ? `${deal.price.toLocaleString('vi-VN')} ₫` : 'Xem tại web'}
          </div>
          {priceDiff !== null && priceDiff !== 0 && (
            <div className={`spa-deal-diff ${isCheaper ? 'cheaper' : 'expensive'}`}>
              {isCheaper
                ? `▼ Tiết kiệm ${Math.abs(priceDiff).toLocaleString('vi-VN')} ₫`
                : `▲ Cao hơn ${priceDiff.toLocaleString('vi-VN')} ₫`}
            </div>
          )}
        </div>

        <a href={deal.url} target="_blank" rel="noopener noreferrer" className="spa-deal-btn">
          Xem ngay ↗
        </a>
      </div>
    </div>
  );
};