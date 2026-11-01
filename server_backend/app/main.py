import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.analyze_controller import router as analyze_router
from app.controllers.health_controller import router as health_router
from app.controllers.understand_controller import router as understand_router
from app.controllers.settings_controller import router as settings_router

app = FastAPI(
    title="Smart Price Assistant API",
    description="Backend Agentic AI Pipeline theo chuẩn MVC",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import RedirectResponse

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(understand_router)
app.include_router(settings_router)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)