# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import datetime
from datetime import timedelta
import os
import json
from pathlib import Path

# Import adapté
# from apps import post_temp_humidity
# from apps.database_configuration import get_db, db_manager, DatabaseSettings

# Chargement dynamique des clés API depuis l'environnement
API_KEYS = os.getenv("API_KEYS", "votre_cle_api_1,votre_cle_api_2,Votre_Cle_API").split(",")


# Pydantic models for request/response validation
class SensorData(BaseModel):
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    temperature: float = Field(..., ge=-50, le=100, description="Temperature in Celsius")

class ValuesRequest(BaseModel):
    average_temperature: float = Field(..., ge=-50, le=100)
    average_humidity: float = Field(..., ge=0, le=100)
    fan_status: str = Field(..., max_length=50)
    humidifier_status: str = Field(..., max_length=50)
    numFailedSensors: int = Field(..., ge=0)
    # Dynamic sensor data will be handled separately

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

# Security
security = HTTPBearer()

class APIKeyManager:
    def __init__(self):
        self.api_keys = [
            {'key': 'votre_cle_api_1'},
            {'key': 'votre_cle_api_2'},
            {'key': 'Votre_Cle_API'},
        ]
    
    def validate_api_key(self, api_key: str) -> bool:
        return any(api['key'] == api_key for api in self.api_keys)

api_key_manager = APIKeyManager()

def get_api_key(request: Request) -> str:
    """Extract API key from headers"""
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )
    
    if not api_key_manager.validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key

# Utility functions
class DateFormatter:
    @staticmethod
    def format_date(date_str: str) -> str:
        """Format date string to standard format"""
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
        """Check and format date for database"""
        try:
            formatted = DateFormatter.format_date(date_str)
            return datetime.datetime.strptime(formatted, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d")
        except ValueError:
            return None

# FastAPI app initialization
app = FastAPI(
    title="Weather Monitoring API",
    description="API for monitoring temperature and humidity sensors",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page"""
    return templates.TemplateResponse("main.html", {"request": request})

@app.post("/values", response_model=APIResponse)
async def post_values(request: Request, api_key: str = Depends(get_api_key)):
    """Post sensor values"""
    try:
        data = await request.json()
        
        # Extract base values
        average_temperature = float(data.get('average_temperature', 0))
        average_humidity = float(data.get('average_humidity', 0))
        fan_status = data.get('fan_status', '')
        humidifier_status = data.get('humidifier_status', '')
        num_failed_sensors = int(data.get('numFailedSensors', 0))
        
        date_serveur = datetime.datetime.now()
        results = []
        
        # Process sensor data
        for sensor_name, sensor_data in data.items():
            if sensor_name.startswith('sensor'):
                try:
                    humidity = float(sensor_data['humidity'])
                    temperature = float(sensor_data['temperature'])
                    
                    data_to_insert = {
                        'sensor': sensor_name,
                        'temperature': temperature,
                        'humidity': humidity,
                        'average_humidity': average_humidity,
                        'average_temperature': average_temperature,
                        'fan_status': fan_status,
                        'humidifier_status': humidifier_status,
                        'numfailedsensors': num_failed_sensors,
                        'date_serveur': date_serveur
                    }
                    
                    result = post_temp_humidity.add_data(data_to_insert)
                    results.append(result)
                    
                except (KeyError, ValueError, TypeError) as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid sensor data for {sensor_name}"
                    )
        
        if all(results):
            # La gestion de la fermeture est maintenant automatique avec le pool
            return APIResponse(message="Data received successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save data"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or invalid data"
        )

@app.get("/getdata")
async def get_data(api_key: str = Depends(get_api_key)):
    """Get current device status"""
    try:
        fan_humidity_status = post_temp_humidity.get_last_data()
        fan_status = fan_humidity_status[0]
        humidifier_status = fan_humidity_status[1]
        motor_status = post_temp_humidity.post_stepper_status()

        return {
            'FAN': fan_status,
            'Humidity': humidifier_status,
            'Motor': motor_status
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data"
        )

@app.get("/WeatherData")
async def get_weather_data(api_key: str = Depends(get_api_key)):
    """Get current weather data"""
    try:
        weather_data = post_temp_humidity.get_weather_data()
        return weather_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather data"
        )

@app.get("/WeatherDF")
async def get_weather_dataframe(api_key: str = Depends(get_api_key)):
    """Get weather data averages"""
    try:
        weather_df = post_temp_humidity.get_data_average()
        return weather_df
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather dataframe"
        )

@app.get("/alldata")
async def get_all_data(
    request: Request,
    date_int: Optional[str] = None,
    date_end: Optional[str] = None,
    api_key: str = Depends(get_api_key)
):
    """Get all data with optional date filtering"""
    try:
        if not date_int or not date_end:
            results = post_temp_humidity.get_all_data(False, False)
            return results
        
        # Add default time if not specified
        if ':' not in date_int:
            date_int += " 00:00"
        if ':' not in date_end:
            date_end += " 00:00"
        
        # Format dates
        formatted_date_int = DateFormatter.format_date(date_int)
        formatted_date_end = DateFormatter.format_date(date_end)
        
        results = post_temp_humidity.get_all_data(formatted_date_int, formatted_date_end)
        return results
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/isrunning")
async def check_running_status(date_request: DateRequest):
    """Check if system is running for given date"""
    try:
        date_formatted = DateFormatter.check_date(date_request.date)
        if not date_formatted:
            return {"message": "Invalid date format"}
        
        is_ok = post_temp_humidity.getdateinit(date_formatted)
        return is_ok
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check running status"
        )

@app.get("/isrunning")
async def get_running_status():
    """Get current running status"""
    return {"message": "Endpoint requires POST method with date parameter"}

@app.post("/parameter", response_model=APIResponse)
async def create_parameter(
    parameter_request: ParameterRequest,
    api_key: str = Depends(get_api_key)
):
    """Create system parameters"""
    try:
        espece_mapping = {
            "option1": "poule",
            "option2": "canne", 
            "option3": "oie",
            "option4": "caille",
            "option5": "other"
        }
        
        remain_date = {
            "poule": 21,
            "canne": 28,
            "oie": 30,
            "caille": 18,
            "other": parameter_request.timetoclose or 28
        }
        
        if parameter_request.espece not in espece_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown species"
            )
        
        espece_name = espece_mapping[parameter_request.espece]
        dayclose = remain_date[espece_name]
        
        if isinstance(dayclose, int) and dayclose < 0:
            dayclose = 28
        
        formatted_date = DateFormatter.format_date(parameter_request.start_date)
        
        data_to_insert = {
            'temperature': max(parameter_request.temperature, 23),
            'humidity': max(parameter_request.humidity, 40),
            'start_date': formatted_date,
            'stat_stepper': parameter_request.stat_stepper,
            'number_stepper': max(parameter_request.number_stepper, 3),
            'espece': espece_name,
            'timetoclose': dayclose
        }
        
        result = post_temp_humidity.create_parameter(data_to_insert)
        
        if result:
            # La gestion de la fermeture est maintenant automatique avec le pool
            return APIResponse(message="Parameters created successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create parameters"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format"
        )

@app.get("/parameter")
async def get_parameter(api_key: str = Depends(get_api_key)):
    """Get system parameters"""
    try:
        result = post_temp_humidity.get_parameter()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve parameters"
        )

# Authentication endpoints (simplified - you may want to implement proper JWT)
@app.post("/login")
async def login(login_request: LoginRequest):
    """User login"""
    try:
        user_id = post_temp_humidity.login(login_request.username, login_request.password)
        if user_id:
            # In a real application, you'd generate a JWT token here
            return {"success": True, "user_id": user_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/check_session")
async def check_session():
    """Check user session - implement based on your auth system"""
    # This would need to be implemented based on your authentication system
    return {"is_authenticated": False}

@app.get("/parametre", response_class=HTMLResponse)
async def parametre_page(request: Request):
    """Parameters page"""
    return templates.TemplateResponse("parametre.html", {"request": request})

@app.get("/logout")
async def logout():
    """User logout"""
    return {"message": "Logged out successfully"}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = db_manager.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.datetime.now()
    }

# Error handlers
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