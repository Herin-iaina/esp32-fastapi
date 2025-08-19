from fastapi import APIRouter
from datetime import datetime, timezone
from core.config import settings

router = APIRouter()

def _db_ping(url: str) -> dict:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "note": "DB reachable"}
    except ModuleNotFoundError:
        return {"status": "unknown", "note": "sqlalchemy not installed; skipped"}
    except Exception as e:
        return {"status": "error", "note": str(e)}

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "environment": settings.environment,
        "name": settings.app_name,
    }

@router.get("/ready")
async def ready():
    db_status = {"status": "skipped", "note": "no database configured"}
    if settings.database_url:
        db_status = _db_ping(settings.database_url)
    overall = "ok" if db_status.get("status") in {"ok", "unknown", "skipped"} else "error"
    return {"status": overall, "checks": {"database": db_status}}
