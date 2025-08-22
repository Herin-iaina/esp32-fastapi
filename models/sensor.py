# -*- coding: utf-8 -*-
import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.exc import SQLAlchemyError

from core.logging import logger
from apps.database_configuration import db_manager, DataTempModel


class SensorData(BaseModel):
    """Modèle pour les données d'un capteur individuel"""
    temperature: float = Field(..., ge=-50, le=100, description="Température du capteur")
    humidity: float = Field(..., ge=0, le=100, description="Humidité du capteur")


class ValuesRequest(BaseModel):
    """Modèle pour la requête de valeurs avec capteurs dynamiques"""
    # Données moyennes globales
    average_temperature: float = Field(..., ge=-50, le=100, description="Température moyenne")
    average_humidity: float = Field(..., ge=0, le=100, description="Humidité moyenne")
    
    # États des équipements
    fan_status: bool = Field(..., description="Statut du ventilateur (True/False)")
    humidifier_status: bool = Field(..., description="Statut de l'humidificateur (True/False)")
    
    # Nombre de capteurs défaillants
    numFailedSensors: int = Field(..., ge=0, description="Nombre de capteurs défaillants")
    
    # Capteurs dynamiques - utilisation de Dict pour permettre des champs flexibles
    sensors: Dict[str, SensorData] = Field(
        default_factory=dict,
        description="Données des capteurs (clés: nom du capteur, valeurs: température et humidité)"
    )

    @field_validator('sensors')
    @classmethod
    def validate_sensors(cls, v: Dict[str, Any]) -> Dict[str, SensorData]:
        """Valide que chaque capteur a le bon format"""
        validated_sensors = {}
        for sensor_name, sensor_data in v.items():
            if not sensor_name.startswith('sensor'):
                continue
            
            if isinstance(sensor_data, dict):
                validated_sensors[sensor_name] = SensorData(**sensor_data)
            else:
                raise ValueError(f"Les données du capteur {sensor_name} doivent être un dictionnaire")
        
        return validated_sensors

    @model_validator(mode='after')
    def validate_at_least_one_sensor(self):
        """Valide qu'au moins un capteur est présent"""
        if not self.sensors:
            raise ValueError("Au moins un capteur doit être présent")
        return self


class DataToInsert(BaseModel):
    """Modèle pour les données à insérer en base"""
    sensor: str
    temperature: float
    humidity: float
    average_temperature: float
    average_humidity: float
    fan_status: bool
    humidifier_status: bool
    numfailedsensors: int
    date_serveur: datetime.datetime = Field(default_factory=datetime.datetime.now)


def validate_temperature(temp: Any) -> bool:
    """Valide une valeur de température"""
    try:
        temp_float = float(temp)
        return -50 <= temp_float <= 100
    except (ValueError, TypeError):
        return False


def validate_humidity(humid: Any) -> bool:
    """Valide une valeur d'humidité"""
    try:
        humid_float = float(humid)
        return 0 <= humid_float <= 100
    except (ValueError, TypeError):
        return False


def add_data(data_to_insert: DataToInsert) -> bool:
    """
    Ajoute des données de capteur en base de données
    
    Args:
        data_to_insert: Données validées à insérer
        
    Returns:
        bool: True si succès, False sinon
    """
    try:
        with db_manager.get_session_context() as session:
            new_data = DataTempModel(
                sensor=data_to_insert.sensor,
                temperature=data_to_insert.temperature,
                humidity=data_to_insert.humidity,
                date_serveur=data_to_insert.date_serveur,
                average_temperature=data_to_insert.average_temperature,
                average_humidity=data_to_insert.average_humidity,
                fan_status=data_to_insert.fan_status,
                humidifier_status=data_to_insert.humidifier_status,
                numfailedsensors=data_to_insert.numfailedsensors
            )
            session.add(new_data)
            session.commit()
            logger.info(f"Données insérées avec succès pour le capteur {data_to_insert.sensor}")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Erreur SQLAlchemy lors de l'insertion des données: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'insertion des données: {e}")
        return False


def process_sensor_data(request_data: ValuesRequest) -> list[bool]:
    """
    Traite et insère les données de tous les capteurs
    
    Args:
        request_data: Données validées de la requête
        
    Returns:
        list[bool]: Liste des résultats d'insertion pour chaque capteur
    """
    results = []
    
    for sensor_name, sensor_data in request_data.sensors.items():
        data_to_insert = DataToInsert(
            sensor=sensor_name,
            temperature=sensor_data.temperature,
            humidity=sensor_data.humidity,
            average_temperature=request_data.average_temperature,
            average_humidity=request_data.average_humidity,
            fan_status=request_data.fan_status,
            humidifier_status=request_data.humidifier_status,
            numfailedsensors=request_data.numFailedSensors
        )
        
        result = add_data(data_to_insert)
        results.append(result)
        
        if not result:
            logger.error(f"Échec de l'insertion pour le capteur {sensor_name}")
    
    return results