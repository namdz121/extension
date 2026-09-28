import React from 'react';

export const AIVerdictView: React.FC<{ verdict: string }> = ({ verdict }) => {
  return (
    <div style={{ background: '#0c0303', borderLeft: '4px solid #3b82f6', padding: '10px', borderRadius: '4px', marginBottom: '12px' }}>
      <div style={{ fontSize: '12px', fontWeight: 700, color: '#1d4ed8', marginBottom: '4px' }}>
        💡 Nhận định từ AI:
      </div>
      <div style={{ fontSize: '12px', color: '#1e293b', lineHeight: 1.5 }}>
        {verdict}
      </div>
    </div>
  );
};