from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.analyze_controller import router as analyze_router
from app.controllers.health_controller import router as health_router

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

app.include_router(health_router)
app.include_router(analyze_router)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)