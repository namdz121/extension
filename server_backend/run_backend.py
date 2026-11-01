import os
import sys
import subprocess
from pathlib import Path

# Cấu hình UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Xác định thư mục server_backend
CURRENT_DIR = Path(__file__).resolve().parent
if (CURRENT_DIR / "app").is_dir():
    SERVER_DIR = CURRENT_DIR
elif (CURRENT_DIR / "server_backend").is_dir():
    SERVER_DIR = CURRENT_DIR / "server_backend"
else:
    SERVER_DIR = CURRENT_DIR

VENV_PYTHON = SERVER_DIR / "venv" / "Scripts" / "python.exe"

def ensure_venv():
    """Tự động kiểm tra và chuyển sang chạy bằng Python trong venv"""
    if VENV_PYTHON.exists():
        current_python = Path(sys.executable).resolve()
        target_python = VENV_PYTHON.resolve()
        
        # Nếu chưa chạy bằng Python của venv, gọi lại script bằng venv Python
        if current_python != target_python:
            print(f"[Launcher] Chuyen sang moi truong ao: {target_python}")
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                result = subprocess.run(
                    [str(target_python), str(Path(__file__).resolve())] + sys.argv[1:],
                    cwd=str(SERVER_DIR),
                    env=env
                )
                sys.exit(result.returncode)
            except KeyboardInterrupt:
                sys.exit(0)
    else:
        print(f"[Launcher] Canh bao: Khong tim thay venv tai {VENV_PYTHON}, chay voi: {sys.executable}")

def run():
    # Thêm SERVER_DIR vào sys.path để import app.main
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))
    
    os.chdir(SERVER_DIR)
    
    from app.config.settings import settings
    port = settings.PORT or 8080
    host = settings.HOST if settings.HOST != "0.0.0.0" else "127.0.0.1"
    
    import uvicorn
    print("\n" + "="*50)
    print("[*] Dang khoi dong Backend Smart Price Assistant...")
    print(f"[*] URL:  http://127.0.0.1:{port}")
    print(f"[*] Docs: http://127.0.0.1:{port}/docs")
    print("="*50 + "\n")
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)

if __name__ == "__main__":
    ensure_venv()
    run()
