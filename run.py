# -*- coding: utf-8 -*-
from fastapi import FastAPI
from routers import auth, system
from core.config import settings
from core.logging import logger
from fastapi.middleware.cors import CORSMiddleware

docs_kwargs = {}
if not settings.enable_docs:
    docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(title=settings.app_name, **docs_kwargs)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & templates
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
templates = Jinja2Templates(directory=settings.templates_dir)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(system.router, tags=["system"])

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting %s on http://127.0.0.1:8000", settings.app_name)
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)
