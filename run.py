# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Depends, status, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
import datetime
from datetime import timedelta, timezone
import os
import json
from pathlib import Path
import logging
import jwt
from contextlib import asynccontextmanager

# Import adapté
from apps import post_temp_humidity
from apps.database_configuration import get_db, db_manager, DatabaseSettings

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Settings:
    """Configuration centralisée de l'application"""
    def __init__(self):
        self.API_KEYS: List[str] = self._get_api_keys()
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "votre_super_cle_secrete_changez_moi")
        self.ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = 7
        self.APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
        self.APP_PORT: int = int(os.getenv("APP_PORT", "5005"))
        self.APP_RELOAD: bool = os.getenv("APP_RELOAD", "False").lower() == "true"
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").lower()
        self.CORS_ORIGINS: List[str] = self._get_cors_origins()

    def _get_api_keys(self) -> List[str]:
        """Récupère et valide les clés API"""
        api_keys_str = os.getenv("API_KEYS", "votre_cle_api_1,votre_cle_api_2,Votre_Cle_API")
        keys = [key.strip() for key in api_keys_str.split(",") if key.strip()]
        if not keys:
            logger.warning("Aucune clé API valide configurée")
        return keys

    def _get_cors_origins(self) -> List[str]:
        """Récupère les origines CORS autorisées"""
        origins_str = os.getenv("CORS_ORIGINS", "*")
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

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

    @field_validator('espece')
    @classmethod
    def validate_espece(cls, v: str) -> str:
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
security = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Gestionnaire des clés API"""
    def __init__(self):
        self.api_keys = [{'key': key} for key in settings.API_KEYS]
        if not self.api_keys:
            logger.warning("Aucune clé API configurée ! Utilisez la variable d'environnement API_KEYS")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Valide une clé API"""
        if not api_key:
            return False
        return any(api['key'] == api_key for api in self.api_keys)


api_key_manager = APIKeyManager()


async def get_api_key(request: Request) -> str:
    """Extrait et valide la clé API des headers"""
    api_key = request.headers.get('X-API-KEY')
    
    if not api_key:
        logger.warning(f"Tentative d'accès sans clé API depuis {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante dans l'header X-API-KEY",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not api_key_manager.validate_api_key(api_key):
        logger.warning(f"Tentative d'accès avec clé API invalide: {api_key[:10]}... depuis {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide",
            headers={"WWW-Authenticate": "ApiKey"},
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
    
    @classmethod
    def format_date(cls, date_str: str) -> str:
        """Formate une chaîne de date au format standard"""
        if not date_str or not isinstance(date_str, str):
            raise ValueError("Date string cannot be empty or non-string")
        
        date_str = date_str.strip()
        
        for fmt in cls.SUPPORTED_FORMATS:
            try:
                datetime_obj = datetime.datetime.strptime(date_str, fmt)
                return datetime_obj.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue
        
        raise ValueError(f"Format de date non supporté: {date_str}")

    @classmethod
    def check_date(cls, date_str: str) -> Optional[str]:
        """Vérifie et formate la date pour la base de données"""
        try:
            formatted = cls.format_date(date_str)
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
        
        to_encode = {"sub": str(user_id), "exp": expire, "type": "access", "iat": datetime.datetime.now(timezone.utc)}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Crée un token de rafraîchissement"""
        expire = datetime.datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh", "iat": datetime.datetime.now(timezone.utc)}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[str]:
        """Vérifie et décode un token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            token_type_payload = payload.get("type", "access")
            
            if not user_id or token_type_payload != token_type:
                logger.warning("Token invalide: user_id ou type incorrect")
                return None
                
            return user_id
        except jwt.ExpiredSignatureError:
            logger.warning("Token expiré")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token invalide: {e}")
            return None


token_manager = TokenManager()


# Context manager pour le cycle de vie de l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    logger.info("Démarrage de l'application Weather Monitoring API")
    logger.info(f"Configuration: Host={settings.APP_HOST}, Port={settings.APP_PORT}")
    
    # Vérification de la santé de la base de données
    if not db_manager.health_check():
        logger.error("Connexion à la base de données échouée au démarrage")
    else:
        logger.info("Connexion à la base de données réussie")
    
    yield
    
    # Shutdown
    logger.info("Arrêt de l'application Weather Monitoring API")


# Initialisation de l'application FastAPI
app = FastAPI(
    title="Weather Monitoring API",
    description="API pour la surveillance des capteurs de température et d'humidité",
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Support API",
        "email": "support@exemple.com"
    },
    lifespan=lifespan
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques et templates
static_dir = Path("static")
templates_dir = Path("templates")

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    logger.warning("Répertoire 'static' non trouvé")

if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))
else:
    logger.warning("Répertoire 'templates' non trouvé")
    templates = None


# Middleware pour logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour logger les requêtes"""
    start_time = datetime.datetime.now()
    
    # Traitement de la requête
    response = await call_next(request)
    
    # Calcul du temps de traitement
    process_time = (datetime.datetime.now() - start_time).total_seconds()
    
    # Log de la requête
    logger.info(
        f"Method: {request.method} | "
        f"URL: {request.url} | "
        f"Status: {response.status_code} | "
        f"Process time: {process_time:.4f}s"
    )
    
    return response


# Routes principales
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def read_root(request: Request):
    """Page principale"""
    if templates:
        return templates.TemplateResponse("main.html", {"request": request})
    return HTMLResponse("""
    <html>
        <head><title>Weather Monitoring API</title></head>
        <body>
            <h1>API Weather Monitoring</h1>
            <p>Interface web non disponible</p>
            <p><a href="/docs">Documentation API</a></p>
        </body>
    </html>
    """)


@app.post("/values", response_model=APIResponse, tags=["Données"])
async def post_values(request: Request, api_key: str = Depends(get_api_key)):
    """Enregistre les données des capteurs"""
    try:
        data = await request.json()
        
        # Validation des données principales
        required_fields = ['average_temperature', 'average_humidity', 'fan_status', 'humidifier_status', 'numFailedSensors']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Champs requis manquants: {', '.join(missing_fields)}"
            )
        
        # Validation des valeurs
        avg_temp = data.get('average_temperature')
        avg_hum = data.get('average_humidity')
        
        if not post_temp_humidity.validate_temperature(avg_temp):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Valeur de température invalide: {avg_temp}"
            )
            
        if not post_temp_humidity.validate_humidity(avg_hum):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Valeur d'humidité invalide: {avg_hum}"
            )
        
        # Extraction et validation des valeurs de base
        try:
            average_temperature = float(avg_temp)
            average_humidity = float(avg_hum)
            fan_status = str(data.get('fan_status'))
            humidifier_status = str(data.get('humidifier_status'))
            num_failed_sensors = int(data.get('numFailedSensors', 0))
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erreur de conversion des données: {e}"
            )
        
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
                    
                    if 'humidity' not in sensor_data or 'temperature' not in sensor_data:
                        raise ValueError("Données de capteur incomplètes (humidity/temperature manquants)")
                    
                    humidity = float(sensor_data['humidity'])
                    temperature = float(sensor_data['temperature'])
                    
                    # Validation des valeurs individuelles
                    if not (0 <= humidity <= 100):
                        raise ValueError(f"L'humidité doit être entre 0 et 100, reçu: {humidity}")
                    if not (-50 <= temperature <= 100):
                        raise ValueError(f"La température doit être entre -50 et 100, reçu: {temperature}")
                    
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
                detail="Aucune donnée de capteur trouvée (aucun champ commençant par 'sensor')"
            )
        
        successful_inserts = sum(1 for result in results if result)
        
        if successful_inserts == sensor_count:
            logger.info(f"Données enregistrées avec succès: {sensor_count} capteurs")
            return APIResponse(
                message=f"Données reçues et enregistrées avec succès ({sensor_count} capteurs)",
                data={
                    "sensors_processed": sensor_count,
                    "sensors_successful": successful_inserts,
                    "failed_sensors": num_failed_sensors
                }
            )
        else:
            logger.error(f"Échec partiel: {successful_inserts}/{sensor_count} capteurs enregistrés")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Échec partiel de l'enregistrement: {successful_inserts}/{sensor_count} capteurs enregistrés"
            )
            
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format JSON invalide"
        )
    except Exception as e:
        logger.error(f"Erreur inattendue dans post_values: {e}", exc_info=True)
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
            'temperature': data.get('average_temperature'),
            'humidity': data.get('average_humidity'),
            'Motor': post_temp_humidity.post_stepper_status(),
            'timestamp': data.get('date_serveur', datetime.datetime.now(timezone.utc))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}", exc_info=True)
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
        logger.error(f"Erreur lors de la récupération des données météo: {e}", exc_info=True)
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
        logger.error(f"Erreur lors de la récupération du dataframe météo: {e}", exc_info=True)
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
        # Si aucune date n'est fournie, retourner toutes les données
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
        logger.error(f"Erreur lors de la récupération de toutes les données: {e}", exc_info=True)
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
        logger.error(f"Erreur lors de la vérification du statut: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la vérification du statut"
        )


@app.get("/isrunning", tags=["Statut"])
async def get_running_status():
    """Information sur l'endpoint de statut"""
    return {
        "message": "Cet endpoint nécessite une méthode POST avec un paramètre date",
        "example": {
            "date": "2024-01-15"
        }
    }


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
    except Exception as e:
        logger.error(f"Erreur inattendue dans create_parameter: {str(e)}", exc_info=True)
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
        logger.error(f"Erreur lors de la récupération des paramètres: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération des paramètres"
        )


# Endpoints d'authentification
@app.post("/login", response_model=TokenResponse, tags=["Authentification"])
async def login(login_request: LoginRequest):
    """Connexion utilisateur"""
    try:
        # Validation des entrées
        if not login_request.username.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nom d'utilisateur ne peut pas être vide"
            )
        
        if not login_request.password.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe ne peut pas être vide"
            )

        user_id = post_temp_humidity.login(login_request.username.strip(), login_request.password)
        
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
                detail="Nom d'utilisateur ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la connexion"
        )


@app.post("/refresh-token", response_model=TokenResponse, tags=["Authentification"])
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    """Rafraîchit le token d'accès"""
    try:
        if not refresh_token or not refresh_token.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de rafraîchissement requis"
            )

        user_id = token_manager.verify_token(refresh_token.strip(), "refresh")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de rafraîchissement invalide ou expiré",
                headers={"WWW-Authenticate": "Bearer"},
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
        logger.error(f"Erreur lors du rafraîchissement du token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec du rafraîchissement du token"
        )


@app.get("/login", response_class=HTMLResponse, tags=["Pages"])
async def login_page(request: Request):
    """Page de connexion"""
    if templates:
        return templates.TemplateResponse("login.html", {"request": request})
    return HTMLResponse("""
    <html>
        <head><title>Connexion - Weather Monitoring</title></head>
        <body>
            <h1>Page de connexion non disponible</h1>
            <p><a href="/">Retour à l'accueil</a></p>
        </body>
    </html>
    """)


@app.get("/check_session", tags=["Authentification"])
async def check_session(authorization: Optional[str] = Depends(security)):
    """Vérifie la session utilisateur"""
    if not authorization:
        return {"is_authenticated": False, "message": "Aucun token fourni"}
    
    try:
        token = authorization.credentials
        user_id = token_manager.verify_token(token)
        
        if user_id:
            return {
                "is_authenticated": True,
                "user_id": user_id
            }
        else:
            return {
                "is_authenticated": False,
                "message": "Token invalide ou expiré"
            }
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de session: {e}")
        return {
            "is_authenticated": False,
            "message": "Erreur lors de la vérification"
        }


@app.get("/parametre", response_class=HTMLResponse, tags=["Pages"])
async def parametre_page(request: Request):
    """Page des paramètres (alias)"""
    if templates:
        return templates.TemplateResponse("parametre.html", {"request": request})
    return HTMLResponse("""
    <html>
        <head><title>Paramètres - Weather Monitoring</title></head>
        <body>
            <h1>Page des paramètres non disponible</h1>
            <p><a href="/">Retour à l'accueil</a></p>
        </body>
    </html>
    """)


@app.post("/logout", tags=["Authentification"])
async def logout():
    """Déconnexion utilisateur"""
    # Dans une implémentation complète, vous pourriez vouloir invalider le token
    # en le stockant dans une liste noire (blacklist)
    return APIResponse(
        message="Déconnexion réussie",
        data={"logout_time": datetime.datetime.now(timezone.utc)}
    )


@app.get("/datatable", tags=["Données"])
async def get_data_table(api_key: str = Depends(get_api_key)):
    """Récupère la table de données"""
    try:
        data = post_temp_humidity.data_table()
        return data
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la table de données: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération de la table de données"
        )


# Health check endpoint
@app.get("/health", tags=["Santé"])
async def health_check():
    """Endpoint de vérification de santé"""
    try:
        db_healthy = db_manager.health_check()
        app_status = "healthy" if db_healthy else "unhealthy"
        
        health_data = {
            "status": app_status,
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": datetime.datetime.now(timezone.utc),
            "version": "2.2.0",
            "uptime": "Service en fonctionnement"
        }
        
        status_code = 200 if db_healthy else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de santé: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Erreur lors de la vérification de santé",
                "timestamp": datetime.datetime.now(timezone.utc)
            }
        )


@app.get("/metrics", tags=["Santé"])
async def get_metrics(api_key: str = Depends(get_api_key)):
    """Récupère les métriques de l'application"""
    try:
        # Métriques de base - à adapter selon vos besoins
        metrics = {
            "api_version": "2.2.0",
            "uptime": datetime.datetime.now(timezone.utc),
            "database_status": "connected" if db_manager.health_check() else "disconnected",
            "total_api_keys": len(api_key_manager.api_keys),
            "cors_origins": len(settings.CORS_ORIGINS)
        }
        return metrics
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération des métriques"
        )


# Gestionnaires d'erreurs globaux
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Gestionnaire pour les erreurs 404"""
    logger.warning(f"Endpoint non trouvé: {request.method} {request.url}")
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint non trouvé",
            "path": str(request.url),
            "method": request.method,
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Gestionnaire pour les erreurs 500"""
    logger.error(f"Erreur serveur interne: {request.method} {request.url} - {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erreur serveur interne",
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """Gestionnaire pour les erreurs de validation"""
    logger.warning(f"Erreur de validation: {request.method} {request.url} - {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Erreur de validation des données",
            "errors": exc.errors() if hasattr(exc, 'errors') else str(exc),
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }
    )


# Endpoint pour obtenir la configuration (sans données sensibles)
@app.get("/config", tags=["Configuration"])
async def get_config_info(api_key: str = Depends(get_api_key)):
    """Récupère les informations de configuration (non sensibles)"""
    try:
        config_info = {
            "app_version": "2.2.0",
            "cors_origins_count": len(settings.CORS_ORIGINS),
            "api_keys_count": len(settings.API_KEYS),
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
            "log_level": settings.LOG_LEVEL,
            "static_files_available": static_dir.exists(),
            "templates_available": templates is not None
        }
        return config_info
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération de la configuration"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Configuration de l'environnement
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "5005"))
    reload = os.getenv("APP_RELOAD", "False").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    logger.info(f"Démarrage du serveur sur {host}:{port}")
    logger.info(f"Mode reload: {reload}")
    logger.info(f"Niveau de log: {log_level}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )