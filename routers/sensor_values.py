import json
import datetime
from datetime import timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, Query
from pydantic import BaseModel, ValidationError

from core.config import settings
from core.logging import logger
from models.sensor import ValuesRequest, process_sensor_data
from core.mock_data import generate_mock_sensor_data, generate_mock_sensor_history
from apps.database_configuration import db_manager, DataTempModel, ParameterDataModel

# Configuration du routeur
router = APIRouter(prefix="/sensor", tags=["Capteurs"])


class APIResponse(BaseModel):
    """Modèle de réponse standardisé"""
    message: str
    data: Dict[str, Any] = {}
    success: bool = True


def get_api_key(
    x_api_key: str | None = Header(None, alias="x-api-key"),
    api_key: str | None = None,
) -> str:
    """
    Valide la clé API envoyée par l'ESP.
    """
    effective_key = x_api_key or api_key
    if not effective_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante"
        )
    if effective_key != settings.sensor_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide"
        )
    return effective_key


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
        if mock:
            # Utiliser les données fictives uniquement si explicitement demandé
            mock_data = generate_mock_sensor_data()
            logger.info("Retour des données fictives (mock=true)")
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
                session = db_manager.SessionLocal()
                # 1. Sélectionner le relevé le plus récent pour CHAQUE capteur unique utile
                # On utilise une sous-requête pour trouver l'ID max par capteur
                from sqlalchemy import func
                subquery = session.query(
                    DataTempModel.sensor, 
                    func.max(DataTempModel.id).label('max_id')
                ).group_by(DataTempModel.sensor).subquery()

                latest_records = session.query(DataTempModel).join(
                    subquery, 
                    DataTempModel.id == subquery.c.max_id
                ).all()
                session.close()
                
                if not latest_records:
                    logger.warning("Aucune données dans data_temp")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pas de données disponibles dans la base"
                    )
                
                # 2. Aggéger les données de tous les capteurs
                sensors_dict = {}
                total_temp = 0
                total_humid = 0
                count = len(latest_records)
                fan_active = False
                humidifier_active = False
                failed_count = 0
                latest_ts = datetime.datetime.min.replace(tzinfo=timezone.utc)

                for rec in latest_records:
                    sensors_dict[rec.sensor] = {
                        "temperature": rec.temperature,
                        "humidity": rec.humidity
                    }
                    total_temp += rec.temperature
                    total_humid += rec.humidity
                    if rec.fan_status: fan_active = True
                    if rec.humidifier_status: humidifier_active = True
                    failed_count = max(failed_count, rec.numfailedsensors or 0)
                    
                    # Garder le timestamp le plus récent
                    rec_ts = rec.date_serveur.replace(tzinfo=timezone.utc) if rec.date_serveur.tzinfo is None else rec.date_serveur
                    if rec_ts > latest_ts:
                        latest_ts = rec_ts

                logger.info(f"Retour des données réelles aggrégées ({count} capteurs)")
                return APIResponse(
                    message="Données réelles (production aggrégée)",
                    data={
                        "average_temperature": total_temp / count if count > 0 else 0,
                        "average_humidity": total_humid / count if count > 0 else 0,
                        "fan_status": fan_active,
                        "humidifier_status": humidifier_active,
                        "numFailedSensors": failed_count,
                        "sensors": sensors_dict,
                        "timestamp": latest_ts.isoformat(),
                        "is_mock": False
                    }
                )
            except HTTPException:
                raise
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
    sensor: str = Query(None, description="Filtrer par nom de capteur"),
    start_date: str = Query(None, description="Date de début (ISO format)"),
    end_date: str = Query(None, description="Date de fin (ISO format)"),
    mock: bool = Query(False, description="Utiliser les données fictives")
):
    """
    Récupère l'historique des données des capteurs avec filtres optionnels
    """
    try:
        if mock:
            history = generate_mock_sensor_history(hours=hours)
            return APIResponse(
                message=f"Historique fictif ({hours} heures)",
                data={
                    "history": history,
                    "total_points": len(history),
                    "is_mock": True
                }
            )
        else:
            if not db_manager.connected:
                raise HTTPException(status_code=503, detail="Base non connectée")
            
            session = db_manager.SessionLocal()
            
            # Déterminer la plage de dates
            if start_date:
                try:
                    since = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except ValueError:
                    since = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=hours)
            else:
                since = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=hours)

            query = session.query(DataTempModel).filter(DataTempModel.date_serveur >= since)
            
            if end_date:
                try:
                    until = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    query = query.filter(DataTempModel.date_serveur <= until)
                except ValueError:
                    pass
            
            if sensor:
                query = query.filter(DataTempModel.sensor == sensor)
            
            # Récupérer les données réelles
            records = query.order_by(DataTempModel.date_serveur.desc()).limit(500).all()
            session.close()
            
            history_data = []
            for r in records:
                history_data.append({
                    "sensor": r.sensor,
                    "temperature": r.temperature,
                    "humidity": r.humidity,
                    "timestamp": r.date_serveur.isoformat() if r.date_serveur else datetime.datetime.now(timezone.utc).isoformat()
                })

            return APIResponse(
                message=f"Historique réel ({len(history_data)} points)",
                data={
                    "history": history_data,
                    "total_points": len(history_data),
                    "hours": hours,
                    "is_mock": False
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur interne"
        )


@router.get("/automation/status")
async def get_automation_status():
    """
    Renvoie true/false pour humidificateur et ventilateur.
    humidifier = true si humidité moyenne < seuil
    fan = true si température moyenne < seuil
    """
    if not db_manager.connected:
        return {"humidifier": False, "fan": False}

    try:
        session = db_manager.SessionLocal()
        from sqlalchemy import func

        # Calculer les moyennes actuelles pour chaque capteur unique (dernier relevé)
        subquery = session.query(
            DataTempModel.sensor,
            func.max(DataTempModel.id).label('max_id')
        ).group_by(DataTempModel.sensor).subquery()

        latest_records = session.query(DataTempModel).join(
            subquery,
            DataTempModel.id == subquery.c.max_id
        ).all()

        if not latest_records:
            session.close()
            return {"humidifier": False, "fan": False}

        total_temp = sum(r.temperature for r in latest_records)
        total_humid = sum(r.humidity for r in latest_records)
        count = len(latest_records)

        avg_temp = total_temp / count
        avg_humid = total_humid / count

        # Récupérer les seuils configurés
        params = session.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()
        session.close()

        if not params:
            return {"humidifier": False, "fan": False}

        # true si moyenne < seuil
        return {
            "humidifier": avg_humid < params.humidity,
            "fan": avg_temp < params.temperature
        }
    except Exception as e:
        logger.error(f"Erreur automation status: {e}")
        return {"humidifier": False, "fan": False}


@router.get("/automation/stepper")
async def get_automation_stepper():
    """
    Renvoie true/false pour la rotation du stepper.
    - Divise 24h par number_stepper pour obtenir l'intervalle
    - Retourne true pendant 2 minutes à chaque intervalle
    - Arrête les rotations après (timetoclose - 10) jours depuis start_date
    """
    if not db_manager.connected:
        return {"stepper": False}

    try:
        session = db_manager.SessionLocal()
        params = session.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()
        session.close()

        if not params:
            return {"stepper": False}

        number_stepper = params.number_stepper or 1
        timetoclose = params.timetoclose
        start_date = params.start_date

        if not start_date:
            return {"stepper": False}

        # Assurer que start_date a un timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        now = datetime.datetime.now(timezone.utc)

        # Vérifier si on est après (timetoclose - 10) jours - pas de rotation
        if timetoclose:
            end_rotation_date = start_date + datetime.timedelta(days=timetoclose - 10)
            if now >= end_rotation_date:
                return {"stepper": False}

        # Calculer l'intervalle en heures (24h / number_stepper)
        interval_hours = 24.0 / number_stepper
        interval_seconds = interval_hours * 3600

        # Calculer le temps écoulé depuis start_date
        elapsed = (now - start_date).total_seconds()

        if elapsed < 0:
            # Pas encore commencé
            return {"stepper": False}

        # Calculer où on en est dans le cycle
        # Position dans l'intervalle actuel
        position_in_interval = elapsed % interval_seconds

        # Retourner true pendant les 2 premières minutes de chaque intervalle
        two_minutes = 2 * 60  # 120 secondes

        if position_in_interval < two_minutes:
            return {"stepper": True}
        else:
            return {"stepper": False}

    except Exception as e:
        logger.error(f"Erreur automation stepper: {e}")
        return {"stepper": False}

# Export du routeur pour l'inclusion dans l'application principale
__all__ = ["router"]