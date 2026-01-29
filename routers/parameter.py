from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from core.logging import logger
from apps.database_configuration import db_manager, ParameterDataModel, DataTempModel
from core.config import settings

router = APIRouter()

# Modèles Pydantic
class ParameterModel(BaseModel):
    temperature: float
    humidity: float
    start_date: str
    stat_stepper: bool
    number_stepper: int
    espece: str  # canne, poule, dinde, autre
    timetoclose: Optional[int] = None
    temp_incubation: float = 37.5  # Température d'incubation (°C)
    humidity_target: float = 60.0  # Humidité cible (%)
    rotation_count: int = 5  # Nombre de rotations par jour
    user_id: Optional[int] = None

class ParameterResponse(BaseModel):
    id: int
    temperature: float
    humidity: float
    start_date: str
    stat_stepper: bool
    number_stepper: int
    espece: str
    timetoclose: Optional[int]
    temp_incubation: float
    humidity_target: float
    rotation_count: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def get_current_parameters() -> dict:
    """Récupérer les paramètres actuels (dernière entrée)"""
    if not db_manager.connected:
        logger.warning("Base non connectée - retourner valeurs par défaut")
        return {
            "temperature": 25.0,
            "humidity": 60.0,
            "start_date": datetime.now(timezone.utc).isoformat(),
            "stat_stepper": False,
            "number_stepper": 3,
            "espece": "poule",
            "timetoclose": None,
            "temp_incubation": 37.5,
            "humidity_target": 60.0,
            "rotation_count": 5,
            "user_id": None
        }
    
    try:
        session = db_manager.SessionLocal()
        latest = session.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()
        session.close()
        
        if not latest:
            return {
                "temperature": 25.0,
                "humidity": 60.0,
                "start_date": datetime.now(timezone.utc).isoformat(),
                "stat_stepper": False,
                "number_stepper": 3,
                "espece": "poule",
                "timetoclose": None,
                "temp_incubation": 37.5,
                "humidity_target": 60.0,
                "rotation_count": 5,
                "user_id": None
            }
        
        return {
            "temperature": latest.temperature,
            "humidity": latest.humidity,
            "start_date": latest.start_date.isoformat() if latest.start_date else datetime.now(timezone.utc).isoformat(),
            "stat_stepper": latest.stat_stepper or False,
            "number_stepper": latest.number_stepper or 3,
            "espece": latest.espece,
            "timetoclose": latest.timetoclose,
            "temp_incubation": float(latest.temp_incubation) if latest.temp_incubation else 37.5,
            "humidity_target": float(latest.humidity_target) if latest.humidity_target else 60.0,
            "rotation_count": latest.rotation_count or 5,
            "user_id": latest.user_id
        }
    except Exception as e:
        logger.error(f"Erreur lecture paramètres: {e}", exc_info=True)
        return {}


@router.get("/parameter", response_model=ParameterModel)
async def read_parameters():
    """Récupère les paramètres actuels"""
    try:
        params = get_current_parameters()
        if not params:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun paramètre disponible"
            )
        return ParameterModel(**params)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur"
        )


@router.post("/parameter", response_model=dict)
async def update_parameters(params: ParameterModel):
    """Sauvegarde les paramètres dans la base de données"""
    try:
        if not db_manager.connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de données non connectée"
            )
        
        session = db_manager.SessionLocal()
        
        # Créer une nouvelle entrée
        try:
            # Gérer le format ISO 8601 (ex: 2024-01-29T11:06:06Z)
            start_date_obj = datetime.fromisoformat(params.start_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Format de date invalide: {params.start_date}, utilisation de la date actuelle")
            start_date_obj = datetime.now(timezone.utc)

        param_record = ParameterDataModel(
            temperature=params.temperature,
            humidity=params.humidity,
            start_date=start_date_obj,
            stat_stepper=params.stat_stepper,
            number_stepper=params.number_stepper,
            espece=params.espece,
            timetoclose=params.timetoclose,
            temp_incubation=params.temp_incubation,
            humidity_target=params.humidity_target,
            rotation_count=params.rotation_count,
            user_id=params.user_id,
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(param_record)
        session.commit()
        session.close()
        
        logger.info(f"Paramètres sauvegardés: espèce={params.espece}, temp={params.temp_incubation}°C")
        
        return {
            "message": "Paramètres sauvegardés avec succès",
            "data": params.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur sauvegarde: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.get("/parameters/history")
async def get_parameters_history(limit: int = 10):
    """Récupère l'historique des paramètres"""
    try:
        if not db_manager.connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base non connectée"
            )
        
        session = db_manager.SessionLocal()
        records = session.query(ParameterDataModel)\
            .order_by(ParameterDataModel.id.desc())\
            .limit(limit)\
            .all()
        session.close()
        
        return {
            "message": "Historique des paramètres",
            "count": len(records),
            "data": records
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur"
        )

