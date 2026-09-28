import React from 'react';
import type { DealCandidate } from '../models/analyze_dto';

export const DealCardItem: React.FC<{ deal: DealCandidate }> = ({ deal }) => {
  const badgeColor = deal.match_type === 'EXACT_MATCH' ? '#16a34a' : '#ea580c';

  return (
    <div style={{ padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px', marginBottom: '8px', background: '#fff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, color: badgeColor, background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
          {deal.match_type} ({deal.composite_score.toFixed(0)}%)
        </span>
        <span style={{ fontSize: '13px', fontWeight: 700, color: '#dc2626' }}>
          {deal.price > 0 ? `${deal.price.toLocaleString('vi-VN')} đ` : 'Xem giá tại web'}
        </span>
      </div>
      <div style={{ fontSize: '12px', fontWeight: 500, margin: '6px 0', color: '#334155' }}>
        {deal.title}
      </div>
      <a href={deal.url} target="_blank" rel="noreferrer" style={{ fontSize: '11px', color: '#2563eb', textDecoration: 'none', fontWeight: 600 }}>
        Mở trang bán đối thủ ↗
      </a>
    </div>
  );
};