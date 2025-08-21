# -*- coding: utf-8 -*-
import datetime
from core.logging import logger
from sqlalchemy import func
from apps.database_configuration import (
    db_manager, 
    DataTempModel, 
)

def validate_temperature(temp):
    return isinstance(temp, (int, float)) and 0 <= temp <= 50

def validate_humidity(humid):
    return isinstance(humid, (int, float)) and 0 <= humid <= 100


def add_data(data_to_insert):
    try:
        with db_manager.get_session_context() as session:
            new_data = DataTempModel(
                sensor=data_to_insert['sensor'],
                temperature=data_to_insert['temperature'],
                humidity=data_to_insert['humidity'],
                date_serveur=data_to_insert.get('date_serveur', datetime.datetime.now()),
                average_temperature=data_to_insert['average_temperature'],
                average_humidity=data_to_insert['average_humidity'],
                fan_status=data_to_insert['fan_status'],
                humidifier_status=data_to_insert['humidifier_status'],
                numfailedsensors=data_to_insert['numfailedsensors']
            )
            session.add(new_data)
            logger.info("Données insérées avec succès dans la table data_temp.")
            return True
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion des données: {e}")
        return False