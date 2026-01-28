import json
import datetime
from datetime import timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, ValidationError

from core.config import settings
from core.logging import logger
from models.sensor import ValuesRequest, process_sensor_data
from core.mock_data import generate_mock_sensor_data, generate_mock_sensor_history
from apps.database_configuration import db_manager, DataTempModel

# Configuration du routeur
router = APIRouter(prefix="/sensor", tags=["Capteurs"])


class APIResponse(BaseModel):
    """Modèle de réponse standardisé"""
    message: str
    data: Dict[str, Any] = {}
    success: bool = True


def get_api_key(api_key: str) -> str:
    """
    Valide la clé API (fonction à adapter selon votre système d'authentification)
    """
    # À implémenter selon votre logique d'authentification
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante"
        )
    return api_key


@router.post("/values", response_model=APIResponse, tags=["Données"])
async def post_values(
    request: Request, 
    api_key: str = Depends(get_api_key)
) -> APIResponse:
    """
    Enregistre les données des capteurs avec validation complète
    
    Expected JSON format:
    {
        "average_temperature": 22.5,
        "average_humidity": 45.0,
        "fan_status": true,
        "humidifier_status": false,
        "numFailedSensors": 0,
        "sensor1": {"temperature": 22.1, "humidity": 44.5},
        "sensor2": {"temperature": 22.9, "humidity": 45.5},
        ...
    }
    """
    try:
        # Parse du JSON
        try:
            raw_data = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format JSON invalide"
            )
        
        # Séparation des données principales et des capteurs
        sensor_data = {}
        main_data = {}
        
        for key, value in raw_data.items():
            if key.startswith('sensor'):
                sensor_data[key] = value
            else:
                main_data[key] = value
        
        # Ajout des données de capteurs au modèle principal
        main_data['sensors'] = sensor_data
        
        # Validation avec Pydantic
        try:
            validated_data = ValuesRequest(**main_data)
        except ValidationError as e:
            logger.error(f"Erreur de validation Pydantic: {e}")
            error_details = []
            for error in e.errors():
                field = " -> ".join(str(x) for x in error['loc'])
                error_details.append(f"{field}: {error['msg']}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Données invalides: {'; '.join(error_details)}"
            )
        
        # Traitement et insertion des données
        logger.info(f"Traitement de {len(validated_data.sensors)} capteurs")
        results = process_sensor_data(validated_data)
        
        # Analyse des résultats
        successful_inserts = sum(results)
        total_sensors = len(results)
        
        if successful_inserts == 0:
            logger.error("Aucune donnée n'a pu être insérée")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Échec complet de l'enregistrement des données"
            )
        
        elif successful_inserts == total_sensors:
            logger.info(f"Toutes les données enregistrées avec succès: {total_sensors} capteurs")
            return APIResponse(
                message=f"Données reçues et enregistrées avec succès ({total_sensors} capteurs)",
                data={
                    "sensors_processed": total_sensors,
                    "sensors_successful": successful_inserts,
                    "sensors_failed": total_sensors - successful_inserts,
                    "failed_sensors_reported": validated_data.numFailedSensors,
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat()
                }
            )
        
        else:
            # Succès partiel
            logger.warning(f"Succès partiel: {successful_inserts}/{total_sensors} capteurs enregistrés")
            return APIResponse(
                message=f"Enregistrement partiel: {successful_inserts}/{total_sensors} capteurs",
                data={
                    "sensors_processed": total_sensors,
                    "sensors_successful": successful_inserts,
                    "sensors_failed": total_sensors - successful_inserts,
                    "failed_sensors_reported": validated_data.numFailedSensors,
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat()
                },
                success=False
            )
    
    except HTTPException:
        # Re-raise des HTTPException pour préserver le code de statut
        raise
    
    except Exception as e:
        logger.error(f"Erreur inattendue dans post_values: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )


@router.get("/health", tags=["Health"])
async def health_check():
    """Point de contrôle de santé du service capteurs"""
    return APIResponse(
        message="Service capteurs opérationnel",
        data={
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "service": "sensor_service"
        }
    )


@router.get("/values", response_model=APIResponse, tags=["Données"])
async def get_values(mock: bool = Query(False, description="Utiliser les données fictives")):
    """
    Récupère les dernières valeurs des capteurs
    
    Parameters:
    - mock: Utiliser les données fictives pour les tests (true/false)
    """
    try:
        if mock or settings.environment == "dev":
            # Utiliser les données fictives en développement
            mock_data = generate_mock_sensor_data()
            logger.info("Retour des données fictives (mode test)")
            return APIResponse(
                message="Données fictives (mode test)",
                data={
                    "average_temperature": mock_data.average_temperature,
                    "average_humidity": mock_data.average_humidity,
                    "fan_status": mock_data.fan_status,
                    "humidifier_status": mock_data.humidifier_status,
                    "numFailedSensors": mock_data.numFailedSensors,
                    "sensors": {
                        name: {
                            "temperature": sensor.temperature,
                            "humidity": sensor.humidity
                        }
                        for name, sensor in mock_data.sensors.items()
                    },
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
                    "is_mock": True
                }
            )
        else:
            # Récupérer les vraies données de la base
            if not db_manager.connected:
                logger.warning("Base de données non connectée - utiliser mock data")
                mock_data = generate_mock_sensor_data()
                return APIResponse(
                    message="Données fictives (base non disponible)",
                    data={
                        "average_temperature": mock_data.average_temperature,
                        "average_humidity": mock_data.average_humidity,
                        "fan_status": mock_data.fan_status,
                        "humidifier_status": mock_data.humidifier_status,
                        "numFailedSensors": mock_data.numFailedSensors,
                        "sensors": {
                            name: {
                                "temperature": sensor.temperature,
                                "humidity": sensor.humidity
                            }
                            for name, sensor in mock_data.sensors.items()
                        },
                        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
                        "is_mock": True
                    }
                )
            
            try:
                # Récupérer la dernière ligne de data_temp
                session = db_manager.SessionLocal()
                latest = session.query(DataTempModel).order_by(DataTempModel.id.desc()).first()
                session.close()
                
                if not latest:
                    logger.warning("Aucune données dans data_temp")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pas de données disponibles dans la base"
                    )
                
                logger.info(f"Retour des données réelles de la base (id={latest.id})")
                return APIResponse(
                    message="Données réelles (production)",
                    data={
                        "average_temperature": latest.average_temperature or 0,
                        "average_humidity": latest.average_humidity or 0,
                        "fan_status": latest.fan_status or False,
                        "humidifier_status": latest.humidifier_status or False,
                        "numFailedSensors": latest.numfailedsensors or 0,
                        "sensors": {
                            latest.sensor: {
                                "temperature": latest.temperature,
                                "humidity": latest.humidity
                            }
                        },
                        "timestamp": latest.date_serveur.isoformat() if latest.date_serveur else datetime.datetime.now(timezone.utc).isoformat(),
                        "is_mock": False
                    }
                )
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de la base: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Erreur base de données: {str(e)}"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des valeurs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )


@router.get("/history", response_model=APIResponse, tags=["Historique"])
async def get_history(
    hours: int = Query(24, ge=1, le=168, description="Nombre d'heures à récupérer"),
    mock: bool = Query(False, description="Utiliser les données fictives")
):
    """
    Récupère l'historique des données des capteurs
    
    Parameters:
    - hours: Nombre d'heures d'historique (1-168)
    - mock: Utiliser les données fictives pour les tests
    """
    try:
        if mock or settings.environment == "dev":
            history = generate_mock_sensor_history(hours=hours)
            logger.info(f"Retour de l'historique fictif ({hours} heures, {len(history)} points)")
            return APIResponse(
                message=f"Historique fictif ({hours} heures)",
                data={
                    "history": history,
                    "total_points": len(history),
                    "hours": hours,
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
                    "is_mock": True
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pas d'historique disponible - mode production nécessite une base de données"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )


# Export du routeur pour l'inclusion dans l'application principale
__all__ = ["router"]