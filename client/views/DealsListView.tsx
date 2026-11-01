import React from 'react';
import type { DealCandidate } from '../models/analyze_dto';
import { DealCardItem } from './DealCardItem';

interface DealsListProps {
  deals: DealCandidate[];
  basePrice?: number;
  currentUrl?: string;
}

const normalizeUrl = (url: string) => {
  try {
    const u = new URL(url);
    return (u.hostname.replace(/^www\./, '') + u.pathname).replace(/\/$/, '').toLowerCase();
  } catch {
    return (url || '').trim().toLowerCase();
  }
};

const isSameUrl = (dealUrl: string, currUrl?: string) => {
  if (!dealUrl || !currUrl) return false;
  const nDeal = normalizeUrl(dealUrl);
  const nCurr = normalizeUrl(currUrl);
  if (nDeal === nCurr) return true;

  // Shopee item ID match
  const matchShopee1 = dealUrl.match(/-i\.(\d+)\.(\d+)/) || dealUrl.match(/\/product\/(\d+)\/(\d+)/);
  const matchShopee2 = currUrl.match(/-i\.(\d+)\.(\d+)/) || currUrl.match(/\/product\/(\d+)\/(\d+)/);
  if (matchShopee1 && matchShopee2 && matchShopee1[2] === matchShopee2[2]) {
    return true;
  }
  return false;
};

export const DealsListView: React.FC<DealsListProps> = ({ deals, basePrice, currentUrl }) => {
  const validDeals = currentUrl ? (deals || []).filter(d => !isSameUrl(d.url, currentUrl)) : (deals || []);

  if (!validDeals || validDeals.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400 text-xs">
        Chưa tìm thấy deal nào tương thích trên thị trường.
      </div>
    );
  }

  const exactDeals = validDeals.filter(d => d.match_type === 'EXACT_MATCH');
  const otherDeals = validDeals.filter(d => d.match_type !== 'EXACT_MATCH');

  return (
    <div className="px-4 pb-6 space-y-4">
      {/* KHU VỰC 1: ĐÚNG SẢN PHẨM & ĐÚNG BIẾN THỂ */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            Đúng sản phẩm & biến thể ({exactDeals.length})
          </h3>
          <span className="text-[10px] text-emerald-600 font-medium">Đối soát chuẩn</span>
        </div>

        {exactDeals.length > 0 ? (
          <div className="space-y-2.5">
            {exactDeals.map((deal, idx) => (
              <DealCardItem key={`exact-${idx}`} deal={deal} basePrice={basePrice} />
            ))}
          </div>
        ) : (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px] leading-relaxed">
            Chưa tìm thấy nơi bán khác có đúng biến thể này. Dưới đây là các biến thể khác hoặc điểm bán tham khảo.
          </div>
        )}
      </div>

      {/* KHU VỰC 2: BIẾN THỂ KHÁC & THAM KHẢO */}
      {otherDeals.length > 0 && (
        <div className="pt-2 border-t border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Biến thể khác & tham khảo ({otherDeals.length})
            </h3>
            <span className="text-[10px] text-gray-400">Khác size/tập/mẫu</span>
          </div>

          <div className="space-y-2.5">
            {otherDeals.map((deal, idx) => (
              <DealCardItem key={`other-${idx}`} deal={deal} basePrice={basePrice} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};