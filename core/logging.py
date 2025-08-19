import logging
import logging.handlers
from pathlib import Path
from core.config import settings

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOGGER_NAME = "smartelia"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(getattr(logging, settings.log_level))

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

# Aligne Uvicorn avec nos logs
for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uv = logging.getLogger(name)
    uv.setLevel(getattr(logging, settings.log_level))
