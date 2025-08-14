# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Depends, status, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional, List, Dict, Any
import datetime
from datetime import timedelta, timezone
import os
import json
from pathlib import Path
import logging
import jwt

# Import adapté
from apps import post_temp_humidity
from apps.database_configuration import get_db, db_manager, DatabaseSettings

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration de l'environnement
class Settings:
    """Configuration centralisée de l'application"""
    API_KEYS: List[str] = os.getenv("API_KEYS", "votre_cle_api_1,votre_cle_api_2,Votre_Cle_API").split(",")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "votre_super_cle_secrete_changez_moi")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 5005))
    APP_RELOAD: bool = os.getenv("APP_RELOAD", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").lower()
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")

settings = Settings()

# Modèles Pydantic pour la validation des requêtes/réponses
class SensorData(BaseModel):
    """Modèle pour les données d'un capteur individuel"""
    humidity: float = Field(..., ge=0, le=100, description="Pourcentage d'humidité")
    temperature: float = Field(..., ge=-50, le=100, description="Température en Celsius")

class ValuesRequest(BaseModel):
    """Modèle pour la requête de valeurs avec capteurs dynamiques"""
    average_temperature: float = Field(..., ge=-50, le=100)
    average_humidity: float = Field(..., ge=0, le=100)
    fan_status: str = Field(..., max_length=50)
    humidifier_status: str = Field(..., max_length=50)
    numFailedSensors: int = Field(..., ge=0)

class ParameterRequest(BaseModel):
    """Modèle pour les paramètres système"""
    temperature: float = Field(..., ge=23, le=50, description="Température (entre 23°C et 50°C)")
    humidity: float = Field(..., ge=40, le=100, description="Humidité (entre 40% et 100%)")
    start_date: str = Field(..., description="Date de début")
    stat_stepper: bool = Field(..., description="État du stepper")
    number_stepper: int = Field(..., ge=3, le=10, description="Nombre de steppers (entre 3 et 10)")
    espece: str = Field(..., description="Type d'espèce")
    timetoclose: Optional[int] = Field(None, ge=18, le=30, description="Temps de fermeture (entre 18 et 30 jours)")

    @validator('espece')
    def validate_espece(cls, v):
        valid_especes = ["option1", "option2", "option3", "option4", "option5"]
        if v not in valid_especes:
            raise ValueError(f"L'espèce doit être l'une des suivantes : {', '.join(valid_especes)}")
        return v

class LoginRequest(BaseModel):
    """Modèle pour la requête de connexion"""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)
    rememberMe: Optional[bool] = False

class DateRequest(BaseModel):
    """Modèle pour les requêtes avec date"""
    date: str = Field(..., description="Chaîne de date")

class APIResponse(BaseModel):
    """Modèle de réponse API standardisée"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))

class TokenResponse(BaseModel):
    """Modèle pour les réponses de token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

# Gestion de la sécurité
security = HTTPBearer()

class APIKeyManager:
    """Gestionnaire des clés API"""
    def __init__(self):
        self.api_keys = [{'key': key.strip()} for key in settings.API_KEYS if key.strip()]
        if not self.api_keys:
            logger.warning("Aucune clé API configurée ! Utilisez la variable d'environnement API_KEYS")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Valide une clé API"""
        return any(api['key'] == api_key for api in self.api_keys)

api_key_manager = APIKeyManager()

def get_api_key(request: Request) -> str:
    """Extrait et valide la clé API des headers"""
    api_key = request.headers.get('X-API-KEY')
    
    if not api_key:
        logger.warning(f"Tentative d'accès sans clé API depuis {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante dans l'header X-API-KEY"
        )
    
    if not api_key_manager.validate_api_key(api_key):
        logger.warning(f"Tentative d'accès avec clé API invalide: {api_key[:10]}... depuis {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide"
        )
    
    return api_key

# Fonctions utilitaires
class DateFormatter:
    """Gestionnaire de formatage des dates"""
    
    SUPPORTED_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y"
    ]
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Formate une chaîne de date au format standard"""
        if not date_str or not isinstance(date_str, str):
            raise ValueError("Date string cannot be empty or non-string")
        
        date_str = date_str.strip()
        
        for fmt in DateFormatter.SUPPORTED_FORMATS:
            try:
                datetime_obj = datetime.datetime.strptime(date_str, fmt)
                return datetime_obj.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue
        
        raise ValueError(f"Format de date non supporté: {date_str}")

    @staticmethod
    def check_date(date_str: str) -> Optional[str]:
        """Vérifie et formate la date pour la base de données"""
        try:
            formatted = DateFormatter.format_date(date_str)
            return datetime.datetime.strptime(formatted, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Erreur de formatage de date: {e}")
            return None

class TokenManager:
    """Gestionnaire des tokens JWT"""
    
    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Crée un token d'accès"""
        if expires_delta:
            expire = datetime.datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {"sub": str(user_id), "exp": expire, "type": "access"}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Crée un token de rafraîchissement"""
        expire = datetime.datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[str]:
        """Vérifie et décode un token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            token_type_payload = payload.get("type", "access")
            
            if not user_id or token_type_payload != token_type:
                return None
                
            return user_id
        except jwt.ExpiredSignatureError:
            logger.warning("Token expiré")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token invalide: {e}")
            return None

token_manager = TokenManager()

# Initialisation de l'application FastAPI
app = FastAPI(
    title="Weather Monitoring API",
    description="API pour la surveillance des capteurs de température et d'humidité",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Support API",
        "email": "support@exemple.com"
    }
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques et templates
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.warning("Répertoire 'static' non trouvé")

if Path("templates").exists():
    templates = Jinja2Templates(directory="templates")
else:
    logger.warning("Répertoire 'templates' non trouvé")
    templates = None

# Routes principales
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def read_root(request: Request):
    """Page principale"""
    if templates:
        return templates.TemplateResponse("main.html", {"request": request})
    return HTMLResponse("<h1>API Weather Monitoring</h1><p>Interface web non disponible</p>")

@app.post("/values", response_model=APIResponse, tags=["Données"])
async def post_values(request: Request, api_key: str = Depends(get_api_key)):
    """Enregistre les données des capteurs"""
    try:
        data = await request.json()
        
        # Validation des données principales
        required_fields = ['average_temperature', 'average_humidity', 'fan_status', 'humidifier_status', 'numFailedSensors']
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Champ requis manquant: {field}"
                )
        
        # Validation des valeurs
        if not post_temp_humidity.validate_temperature(data.get('average_temperature')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valeur de température invalide"
            )
            
        if not post_temp_humidity.validate_humidity(data.get('average_humidity')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valeur d'humidité invalide"
            )
        
        # Extraction des valeurs de base
        average_temperature = float(data.get('average_temperature'))
        average_humidity = float(data.get('average_humidity'))
        fan_status = str(data.get('fan_status'))
        humidifier_status = str(data.get('humidifier_status'))
        num_failed_sensors = int(data.get('numFailedSensors', 0))
        
        date_serveur = datetime.datetime.now(timezone.utc)
        results = []
        sensor_count = 0
        
        # Traitement des données des capteurs
        for sensor_name, sensor_data in data.items():
            if sensor_name.startswith('sensor'):
                sensor_count += 1
                try:
                    if not isinstance(sensor_data, dict):
                        raise ValueError("Les données du capteur doivent être un objet")
                    
                    humidity = float(sensor_data['humidity'])
                    temperature = float(sensor_data['temperature'])
                    
                    # Validation des valeurs individuelles
                    if not (0 <= humidity <= 100):
                        raise ValueError("L'humidité doit être entre 0 et 100")
                    if not (-50 <= temperature <= 100):
                        raise ValueError("La température doit être entre -50 et 100")
                    
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
                    logger.error(f"Erreur données capteur {sensor_name}: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Données invalides pour {sensor_name}: {str(e)}"
                    )
        
        if sensor_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucune donnée de capteur trouvée"
            )
        
        if all(results):
            logger.info(f"Données enregistrées avec succès: {sensor_count} capteurs")
            return APIResponse(
                message=f"Données reçues et enregistrées avec succès ({sensor_count} capteurs)",
                data={"sensors_processed": sensor_count, "failed_sensors": num_failed_sensors}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Échec de l'enregistrement des données"
            )
            
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format JSON invalide"
        )
    except Exception as e:
        logger.error(f"Erreur inattendue dans post_values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )

@app.get("/getdata", tags=["Données"])
async def get_data(api_key: str = Depends(get_api_key)):
    """Récupère le statut actuel du dispositif"""
    try:
        data = post_temp_humidity.get_last_data()
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune donnée trouvée"
            )
        
        return {
            'temperature': data['average_temperature'],
            'humidity': data['average_humidity'],
            'Motor': post_temp_humidity.post_stepper_status(),
            'timestamp': data.get('date_serveur', datetime.datetime.now(timezone.utc))
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération des données"
        )

@app.get("/WeatherData", tags=["Données"])
async def get_weather_data(api_key: str = Depends(get_api_key)):
    """Récupère les données météo actuelles"""
    try:
        weather_data = post_temp_humidity.get_weather_data()
        return weather_data
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données météo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération des données météo"
        )

@app.get("/WeatherDF", tags=["Données"])
async def get_weather_dataframe(api_key: str = Depends(get_api_key)):
    """Récupère les moyennes des données météo"""
    try:
        weather_df = post_temp_humidity.get_data_average()
        return weather_df
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du dataframe météo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération du dataframe météo"
        )

@app.get("/alldata", tags=["Données"])
async def get_all_data(
    request: Request,
    date_int: Optional[str] = None,
    date_end: Optional[str] = None,
    api_key: str = Depends(get_api_key)
):
    """Récupère toutes les données avec filtrage optionnel par date"""
    try:
        if not date_int or not date_end:
            results = post_temp_humidity.get_all_data(None, None)
            return results
        
        # Ajouter l'heure par défaut si non spécifiée
        if ':' not in date_int:
            date_int += " 00:00"
        if ':' not in date_end:
            date_end += " 23:59"
        
        # Formater les dates
        try:
            formatted_date_int = DateFormatter.format_date(date_int)
            formatted_date_end = DateFormatter.format_date(date_end)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format de date invalide: {str(e)}"
            )
        
        # Vérifier que la date de début est antérieure à la date de fin
        if formatted_date_int > formatted_date_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de début doit être antérieure à la date de fin"
            )
        
        results = post_temp_humidity.get_all_data(formatted_date_int, formatted_date_end)
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de toutes les données: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )

@app.post("/isrunning", tags=["Statut"])
async def check_running_status(date_request: DateRequest):
    """Vérifie si le système fonctionne pour la date donnée"""
    try:
        date_formatted = DateFormatter.check_date(date_request.date)
        if not date_formatted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format de date invalide"
            )
        
        is_ok = post_temp_humidity.getdateinit(date_formatted)
        return is_ok
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la vérification du statut"
        )

@app.get("/isrunning", tags=["Statut"])
async def get_running_status():
    """Information sur l'endpoint de statut"""
    return {"message": "Cet endpoint nécessite une méthode POST avec un paramètre date"}

@app.post("/parameter", response_model=APIResponse, tags=["Configuration"])
async def create_parameter(parameter_request: ParameterRequest):
    """Crée ou met à jour les paramètres du système"""
    try:
        # Mapping des espèces avec validation
        espece_mapping = {
            "option1": "poule",
            "option2": "canne", 
            "option3": "oie",
            "option4": "caille",
            "option5": "other"
        }
        
        espece_name = espece_mapping.get(parameter_request.espece)
        if not espece_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type d'espèce invalide. Valeurs acceptées : {', '.join(espece_mapping.keys())}"
            )

        # Validation et récupération du temps de fermeture
        remain_date = {
            "poule": 21,
            "canne": 28,
            "oie": 30,
            "caille": 18,
            "other": None
        }

        dayclose = remain_date.get(espece_name)
        if espece_name == "other":
            if parameter_request.timetoclose is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le temps de fermeture est requis pour le type 'other'"
                )
            dayclose = parameter_request.timetoclose

        # Validation de la date
        try:
            formatted_date = DateFormatter.format_date(parameter_request.start_date)
            logger.info(f"Date formatée: {formatted_date}")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format de date invalide: {str(e)}"
            )

        # Préparation des données
        data_to_insert = {
            'temperature': parameter_request.temperature,
            'humidity': parameter_request.humidity,
            'start_date': formatted_date,
            'stat_stepper': parameter_request.stat_stepper,
            'number_stepper': parameter_request.number_stepper,
            'espece': espece_name,
            'timetoclose': dayclose
        }
        
        logger.info(f"Date de début reçue: {parameter_request.start_date}")
        result = post_temp_humidity.create_parameter(data_to_insert)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Échec de la création des paramètres"
            )

        logger.info("Paramètres créés avec succès")
        return APIResponse(
            message="Paramètres créés avec succès",
            data={**data_to_insert, 'id': result} if isinstance(result, (int, str)) else data_to_insert
        )
            
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur inattendue dans create_parameter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )

@app.get("/parameter", response_class=HTMLResponse, tags=["Pages"])
async def get_parameter_page(request: Request):
    """Page des paramètres"""
    if templates:
        return templates.TemplateResponse("parameter.html", {"request": request})
    return HTMLResponse("<h1>Page des paramètres non disponible</h1>")

@app.get("/api/parameter", tags=["Configuration"])
async def get_parameter_api(api_key: str = Depends(get_api_key)):
    """Récupère les paramètres système"""
    try:
        logger.info("Demande de récupération des paramètres système")
        result = post_temp_humidity.get_parameter()
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération des paramètres"
        )

# Endpoints d'authentification
@app.post("/login", response_model=TokenResponse, tags=["Authentification"])
async def login(login_request: LoginRequest):
    """Connexion utilisateur"""
    try:
        user_id = post_temp_humidity.login(login_request.username, login_request.password)
        if user_id:
            # Création du token d'accès
            access_token = token_manager.create_access_token(user_id)
            
            # Token de rafraîchissement si demandé
            refresh_token = None
            if login_request.rememberMe:
                refresh_token = token_manager.create_refresh_token(user_id)

            logger.info(f"Connexion réussie pour l'utilisateur: {login_request.username}")
            
            response_data = {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }
            
            if refresh_token:
                response_data["refresh_token"] = refresh_token
                
            return TokenResponse(**response_data)
        else:
            logger.warning(f"Tentative de connexion échouée pour: {login_request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la connexion"
        )

@app.post("/refresh-token", response_model=TokenResponse, tags=["Authentification"])
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    """Rafraîchit le token d'accès"""
    try:
        user_id = token_manager.verify_token(refresh_token, "refresh")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de rafraîchissement invalide ou expiré"
            )

        # Création d'un nouvel access token
        new_access_token = token_manager.create_access_token(user_id)

        logger.info(f"Token rafraîchi pour l'utilisateur: {user_id}")
        return TokenResponse(
            access_token=new_access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement du token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec du rafraîchissement du token"
        )

@app.get("/login", response_class=HTMLResponse, tags=["Pages"])
async def login_page(request: Request):
    """Page de connexion"""
    if templates:
        return templates.TemplateResponse("login.html", {"request": request})
    return HTMLResponse("<h1>Page de connexion non disponible</h1>")

@app.get("/check_session", tags=["Authentification"])
async def check_session(authorization: Optional[str] = Depends(security)):
    """Vérifie la session utilisateur"""
    if not authorization:
        return {"is_authenticated": False}
    
    try:
        token = authorization.credentials
        user_id = token_manager.verify_token(token)
        return {
            "is_authenticated": bool(user_id),
            "user_id": user_id
        }
    except:
        return {"is_authenticated": False}

@app.get("/parametre", response_class=HTMLResponse, tags=["Pages"])
async def parametre_page(request: Request):
    """Page des paramètres (alias)"""
    if templates:
        return templates.TemplateResponse("parametre.html", {"request": request})
    return HTMLResponse("<h1>Page des paramètres non disponible</h1>")

@app.post("/logout", tags=["Authentification"])
async def logout():
    """Déconnexion utilisateur"""
    # Dans une implémentation complète, vous pourriez vouloir inval
    return {"message": "Logged out successfully"}

@app.get("/datatable")
async def get_data_table(api_key: str = Depends(get_api_key)):
    """Get data table"""
    try:
        data = post_temp_humidity.data_table()
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data table"
        )

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