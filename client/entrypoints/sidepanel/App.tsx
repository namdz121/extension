import React, { useState } from 'react';
import type { AnalyzeRequestDTO, AnalyzeResponseDTO } from '../../models/analyze_dto';
import { ProductHeaderView } from '../../views/ProductHeaderView';
import { AIVerdictView } from '../../views/AIVerdictView';
import { DealCardItem } from '../../views/DealCardItem';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalyzeResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScanAndAnalyze = async () => {
    setLoading(true);
    setError(null);

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) {
        throw new Error('Không thể kết nối với tab trình duyệt');
      }

      chrome.tabs.sendMessage(tab.id, { action: 'EXTRACT_PAGE_DATA' }, async (domPayload: AnalyzeRequestDTO) => {
        if (!domPayload) {
          setError('Không thể đọc dữ liệu trang này (Hãy thử refresh lại trang web).');
          setLoading(false);
          return;
        }

        try {
          const res = await fetch('http://127.0.0.1:8000/api/v1/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(domPayload)
          });

          if (!res.ok) {
            throw new Error(`Server phản hồi lỗi: ${res.status}`);
          }

          const result: AnalyzeResponseDTO = await res.json();
          setData(result);
        } catch (fetchErr: any) {
          setError('Lỗi kết nối tới Backend FastAPI (127.0.0.1:8000)');
        } finally {
          setLoading(false);
        }
      });
    } catch (err: any) {
      setError(err.message || 'Lỗi không xác định');
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '14px', fontFamily: 'system-ui, sans-serif', width: '100%', boxSizing: 'border-box' }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', color: '#0f172a' }}>
        Smart Price Assistant
      </h3>

      <button
        onClick={handleScanAndAnalyze}
        disabled={loading}
        style={{
          width: '100%',
          padding: '10px',
          background: loading ? '#94a3b8' : '#2563eb',
          color: '#fff',
          border: 'none',
          borderRadius: '6px',
          fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
          marginBottom: '14px'
        }}
      >
        {loading ? 'AI đang phân tích thị trường...' : '🔍 So sánh giá trang này'}
      </button>

      {error && (
        <div style={{ background: '#fef2f2', color: '#b91c1c', padding: '8px', borderRadius: '6px', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {data && (
        <div>
          <ProductHeaderView entity={data.canonical_entity} />
          <AIVerdictView verdict={data.ai_verdict} />

          <div style={{ fontSize: '13px', fontWeight: 700, margin: '12px 0 8px 0', color: '#334155' }}>
            Điểm bán đối thủ ({data.deals.length}):
          </div>
          {data.deals.map((deal, idx) => (
            <DealCardItem key={idx} deal={deal} />
          ))}
        </div>
      )}
    </div>
  );
}