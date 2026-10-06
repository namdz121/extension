import React from 'react';
import type { DealCandidate } from '../models/analyze_dto';
import { DealCardItem } from './DealCardItem';

interface DealsListProps {
  deals: DealCandidate[];
  basePrice?: number;
}

export const DealsListView: React.FC<DealsListProps> = ({ deals, basePrice }) => {
  if (!deals || deals.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400 text-xs">
        Chưa tìm thấy deal nào tương thích trên thị trường.
      </div>
    );
  }

  return (
    <div className="px-4 pb-6">
      <div className="flex items-center justify-between mb-2.5">
        <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
          Điểm bán khác ({deals.length})
        </h3>
        <span className="text-[10px] text-gray-400">Sắp xếp theo độ tin cậy</span>
      </div>

      <div className="space-y-2.5">
        {deals.map((deal, idx) => (
          <DealCardItem key={idx} deal={deal} basePrice={basePrice} />
        ))}
      </div>
    </div>
  );
};