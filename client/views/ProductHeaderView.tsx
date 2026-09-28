import React from 'react';
import type { CanonicalEntity } from '../models/analyze_dto';

export const ProductHeaderView: React.FC<{ entity: CanonicalEntity }> = ({ entity }) => {
  return (
    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', marginBottom: '12px', border: '1px solid #e2e8f0' }}>
      <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
        {entity.category} {entity.brand ? `• ${entity.brand}` : ''}
      </div>
      <div style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: '4px 0' }}>
        {entity.model || 'Sản phẩm không rõ tên'}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
        {Object.entries(entity.key_specs).map(([key, value]) => (
          <span key={key} style={{ fontSize: '11px', background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>
            {key}: {String(value)}
          </span>
        ))}
      </div>
    </div>
  );
};