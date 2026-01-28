# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, system, parameter, sensor_values

from core.config import settings
from core.logging import logger

docs_kwargs = {}
if not settings.enable_docs:
    docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(
    title=settings.app_name,
    description="API REST pour système de surveillance des capteurs ESP32",
    version="2.0.0",
    **docs_kwargs
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Middleware CORS - Permettre le frontend séparé
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:5173", "http://localhost:3000"],
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

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting %s on http://127.0.0.1:8000", settings.app_name)
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)
