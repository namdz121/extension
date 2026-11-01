import React from 'react';
import type { DealCandidate } from '../models/analyze_dto';

export interface DealCardItemProps {
  deal: DealCandidate;
  basePrice?: number;
}

export const DealCardItem: React.FC<DealCardItemProps> = ({ deal, basePrice }) => {
  const getDomainInfo = (urlStr: string) => {
    try {
      const hostname = new URL(urlStr).hostname.replace('www.', '').toLowerCase();

      // Nhận diện các sàn và shop uy tín tại Việt Nam
      if (hostname.includes('shopee.vn')) return { label: 'Shopee VN', isVN: true };
      if (hostname.includes('shop.tiktok.com') || hostname.includes('tiktok.com')) return { label: 'TikTok Shop', isVN: true };
      if (hostname.includes('lazada.vn')) return { label: 'Lazada VN', isVN: true };
      if (hostname.includes('tiki.vn')) return { label: 'Tiki', isVN: true };
      if (hostname.includes('cellphones.com.vn')) return { label: 'CellphoneS', isVN: true };
      if (hostname.includes('thegioididong.com')) return { label: 'Thế Giới Di Động', isVN: true };
      if (hostname.includes('dienmayxanh.com')) return { label: 'Điện Máy Xanh', isVN: true };
      if (hostname.includes('fptshop.com.vn')) return { label: 'FPT Shop', isVN: true };
      if (hostname.includes('hoanghamobile.com')) return { label: 'Hoàng Hà Mobile', isVN: true };
      if (hostname.includes('didongviet.vn')) return { label: 'Di Động Việt', isVN: true };
      if (hostname.includes('viettelstore.vn')) return { label: 'Viettel Store', isVN: true };
      if (hostname.includes('mediamart.vn')) return { label: 'MediaMart', isVN: true };
      if (hostname.includes('nguyenkim.com')) return { label: 'Nguyễn Kim', isVN: true };
      if (hostname.includes('dienmaycholon.vn')) return { label: 'ĐM Chợ Lớn', isVN: true };
      if (hostname.includes('meta.vn')) return { label: 'META.vn', isVN: true };
      if (hostname.includes('phongvu.vn')) return { label: 'Phong Vũ', isVN: true };
      if (hostname.includes('gearvn.com')) return { label: 'GearVN', isVN: true };
      if (hostname.includes('hasaki.vn')) return { label: 'Hasaki', isVN: true };
      if (hostname.includes('watsons.vn')) return { label: 'Watsons', isVN: true };
      if (hostname.includes('guardian.com.vn')) return { label: 'Guardian', isVN: true };
      if (hostname.includes('coolmate.me')) return { label: 'Coolmate', isVN: true };
      if (hostname.includes('canifa.com')) return { label: 'Canifa', isVN: true };
      if (hostname.includes('fahasa.com')) return { label: 'Fahasa', isVN: true };
      if (hostname.includes('batdongsan.com.vn')) return { label: 'Batdongsan', isVN: true };
      if (hostname.includes('chotot.com')) return { label: 'Chợ Tốt', isVN: true };

      const isVN = hostname.endsWith('.vn') || hostname.includes('.vn');
      const firstPart = hostname.split('.')[0] || 'Web';
      const cleanName = firstPart.charAt(0).toUpperCase() + firstPart.slice(1);
      return { label: cleanName, isVN };
    } catch {
      return { label: 'Điểm bán', isVN: false };
    }
  };

  const domainInfo = getDomainInfo(deal.url);
  const priceDiff = basePrice && deal.price > 0 ? deal.price - basePrice : null;
  const isCheaper = priceDiff !== null && priceDiff < 0;

  return (
    <div className="spa-deal-card">
      <div className="spa-deal-top">
        <span className="spa-deal-source">
          🛒 {domainInfo.label}
          {domainInfo.isVN && <span className="spa-vn-badge" title="Website bán lẻ tại Việt Nam">🇻🇳</span>}
        </span>
        <span className={`spa-deal-badge ${deal.match_type === 'EXACT_MATCH' ? 'exact' : deal.match_type === 'VARIANT_DIFF' ? 'variant-diff' : ''}`}>
          {deal.match_type === 'EXACT_MATCH' ? 'Chuẩn model' : deal.match_type === 'VARIANT_DIFF' ? 'Khác biến thể' : 'Tham khảo'}
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

export default DealCardItem;