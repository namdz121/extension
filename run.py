import os
import sys
import time
import subprocess
import threading
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

BASE_DIR = Path(__file__).resolve().parent
SERVER_DIR = BASE_DIR / "server_backend"
CLIENT_DIR = BASE_DIR / "client"

VENV_PYTHON = SERVER_DIR / "venv" / "Scripts" / "python.exe"
RUN_BACKEND = SERVER_DIR / "run_backend.py"

def stream_output(pipe, prefix):
    """Đọc và in output theo thời gian thực"""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                print(f"[{prefix}] {line.rstrip()}")
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass

def main():
    print("=" * 60)
    print("🚀 KHỞI ĐỘNG HỆ THỐNG SMART PRICE ASSISTANT (BE & FE)")
    print("=" * 60)

    python_exec = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    if not VENV_PYTHON.exists():
        print(f"[Cảnh báo] Không tìm thấy venv tại {VENV_PYTHON}, dùng: {python_exec}")

    # Thiết lập biến môi trường
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PORT"] = "8080"

    print("\n🔹 [1/2] Đang khởi động Backend FastAPI (Port 8080)...")
    backend_proc = subprocess.Popen(
        [python_exec, "-u", str(RUN_BACKEND)],
        cwd=str(SERVER_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    t_be = threading.Thread(target=stream_output, args=(backend_proc.stdout, "BACKEND"), daemon=True)
    t_be.start()

    time.sleep(2)

    print("\n🔹 [2/2] Đang khởi động Frontend Extension (WXT Dev Server)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        f"{npm_cmd} run dev",
        cwd=str(CLIENT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        shell=True
    )

    t_fe = threading.Thread(target=stream_output, args=(frontend_proc.stdout, "CLIENT "), daemon=True)
    t_fe.start()

    print("\n" + "=" * 60)
    print("✅ ĐÃ KHỞI ĐỘNG CẢ 2 TIẾN TRÌNH:")
    print("  - Backend API:  http://127.0.0.1:8080")
    print("  - Swagger Docs: http://127.0.0.1:8080/docs")
    print("  - Extension:    Đang nạp vào trình duyệt...")
    print("  (Nhấn Ctrl + C để dừng cả Backend và Frontend)")
    print("=" * 60 + "\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("\n[Lưu ý] Tiến trình Backend đã dừng.")
                break
            if frontend_proc.poll() is not None:
                print("\n[Lưu ý] Tiến trình Frontend đã dừng.")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Đang dừng toàn bộ dịch vụ...")
    finally:
        for p in [backend_proc, frontend_proc]:
            try:
                p.terminate()
            except Exception:
                pass
        print("✔️ Đã đóng tất cả tiến trình.")

if __name__ == "__main__":
    main()
