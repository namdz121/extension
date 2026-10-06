import React, { useEffect, useState } from 'react';
import '../../assets/style.css';
import { extractPageMetadata } from '../../utils/dom_parser';
import type { AnalyzeResponseDTO, AnalyzeRequestDTO } from '../../models/analyze_dto';

import { ProductHeaderView } from '../../views/ProductHeaderView';
import { AIVerdictView } from '../../views/AIVerdictView';
import { DealsListView } from '../../views/DealsListView';

export const App: React.FC = () => {
  const [data, setData] = useState<AnalyzeResponseDTO | null>(null);
  const [currentRequest, setCurrentRequest] = useState<AnalyzeRequestDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const triggerAnalyze = async () => {
    setLoading(true);
    setErrorMsg(null);

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) {
        throw new Error('Không tìm thấy tab trình duyệt hợp lệ.');
      }

      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractPageMetadata
      });

      const extracted = results?.[0]?.result;
      if (!extracted || !extracted.raw_title) {
        throw new Error('Không tìm thấy thông tin sản phẩm trên trang hiện tại. Hãy cuộn xem tiêu đề sản phẩm.');
      }

      setCurrentRequest(extracted);

      // Gọi Backend FastAPI
      const res = await fetch('http://127.0.0.1:8000/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(extracted)
      });

      if (!res.ok) {
        throw new Error(`Máy chủ backend phản hồi lỗi: ${res.status}`);
      }

      const resJson: AnalyzeResponseDTO = await res.json();
      setData(resJson);
    } catch (err: any) {
      console.error(err);
      if (err.message.includes('Failed to fetch')) {
        setErrorMsg('Không thể kết nối đến Backend (http://127.0.0.1:8000). Hãy kiểm tra xem bạn đã khởi động server FastAPI chưa.');
      } else {
        setErrorMsg(err.message || 'Đã xảy ra lỗi khi phân tích.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    triggerAnalyze();
  }, []);

  return (
    <div className="spa-app">
      {/* Top Navbar */}
      <header className="spa-navbar">
        <div className="spa-brand">
          <span>🛒</span>
          <span>Smart Price Assistant</span>
        </div>
        <span className="spa-badge-status">Sẵn sàng</span>
      </header>

      {/* Error state */}
      {errorMsg && (
        <div className="spa-error-box">
          <div className="spa-error-title">⚠️ Có lỗi xảy ra</div>
          <div className="spa-error-desc">{errorMsg}</div>
          <button onClick={triggerAnalyze} className="spa-btn-retry">
            Thử lại ngay
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && !data && (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748b' }}>
          <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
          <div style={{ fontWeight: 600, fontSize: '15px', color: '#1e293b' }}>Đang đối soát giá thị trường...</div>
          <div style={{ fontSize: '13px', marginTop: '4px' }}>Gemini AI & Tavily đang quét deal</div>
        </div>
      )}

      {/* Data display */}
      {data && (
        <>
          <ProductHeaderView
            entity={data.canonical_entity}
            rawPrice={currentRequest?.raw_price}
            imageUrl={currentRequest?.image_data}
            onRefresh={triggerAnalyze}
            isLoading={loading}
          />

          <AIVerdictView verdict={data.ai_verdict} />

          <DealsListView
            deals={data.deals}
            basePrice={data.canonical_entity.normalized_price || currentRequest?.raw_price}
          />
        </>
      )}

      <footer className="spa-footer">
        Dữ liệu được cập nhật và thẩm định tự động bởi AI
      </footer>
    </div>
  );
};

export default App;