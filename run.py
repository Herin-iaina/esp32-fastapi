# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from models.login import create_user
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import auth, system, parameter, sensor_values
from pathlib import Path

from core.config import settings
from core.logging import logger

docs_kwargs = {}
if not settings.enable_docs:
    docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.admin_username and settings.admin_password:
        logger.info(f"Checking for admin user: {settings.admin_username}")
        create_user(settings.admin_username, settings.admin_password)
    
    yield

app = FastAPI(
    title=settings.app_name,
    description="API REST pour système de surveillance des capteurs ESP32",
    version="2.0.0",
    lifespan=lifespan,
    **docs_kwargs
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Middleware CORS - Permettre le frontend séparé
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:5173", "http://localhost:3000", "localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers API
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(sensor_values.router, prefix="/api", tags=["Capteurs"])
app.include_router(system.router, prefix="/api", tags=["Système"])
app.include_router(parameter.router, prefix="/api", tags=["Paramètres"])

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Endpoint de vérification de santé"""
    return {"status": "ok", "version": "2.0.0"}

# Servir le frontend en production
frontend_dist = Path(__file__).parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets", html=False), name="assets")
    
    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str = ""):
        """Servir l'application React (SPA)"""
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting %s on http://127.0.0.1:8000", settings.app_name)
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=False)
