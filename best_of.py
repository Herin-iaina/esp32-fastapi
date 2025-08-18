"""
FastAPI Best-Of starter (Pydantic v2)
- Strict env-driven config (no hard-coded secrets)
- Clean logging (console + rotating file)
- CORS allowlist (comma-separated in env)
- JWT auth helpers (HS256, exp/iat/nbf)
- Health & readiness endpoints
- Optional DB readiness ping (skipped if no DB configured)

Env variables (prefix APP_):
  APP_SECRET_KEY=change-me
  APP_CORS_ORIGINS=https://example.com,https://admin.example.com
  APP_ACCESS_TOKEN_EXPIRES_MINUTES=30
  APP_LOG_LEVEL=INFO
  APP_ENVIRONMENT=dev
  APP_ENABLE_DOCS=true
  APP_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname  (optional)

Run:
  uvicorn main_bestof:app --reload --port 8000
"""
from __future__ import annotations

import logging
import logging.handlers
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import jwt  # PyJWT
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import Field, SecretStr
from pydantic import ValidationError
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# ----------------------------------------------------------------------------
# Settings (Pydantic v2)
# ----------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "Smartelia API"
    environment: Literal["dev", "staging", "prod"] = "dev"
    secret_key: SecretStr
    access_token_expires_minutes: int = 30
    cors_origins: list[str] = Field(default_factory=list)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    enable_docs: bool = True
    database_url: str | None = None  # optional; used for readiness check

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        # Support: list or comma-separated string
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


try:
    settings = Settings()
except ValidationError as e:
    # Fail fast with a clean message when mandatory env vars are missing
    raise RuntimeError(f"Invalid configuration: {e}")

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOGGER_NAME = "smartelia"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(getattr(logging, settings.log_level))

if not logger.handlers:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

# Align uvicorn access/error loggers with our level
for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uv = logging.getLogger(name)
    uv.setLevel(getattr(logging, settings.log_level))

# ----------------------------------------------------------------------------
# App init
# ----------------------------------------------------------------------------

docs_kwargs = {}
if not settings.enable_docs:
    docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(title=settings.app_name, **docs_kwargs)

# CORS (explicit allowlist; no wildcard in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Error handler (generic 500 guard)
# ----------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred. Please try again later.",
            "trace_id": request.headers.get("X-Request-ID"),
        },
    )

# ----------------------------------------------------------------------------
# JWT helpers
# ----------------------------------------------------------------------------

ALGORITHM = "HS256"

class TokenPayload(BaseModel):
    sub: str
    iat: int
    nbf: int
    exp: int


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes if expires_minutes is not None else settings.access_token_expires_minutes
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> TokenPayload:
    try:
        decoded = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[ALGORITHM])
        return TokenPayload(**decoded)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Dependency: get current subject from Authorization: Bearer <token>
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=True)

async def current_subject(creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> str:
    token = creds.credentials
    payload = decode_token(token)
    return payload.sub

# ----------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

# ----------------------------------------------------------------------------
# Readiness checker (optional DB ping)
# ----------------------------------------------------------------------------

def _db_ping(url: str) -> dict:
    """Try a lightweight connect if SQLAlchemy is available; otherwise best-effort.
    Returns dict with status and note.
    """
    try:
        from sqlalchemy import create_engine, text  # lazy import
        engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "note": "DB reachable"}
    except ModuleNotFoundError:
        return {"status": "unknown", "note": "sqlalchemy not installed; skipped"}
    except Exception as e:
        return {"status": "error", "note": str(e)}

# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "environment": settings.environment,
        "name": settings.app_name,
    }


@app.get("/ready")
async def ready():
    db_status = {"status": "skipped", "note": "no database configured"}
    if settings.database_url:
        db_status = _db_ping(settings.database_url)
    overall = "ok" if db_status.get("status") in {"ok", "unknown", "skipped"} else "error"
    return {
        "status": overall,
        "checks": {
            "database": db_status,
        },
    }


@app.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    # Replace with real authentication (DB/IdP). For now: accept anything non-empty for demo.
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="username and password required")

    # Example: subject can be a user id or email
    token = create_access_token(subject=body.username)
    return LoginResponse(access_token=token, expires_in=settings.access_token_expires_minutes * 60)


@app.get("/me")
async def me(subject: Annotated[str, Depends(current_subject)]):
    return {"subject": subject}


# ----------------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting %s on http://127.0.0.1:8000", settings.app_name)
    uvicorn.run(
        "main_bestof:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
