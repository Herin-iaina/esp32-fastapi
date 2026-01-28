# -*- coding: utf-8 -*-
"""
Module de données fictives pour les tests
Génère des données réalistes de capteurs
"""
import datetime
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


def generate_mock_sensor_history(hours: int = 24):
    """
    Génère un historique de données fictives
    """
    history = []
    now = datetime.datetime.now()
    
    for i in range(hours):
        timestamp = now - datetime.timedelta(hours=hours - i)
        
        # Variation sinusoïdale pour un pattern réaliste
        base_temp = 22 + 3 * (i / hours)
        base_humidity = 50 + 10 * (i / hours)
        
        history.append({
            "timestamp": timestamp.isoformat(),
            "temperature": round(base_temp + random.uniform(-1, 1), 1),
            "humidity": round(base_humidity + random.uniform(-2, 2), 1),
            "sensor": "sensor_01"
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
