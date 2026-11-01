import React, { useEffect, useState } from 'react';
import {
  Settings,
  Key,
  Save,
  RefreshCw,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Cpu,
  FileCode,
  X,
  Check,
  Server
} from 'lucide-react';
import type {
  SettingsResponseDTO,
  AllowedModel,
  TestKeyResponseDTO,
  SaveSettingsResponseDTO
} from '../models/settings_dto';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSettingsSaved?: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSettingsSaved
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [geminiKey, setGeminiKey] = useState<string>('');
  const [tavilyKey, setTavilyKey] = useState<string>('');
  const [geminiModel, setGeminiModel] = useState<string>('gemini-3.1-flash-lite');
  const [allowedModels, setAllowedModels] = useState<AllowedModel[]>([]);
  const [envPath, setEnvPath] = useState<string>('');

  const [showGemini, setShowGemini] = useState<boolean>(false);
  const [showTavily, setShowTavily] = useState<boolean>(false);

  const [testingGemini, setTestingGemini] = useState<boolean>(false);
  const [geminiTestResult, setGeminiTestResult] = useState<TestKeyResponseDTO | null>(null);

  const [testingTavily, setTestingTavily] = useState<boolean>(false);
  const [tavilyTestResult, setTavilyTestResult] = useState<TestKeyResponseDTO | null>(null);

  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [saveErrorMsg, setSaveErrorMsg] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);

  // Tải cài đặt từ backend / .env
  const fetchSettings = async () => {
    setLoading(true);
    setSaveErrorMsg(null);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/settings');
      if (!res.ok) {
        throw new Error(`Mã lỗi backend: ${res.status}`);
      }
      const data: SettingsResponseDTO = await res.json();
      setGeminiKey(data.gemini_api_key || '');
      setTavilyKey(data.tavily_api_key || '');
      setGeminiModel(data.gemini_model || 'gemini-3.1-flash-lite');
      setAllowedModels(data.allowed_models || []);
      setEnvPath(data.env_file_path || '');
      setBackendOnline(true);
    } catch (err: any) {
      console.error(err);
      setBackendOnline(false);
      setSaveErrorMsg(
        'Không thể kết nối đến Backend (http://127.0.0.1:8080). Hãy đảm bảo server đã chạy.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      setGeminiTestResult(null);
      setTavilyTestResult(null);
      setSaveSuccessMsg(null);
    }
  }, [isOpen]);

  // Kiểm tra cảnh báo nhầm key
  const isGeminiMisconfigured = geminiKey.trim().startsWith('tvly-');
  const isTavilyMisconfigured =
    tavilyKey.trim().startsWith('AIza') || tavilyKey.trim().startsWith('AQ.');

  // Test Gemini Key
  const handleTestGemini = async () => {
    const key = geminiKey.trim();
    if (!key) {
      setGeminiTestResult({ success: false, message: 'Vui lòng nhập Gemini API Key để kiểm tra.' });
      return;
    }
    setTestingGemini(true);
    setGeminiTestResult(null);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/settings/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service: 'gemini',
          api_key: key,
          gemini_model: geminiModel
        })
      });
      const data: TestKeyResponseDTO = await res.json();
      setGeminiTestResult(data);
    } catch (err: any) {
      setGeminiTestResult({
        success: false,
        message: 'Lỗi kết nối tới Backend khi test Gemini.'
      });
    } finally {
      setTestingGemini(false);
    }
  };

  // Test Tavily Key
  const handleTestTavily = async () => {
    const key = tavilyKey.trim();
    if (!key) {
      setTavilyTestResult({ success: false, message: 'Vui lòng nhập Tavily API Key để kiểm tra.' });
      return;
    }
    setTestingTavily(true);
    setTavilyTestResult(null);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/settings/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service: 'tavily',
          api_key: key
        })
      });
      const data: TestKeyResponseDTO = await res.json();
      setTavilyTestResult(data);
    } catch (err: any) {
      setTavilyTestResult({
        success: false,
        message: 'Lỗi kết nối tới Backend khi test Tavily.'
      });
    } finally {
      setTestingTavily(false);
    }
  };

  // Lưu cài đặt & ghi đè file .env
  const handleSave = async () => {
    setSaveErrorMsg(null);
    setSaveSuccessMsg(null);

    if (isGeminiMisconfigured) {
      setSaveErrorMsg('Khóa Gemini đang chứa key của Tavily (tvly-). Vui lòng kiểm tra lại!');
      return;
    }
    if (isTavilyMisconfigured) {
      setSaveErrorMsg('Khóa Tavily đang chứa key của Gemini (AIza/AQ). Vui lòng kiểm tra lại!');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gemini_api_key: geminiKey.trim(),
          tavily_api_key: tavilyKey.trim(),
          gemini_model: geminiModel
        })
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Không thể lưu cài đặt.');
      }

      const data: SaveSettingsResponseDTO = await res.json();
      setSaveSuccessMsg(data.message || 'Đã lưu và đồng bộ thành công vào file .env!');
      if (onSettingsSaved) {
        onSettingsSaved();
      }

      // Tự động tắt thông báo sau 4 giây
      setTimeout(() => {
        setSaveSuccessMsg(null);
      }, 4000);
    } catch (err: any) {
      setSaveErrorMsg(err.message || 'Đã xảy ra lỗi khi lưu cài đặt.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="spa-modal-backdrop">
      <div className="spa-settings-sheet">
        {/* Header */}
        <div className="spa-settings-header">
          <div className="spa-settings-title-row">
            <div className="spa-settings-icon-wrap">
              <Settings size={18} className="spa-settings-icon" />
            </div>
            <div>
              <h2 className="spa-settings-title">Cấu hình & Đồng bộ .env</h2>
              <p className="spa-settings-subtitle">Quản lý API Key & Đồng bộ thời gian thực với file .env</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="spa-btn-close-modal"
            title="Đóng"
            aria-label="Đóng"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="spa-settings-body">
          {/* Status info bar */}
          <div className="spa-env-info-card">
            <div className="spa-env-info-row">
              <div className="spa-env-info-item">
                <FileCode size={14} className="text-slate-500" />
                <span className="spa-env-label">Vị trí file:</span>
                <span className="spa-env-badge" title={envPath}>
                  {envPath ? envPath.split(/[/\\]/).slice(-2).join('/') : 'server_backend/.env'}
                </span>
              </div>
              <div className="spa-env-info-item">
                <Server size={14} className="text-slate-500" />
                <span
                  className={`spa-status-pill ${
                    backendOnline ? 'spa-status-online' : 'spa-status-offline'
                  }`}
                >
                  <span className="spa-status-dot"></span>
                  {backendOnline ? 'Backend Online' : 'Backend Offline'}
                </span>
              </div>
            </div>

            <div className="spa-env-summary-row">
              <span className="spa-chip-indicator">
                Gemini:{' '}
                {geminiKey.trim() ? (
                  <strong className="text-emerald-600">Đã nạp ({geminiKey.slice(0, 4)}...{geminiKey.slice(-4)})</strong>
                ) : (
                  <strong className="text-amber-600">Chưa có key</strong>
                )}
              </span>
              <span className="spa-chip-indicator">
                Tavily:{' '}
                {tavilyKey.trim() ? (
                  <strong className="text-emerald-600">Đã nạp ({tavilyKey.slice(0, 4)}...{tavilyKey.slice(-4)})</strong>
                ) : (
                  <strong className="text-amber-600">Chưa có key</strong>
                )}
              </span>
            </div>
          </div>

          {/* Success / Error Alerts */}
          {saveSuccessMsg && (
            <div className="spa-alert spa-alert-success">
              <CheckCircle2 size={16} />
              <span>{saveSuccessMsg}</span>
            </div>
          )}

          {saveErrorMsg && (
            <div className="spa-alert spa-alert-error">
              <AlertTriangle size={16} />
              <span>{saveErrorMsg}</span>
            </div>
          )}

          {/* Section 1: Gemini API Key */}
          <div className="spa-field-group">
            <div className="spa-field-header">
              <label className="spa-field-label">
                <Key size={14} className="spa-field-label-icon text-indigo-600" />
                Google Gemini API Key
              </label>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="spa-field-link"
              >
                Lấy key miễn phí <ExternalLink size={11} />
              </a>
            </div>

            <div className="spa-input-group">
              <input
                type={showGemini ? 'text' : 'password'}
                value={geminiKey}
                onChange={(e) => {
                  setGeminiKey(e.target.value);
                  setGeminiTestResult(null);
                }}
                placeholder="Dán khóa Gemini API (AIza... hoặc AQ....)"
                className={`spa-input ${isGeminiMisconfigured ? 'spa-input-invalid' : ''}`}
              />
              <button
                type="button"
                onClick={() => setShowGemini(!showGemini)}
                className="spa-input-btn"
                title={showGemini ? 'Ẩn key' : 'Hiện key'}
              >
                {showGemini ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {isGeminiMisconfigured && (
              <div className="spa-input-warning">
                <AlertTriangle size={13} />
                <span>Cảnh báo: Khóa này có tiền tố tvly- của Tavily, không phải Gemini!</span>
              </div>
            )}

            <div className="spa-field-actions">
              <button
                type="button"
                onClick={handleTestGemini}
                disabled={testingGemini || !geminiKey.trim()}
                className="spa-btn-test"
              >
                {testingGemini ? (
                  <>
                    <RefreshCw size={12} className="spa-spinner" /> Đang kiểm tra...
                  </>
                ) : (
                  <>Kiểm tra kết nối Gemini</>
                )}
              </button>

              {geminiTestResult && (
                <span
                  className={`spa-test-badge ${
                    geminiTestResult.success ? 'spa-test-ok' : 'spa-test-fail'
                  }`}
                >
                  {geminiTestResult.success ? <Check size={12} /> : <XCircle size={12} />}
                  {geminiTestResult.message}
                </span>
              )}
            </div>
          </div>

          {/* Section 2: Tavily Search API Key */}
          <div className="spa-field-group">
            <div className="spa-field-header">
              <label className="spa-field-label">
                <Key size={14} className="spa-field-label-icon text-sky-600" />
                Tavily Search API Key
              </label>
              <a
                href="https://app.tavily.com"
                target="_blank"
                rel="noreferrer"
                className="spa-field-link"
              >
                Lấy key tại Tavily <ExternalLink size={11} />
              </a>
            </div>

            <div className="spa-input-group">
              <input
                type={showTavily ? 'text' : 'password'}
                value={tavilyKey}
                onChange={(e) => {
                  setTavilyKey(e.target.value);
                  setTavilyTestResult(null);
                }}
                placeholder="Dán khóa Tavily API (bắt đầu bằng tvly-...)"
                className={`spa-input ${isTavilyMisconfigured ? 'spa-input-invalid' : ''}`}
              />
              <button
                type="button"
                onClick={() => setShowTavily(!showTavily)}
                className="spa-input-btn"
                title={showTavily ? 'Ẩn key' : 'Hiện key'}
              >
                {showTavily ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {isTavilyMisconfigured && (
              <div className="spa-input-warning">
                <AlertTriangle size={13} />
                <span>Cảnh báo: Khóa này là của Google Gemini, không phải Tavily!</span>
              </div>
            )}

            <div className="spa-field-actions">
              <button
                type="button"
                onClick={handleTestTavily}
                disabled={testingTavily || !tavilyKey.trim()}
                className="spa-btn-test"
              >
                {testingTavily ? (
                  <>
                    <RefreshCw size={12} className="spa-spinner" /> Đang kiểm tra...
                  </>
                ) : (
                  <>Kiểm tra kết nối Tavily</>
                )}
              </button>

              {tavilyTestResult && (
                <span
                  className={`spa-test-badge ${
                    tavilyTestResult.success ? 'spa-test-ok' : 'spa-test-fail'
                  }`}
                >
                  {tavilyTestResult.success ? <Check size={12} /> : <XCircle size={12} />}
                  {tavilyTestResult.message}
                </span>
              )}
            </div>
          </div>

          {/* Section 3: Gemini Model Selection */}
          <div className="spa-field-group">
            <div className="spa-field-header">
              <label className="spa-field-label">
                <Cpu size={14} className="spa-field-label-icon text-violet-600" />
                Mô hình Gemini LLM
              </label>
              <span className="spa-field-hint">Chọn model xử lý thẩm định</span>
            </div>

            <div className="spa-model-list">
              {(allowedModels.length > 0
                ? allowedModels
                : [
                    {
                      id: 'gemini-3.1-flash-lite',
                      name: 'Gemini 3.1 Flash Lite (Siêu nhanh, tiết kiệm)',
                      desc: 'Tốc độ phản hồi cực nhanh, tối ưu chi phí token'
                    },
                    {
                      id: 'gemini-3.5-flash-lite',
                      name: 'Gemini 3.5 Flash Lite (Cân bằng, chính xác)',
                      desc: 'Độ chính xác cao hơn cho bóc tách thực thể phức tạp'
                    },
                    {
                      id: 'gemini-2.0-flash',
                      name: 'Gemini 2.0 Flash (Chuẩn Google GenAI)',
                      desc: 'Khả năng suy luận đa nhiệm tốt, tính ổn định cao'
                    }
                  ]
              ).map((m) => {
                const isSelected = geminiModel === m.id;
                return (
                  <div
                    key={m.id}
                    onClick={() => setGeminiModel(m.id)}
                    className={`spa-model-option ${isSelected ? 'spa-model-selected' : ''}`}
                  >
                    <div className="spa-model-radio">
                      <div className={`spa-radio-circle ${isSelected ? 'spa-radio-active' : ''}`} />
                    </div>
                    <div className="spa-model-info">
                      <div className="spa-model-name">{m.name}</div>
                      {m.desc && <div className="spa-model-desc">{m.desc}</div>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="spa-settings-footer">
          <button
            type="button"
            onClick={fetchSettings}
            disabled={loading || saving}
            className="spa-btn-secondary"
            title="Tải lại giá trị mới nhất trực tiếp từ file .env"
          >
            <RefreshCw size={14} className={loading ? 'spa-spinner' : ''} />
            <span>Tải lại từ .env</span>
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={saving || loading || !backendOnline}
            className="spa-btn-primary"
          >
            {saving ? (
              <>
                <RefreshCw size={14} className="spa-spinner" />
                <span>Đang đồng bộ...</span>
              </>
            ) : (
              <>
                <Save size={14} />
                <span>Lưu & Đồng bộ vào .env</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
