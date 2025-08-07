# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime
import os

# Import adapté
from apps import post_temp_humidity
from apps.database_configuration import get_db, db_manager, DatabaseSettings

# Chargement dynamique des clés API depuis l'environnement
API_KEYS = os.getenv("API_KEYS", "votre_cle_api_1,votre_cle_api_2,Votre_Cle_API").split(",")

class SensorData(BaseModel):
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    temperature: float = Field(..., ge=-50, le=100, description="Temperature in Celsius")

class ValuesRequest(BaseModel):
    average_temperature: float = Field(..., ge=-50, le=100)
    average_humidity: float = Field(..., ge=0, le=100)
    fan_status: bool
    humidifier_status: bool
    numFailedSensors: int = Field(..., ge=0)

class ParameterRequest(BaseModel):
    temperature: float = Field(..., gt=0, description="Target temperature")
    humidity: float = Field(..., gt=0, description="Target humidity")
    start_date: str = Field(..., description="Start date")
    stat_stepper: str = Field(..., description="Stepper status")
    number_stepper: int = Field(..., gt=0, description="Number of steppers")
    espece: str = Field(..., description="Species type")
    timetoclose: Optional[int] = Field(None, description="Time to close in days")

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    rememberMe: Optional[bool] = False

class DateRequest(BaseModel):
    date: str = Field(..., description="Date string")

class APIResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None

def get_api_key(request: Request) -> str:
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key missing")
    if api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return api_key

class DateFormatter:
    @staticmethod
    def format_date(date_str: str) -> str:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y"
        ]
        for fmt in formats:
            try:
                datetime_obj = datetime.datetime.strptime(date_str, fmt)
                return datetime_obj.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue
        raise ValueError("Invalid date format")

    @staticmethod
    def check_date(date_str: str) -> Optional[str]:
        try:
            formatted = DateFormatter.format_date(date_str)
            return datetime.datetime.strptime(formatted, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d")
        except ValueError:
            return None

app = FastAPI(
    title="Weather Monitoring API",
    description="API for monitoring temperature and humidity sensors",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

# ... (tous les autres endpoints restent inchangés, sauf pour l'import et la gestion API key) ...

# Exemple pour un endpoint utilisant la session SQLAlchemy :
@app.get("/health")
async def health_check():
    db_healthy = db_manager.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.datetime.now()
    }

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 5005)),
        reload=os.getenv("APP_RELOAD", "False").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )