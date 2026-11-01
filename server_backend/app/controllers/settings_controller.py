import os
import re
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.config.settings import settings, ENV_FILE_PATH
from google import genai
from tavily import TavilyClient

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

class SettingsDTO(BaseModel):
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"

class TestKeyDTO(BaseModel):
    service: str  # "gemini" hoặc "tavily"
    api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"

ALLOWED_MODELS = [
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite (Siêu nhanh, tiết kiệm)", "desc": "Tốc độ phản hồi cực nhanh, tối ưu chi phí token"},
    {"id": "gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite (Cân bằng, chính xác)", "desc": "Độ chính xác cao hơn cho bóc tách thực thể phức tạp"},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Chuẩn Google GenAI)", "desc": "Khả năng suy luận đa nhiệm tốt, tính ổn định cao"}
]

def read_env_file() -> dict:
    """Đọc trực tiếp các biến môi trường từ file .env để đảm bảo luôn bám sát file trên ổ đĩa"""
    env_path = Path(ENV_FILE_PATH)
    data = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    k, v = stripped.split("=", 1)
                    data[k.strip()] = v.strip().strip("'\"")
    return data

def update_env_file(gemini_key: str, tavily_key: str, gemini_model: str):
    """Cập nhật an toàn file .env mà không làm mất các biến khác (HOST, PORT, CACHE_TTL...)"""
    env_path = Path(ENV_FILE_PATH)
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    keys_set = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={gemini_key}\n")
            keys_set.add("GEMINI_API_KEY")
        elif stripped.startswith("TAVILY_API_KEY="):
            new_lines.append(f"TAVILY_API_KEY={tavily_key}\n")
            keys_set.add("TAVILY_API_KEY")
        elif stripped.startswith("GEMINI_MODEL="):
            new_lines.append(f"GEMINI_MODEL={gemini_model}\n")
            keys_set.add("GEMINI_MODEL")
        else:
            new_lines.append(line)

    if "GEMINI_API_KEY" not in keys_set:
        new_lines.append(f"GEMINI_API_KEY={gemini_key}\n")
    if "TAVILY_API_KEY" not in keys_set:
        new_lines.append(f"TAVILY_API_KEY={tavily_key}\n")
    if "GEMINI_MODEL" not in keys_set:
        new_lines.append(f"GEMINI_MODEL={gemini_model}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def _reload_all_services():
    """Tải lại thông tin khóa API và mô hình cho toàn bộ các service trong backend"""
    # Pipeline truyền thống
    try:
        from app.services.normalizer_service import normalizer_service
        if hasattr(normalizer_service, "reload_credentials"):
            normalizer_service.reload_credentials()
    except Exception as e:
        print(f"[Settings] Reload normalizer_service error: {e}")

    try:
        from app.services.judge_service import judge_service
        if hasattr(judge_service, "reload_credentials"):
            judge_service.reload_credentials()
    except Exception as e:
        print(f"[Settings] Reload judge_service error: {e}")

    try:
        from app.services.search_service import search_service
        if hasattr(search_service, "reload_credentials"):
            search_service.reload_credentials()
    except Exception as e:
        print(f"[Settings] Reload search_service error: {e}")

    # Pipeline mới (understand_controller)
    try:
        from app.services.extractor_service import extractor_service
        if hasattr(extractor_service, "reload_credentials"):
            extractor_service.reload_credentials()
    except Exception as e:
        print(f"[Settings] Reload extractor_service error: {e}")

    try:
        from app.services.verifier_service import verifier_service
        if hasattr(verifier_service, "reload_credentials"):
            verifier_service.reload_credentials()
    except Exception as e:
        print(f"[Settings] Reload verifier_service error: {e}")

    try:
        from app.services.multi_search_service import multi_search_service
        if hasattr(multi_search_service, "reload_credentials"):
            multi_search_service.reload_credentials()
    except Exception as e:
        print(f"[Settings] Reload multi_search_service error: {e}")

@router.get("")
async def get_settings():
    """Lấy cấu hình hiện tại từ file .env và đồng bộ với runtime settings"""
    disk_data = read_env_file()
    
    # Ưu tiên giá trị đọc được từ file .env nếu có, fallback về runtime settings
    gemini_key = disk_data.get("GEMINI_API_KEY", settings.GEMINI_API_KEY or "")
    tavily_key = disk_data.get("TAVILY_API_KEY", settings.TAVILY_API_KEY or "")
    gemini_model = disk_data.get("GEMINI_MODEL", getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite"))

    # Nếu file .env bị thay đổi bên ngoài (ví dụ gõ tay trong IDE), đồng bộ ngay vào runtime
    if (gemini_key != settings.GEMINI_API_KEY or 
        tavily_key != settings.TAVILY_API_KEY or 
        gemini_model != getattr(settings, "GEMINI_MODEL", "")):
        settings.GEMINI_API_KEY = gemini_key
        settings.TAVILY_API_KEY = tavily_key
        settings.GEMINI_MODEL = gemini_model
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["TAVILY_API_KEY"] = tavily_key
        os.environ["GEMINI_MODEL"] = gemini_model
        _reload_all_services()

    return {
        "gemini_api_key": gemini_key,
        "tavily_api_key": tavily_key,
        "gemini_model": gemini_model,
        "has_gemini_key": bool(gemini_key.strip()),
        "has_tavily_key": bool(tavily_key.strip()),
        "env_file_path": str(ENV_FILE_PATH),
        "allowed_models": ALLOWED_MODELS
    }

@router.post("")
async def save_settings(dto: SettingsDTO):
    """Lưu và đồng bộ cấu hình vào file .env và runtime"""
    clean_gemini = dto.gemini_api_key.strip()
    clean_tavily = dto.tavily_api_key.strip()
    clean_model = dto.gemini_model.strip() or "gemini-3.1-flash-lite"

    # Kiểm tra tránh nhầm lẫn giữa key Tavily và Gemini
    if clean_gemini.startswith("tvly-"):
        raise HTTPException(
            status_code=400,
            detail="Phát hiện nhầm lẫn: Bạn đang điền API Key của Tavily (bắt đầu bằng tvly-) vào ô Gemini!"
        )
    if clean_tavily.startswith("AIza") or clean_tavily.startswith("AQ."):
        raise HTTPException(
            status_code=400,
            detail="Phát hiện nhầm lẫn: Bạn đang điền API Key của Google Gemini vào ô Tavily!"
        )

    # Cập nhật runtime settings & biến môi trường tiến trình
    settings.GEMINI_API_KEY = clean_gemini
    settings.TAVILY_API_KEY = clean_tavily
    settings.GEMINI_MODEL = clean_model
    os.environ["GEMINI_API_KEY"] = clean_gemini
    os.environ["TAVILY_API_KEY"] = clean_tavily
    os.environ["GEMINI_MODEL"] = clean_model

    # Ghi đè vào file .env trên ổ đĩa
    update_env_file(clean_gemini, clean_tavily, clean_model)

    # Tái tạo client cho tất cả services
    _reload_all_services()

    return {
        "status": "success",
        "message": "Đã lưu và đồng bộ thành công vào file .env!",
        "settings": {
            "gemini_api_key": clean_gemini,
            "tavily_api_key": clean_tavily,
            "gemini_model": clean_model
        }
    }

@router.post("/test")
async def test_api_key(dto: TestKeyDTO):
    """Kiểm tra tính hợp lệ của API Key trước khi người dùng lưu"""
    service = dto.service.lower()
    key = dto.api_key.strip()

    if not key:
        return {"success": False, "message": "API Key không được để trống."}

    if service == "gemini":
        if key.startswith("tvly-"):
            return {
                "success": False,
                "message": "Đây là key của Tavily, không phải của Google Gemini!"
            }
        try:
            client = genai.Client(api_key=key)
            test_model = dto.gemini_model or "gemini-3.1-flash-lite"
            resp = client.models.generate_content(
                model=test_model,
                contents="Ping test! Respond with: OK"
            )
            return {
                "success": True,
                "message": f"Kết nối Google Gemini ({test_model}) thành công!"
            }
        except Exception as e:
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                err_str = "Khóa Gemini API không hợp lệ hoặc đã hết hạn."
            elif "RESOURCE_EXHAUSTED" in err_str:
                err_str = "Hạn mức (Quota) của khóa Gemini này đã tạm thời cạn kiệt."
            return {"success": False, "message": f"Lỗi Gemini: {err_str}"}

    elif service == "tavily":
        if key.startswith("AIza") or key.startswith("AQ."):
            return {
                "success": False,
                "message": "Đây là key của Google Gemini, không phải của Tavily!"
            }
        try:
            client = TavilyClient(api_key=key)
            client.search(query="iPhone 16", max_results=1)
            return {"success": True, "message": "Kết nối Tavily Search API thành công!"}
        except Exception as e:
            err_str = str(e)
            if "unauthorized" in err_str.lower() or "invalid api key" in err_str.lower():
                err_str = "Khóa Tavily API không hợp lệ hoặc bị vô hiệu hóa."
            return {"success": False, "message": f"Lỗi Tavily: {err_str}"}

    return {"success": False, "message": "Dịch vụ không hợp lệ."}
