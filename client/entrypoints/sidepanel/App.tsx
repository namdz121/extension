import React, { useEffect, useState } from 'react';
import '../../assets/style.css';
import { extractPageMetadata } from '../../utils/dom_parser';
import type { AnalyzeResponseDTO, AnalyzeRequestDTO } from '../../models/analyze_dto';
import type { SettingsResponseDTO } from '../../models/settings_dto';

import { ProductHeaderView } from '../../views/ProductHeaderView';
import { AIVerdictView } from '../../views/AIVerdictView';
import { DealsListView } from '../../views/DealsListView';
import { SettingsModal } from '../../views/SettingsModal';
import { Settings, AlertTriangle } from 'lucide-react';

export const App: React.FC = () => {
  const [data, setData] = useState<AnalyzeResponseDTO | null>(null);
  const [currentRequest, setCurrentRequest] = useState<AnalyzeRequestDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Trạng thái modal cấu hình & đồng bộ .env
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [missingKeys, setMissingKeys] = useState<boolean>(false);

  // Kiểm tra trạng thái cấu hình từ .env
  const checkKeyStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/settings');
      if (res.ok) {
        const settingsData: SettingsResponseDTO = await res.json();
        const hasGemini = Boolean(settingsData.has_gemini_key || settingsData.gemini_api_key?.trim());
        const hasTavily = Boolean(settingsData.has_tavily_key || settingsData.tavily_api_key?.trim());
        setMissingKeys(!hasGemini || !hasTavily);
      }
    } catch {
      // Backend có thể chưa chạy, giữ nguyên
    }
  };

  const triggerAnalyze = async () => {
    setLoading(true);
    setErrorMsg(null);

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) {
        throw new Error('Không tìm thấy tab trình duyệt hợp lệ.');
      }

      const url = tab.url || '';
      if (!url || url.startsWith('chrome://') || url.startsWith('about:') || url.startsWith('edge://')) {
        throw new Error('Vui lòng mở một trang web sản phẩm (Shopee, Tiki, Lazada...) để bắt đầu phân tích.');
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
      const res = await fetch('http://127.0.0.1:8080/api/v1/analyze', {
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
      if (err.message?.includes('Failed to fetch')) {
        setErrorMsg('Không thể kết nối đến Backend (http://127.0.0.1:8080). Hãy kiểm tra xem bạn đã khởi động server FastAPI chưa.');
      } else {
        setErrorMsg(err.message || 'Đã xảy ra lỗi khi phân tích.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkKeyStatus();
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
        <div className="spa-nav-actions">
          <button
            onClick={() => setShowSettings(true)}
            className="spa-btn-settings"
            title="Cài đặt & Đồng bộ .env"
            aria-label="Cài đặt"
          >
            <Settings size={14} />
            <span>Cài đặt</span>
          </button>
          <span className="spa-badge-status">Sẵn sàng</span>
        </div>
      </header>

      {/* Cảnh báo nếu chưa cấu hình đủ key trong .env */}
      {missingKeys && (
        <div className="spa-key-warning-banner">
          <div className="spa-key-warning-text">
            <AlertTriangle size={14} />
            <span>Chưa cấu hình API Key trong file .env</span>
          </div>
          <button
            onClick={() => setShowSettings(true)}
            className="spa-key-warning-btn"
          >
            Cấu hình ngay
          </button>
        </div>
      )}

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
            currentUrl={currentRequest?.page_url}
          />
        </>
      )}

      <footer className="spa-footer">
        Dữ liệu được cập nhật và thẩm định tự động bởi AI
      </footer>

      {/* Modal Settings đồng bộ .env */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        onSettingsSaved={() => {
          checkKeyStatus();
          triggerAnalyze();
        }}
      />
    </div>
  );
};

export default App;