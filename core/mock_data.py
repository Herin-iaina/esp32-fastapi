# -*- coding: utf-8 -*-
"""
Module de données fictives pour les tests
Génère des données réalistes de capteurs
"""
import datetime
from datetime import timezone
import math
import random
from models.sensor import ValuesRequest, SensorData

def generate_mock_sensor_data() -> ValuesRequest:
    """
    Génère des données fictives réalistes de capteurs
    """
    # Nombre aléatoire de capteurs (2-5)
    num_sensors = random.randint(2, 5)
    
    # Données globales moyennes
    base_temp = random.uniform(18, 28)
    base_humidity = random.uniform(40, 65)
    
    # Générer les capteurs individuels
    sensors = {}
    for i in range(1, num_sensors + 1):
        sensor_name = f"sensor_{i:02d}"
        # Ajouter une petite variation par rapport à la moyenne
        temp = base_temp + random.uniform(-2, 2)
        humidity = base_humidity + random.uniform(-5, 5)
        
        sensors[sensor_name] = SensorData(
            temperature=round(temp, 1),
            humidity=round(max(0, min(100, humidity)), 1)
        )
    
    # Créer la requête avec les données
    return ValuesRequest(
        average_temperature=round(base_temp, 1),
        average_humidity=round(base_humidity, 1),
        fan_status=base_temp > 25,
        humidifier_status=base_humidity < 50,
        numFailedSensors=random.randint(0, 1),
        sensors=sensors
    )


def generate_mock_sensor_history(hours: int = 48):
    """
    Génère un historique de données fictives multi-capteurs sur la période demandée
    """
    history = []
    now = datetime.datetime.now(timezone.utc)
    sensors = ["sensor_01", "sensor_02", "sensor_03"]
    
    # Générer des relevés par heure pour chaque capteur
    for i in range(hours, -1, -1):
        timestamp = (now - datetime.timedelta(hours=i)).isoformat()
        
        # Variation sinusoïdale de base pour la journée
        hour_offset = (hours - i) % 24
        daily_temp_cycle = 2.5 * math.sin((hour_offset - 8) * math.pi / 12)
        daily_humid_cycle = -5.0 * math.sin((hour_offset - 8) * math.pi / 12)
        
        for idx, sensor_name in enumerate(sensors):
            # Petite déviation par capteur
            sensor_offset_temp = (idx - 1) * 0.8
            sensor_offset_humid = (idx - 1) * -1.5
            
            temp = 22.5 + daily_temp_cycle + sensor_offset_temp + random.uniform(-0.5, 0.5)
            humid = 52.0 + daily_humid_cycle + sensor_offset_humid + random.uniform(-1.2, 1.2)
            
            history.append({
                "timestamp": timestamp,
                "temperature": round(temp, 1),
                "humidity": round(max(0.0, min(100.0, humid)), 1),
                "sensor": sensor_name
            })
    
    return history


def get_mock_dashboard_stats():
    """
    Retourne les stats d'un tableau de bord fictif
    """
    return {
        "total_readings": random.randint(1000, 10000),
        "average_temperature": round(random.uniform(18, 28), 1),
        "average_humidity": round(random.uniform(40, 65), 1),
        "active_sensors": random.randint(2, 5),
        "failed_sensors": random.randint(0, 1),
        "uptime_hours": random.randint(100, 1000),
    }


def get_mock_system_info():
    """
    Retourne des infos système fictives
    """
    return {
        "app_name": "Smartelia API",
        "version": "2.0.0",
        "environment": "development",
        "database_connected": True,
        "uptime_seconds": random.randint(3600, 86400),
        "last_update": datetime.datetime.now().isoformat(),
    }
