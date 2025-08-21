from fastapi import APIRouter, Depends, HTTPException
from typing import Literal, Annotated
from pydantic import BaseModel
from core.config import settings
from typing import Optional
from core.logging import logger
from models.sensor import (
    add_data , validate_temperature, validate_humidity)



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
                status_code=400,
                detail=f"Champs requis manquants: {', '.join(missing_fields)}"
            )
        
        # Validation des valeurs
        avg_temp = data.get('average_temperature')
        avg_hum = data.get('average_humidity')
        
        if not validate_temperature(avg_temp):
            raise HTTPException(
                status_code=400,
                detail=f"Valeur de température invalide: {avg_temp}"
            )
            
        if not validate_humidity(avg_hum):
            raise HTTPException(
                status_code=400,
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
                status_code=400,
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
                status_code=500,
                detail=f"Échec partiel de l'enregistrement: {successful_inserts}/{sensor_count} capteurs enregistrés"
            )
            
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON: {e}")
        raise HTTPException(
            status_code=400,
            detail="Format JSON invalide"
        )
    except Exception as e:
        logger.error(f"Erreur inattendue dans post_values: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erreur serveur interne"
        )
