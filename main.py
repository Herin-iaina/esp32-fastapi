# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
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

@app.get("/api/sensors/history")
async def get_sensor_history(
    sensor: Optional[str] = Query(None, description="Nom du capteur"),
    start: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Any = Depends(get_db)
):
    """
    Retourne l'historique des températures et humidités pour un capteur et une période donnée.
    """
    from apps.database_configuration import DataTempModel
    query = db.query(DataTempModel)
    if sensor:
        query = query.filter(DataTempModel.sensor == sensor)
    if start:
        try:
            start_dt = datetime.datetime.strptime(start, "%Y-%m-%d")
            query = query.filter(DataTempModel.date_serveur >= start_dt)
        except Exception:
            raise HTTPException(status_code=400, detail="Format de date de début invalide")
    if end:
        try:
            end_dt = datetime.datetime.strptime(end, "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(DataTempModel.date_serveur < end_dt)
        except Exception:
            raise HTTPException(status_code=400, detail="Format de date de fin invalide")
    query = query.order_by(DataTempModel.date_serveur.asc())
    results = query.all()
    labels = [r.date_serveur.strftime("%Y-%m-%d") for r in results]
    temp_data = [r.temperature for r in results]
    hum_data = [r.humidity for r in results]
    return {
        "labels": labels,
        "temperature": temp_data,
        "humidity": hum_data
    }

@app.get("/api/sensors/realtime")
async def get_realtime_sensors(db: Any = Depends(get_db)):
    """
    Retourne la dernière valeur de chaque capteur.
    """
    from apps.database_configuration import DataTempModel
    subq = db.query(
        DataTempModel.sensor,
        func.max(DataTempModel.date_serveur).label("max_date")
    ).group_by(DataTempModel.sensor).subquery()

    results = db.query(DataTempModel).join(
        subq,
        (DataTempModel.sensor == subq.c.sensor) &
        (DataTempModel.date_serveur == subq.c.max_date)
    ).all()

    sensors = [
        {
            "name": r.sensor,
            "temperature": r.temperature,
            "humidity": r.humidity
        }
        for r in results
    ]
    return sensors

@app.get("/api/sensors/list")
async def get_sensor_list(db: Any = Depends(get_db)):
    """
    Retourne la liste des capteurs distincts.
    """
    from apps.database_configuration import DataTempModel
    sensors = db.query(DataTempModel.sensor).distinct().all()
    return [s[0] for s in sensors]

@app.get("/api/parameters/current")
async def get_current_parameters(db: Any = Depends(get_db)):
    """
    Retourne les derniers paramètres enregistrés.
    """
    from apps.database_configuration import ParameterDataModel
    param = db.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()
    if not param:
        raise HTTPException(status_code=404, detail="Aucun paramètre trouvé")
    return {
        "temperature": param.temperature,
        "humidity": param.humidity,
        "start_date": param.start_date.strftime("%Y-%m-%d"),
        "stat_stepper": "ON" if param.stat_stepper else "OFF",
        "number_stepper": param.number_stepper,
        "espece": param.espece,
        "timetoclose": param.timetoclose
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 5005)),
        reload=os.getenv("APP_RELOAD", "False").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )