"""
MQTT Middleware - Bridge between ESP32 MQTT and FastAPI
Ce middleware:
1. Reçoit les données des capteurs via MQTT
2. Les envoie à l'API FastAPI
3. Récupère les commandes d'automation et les publie sur MQTT
"""

import json
import time
import logging
import asyncio
import threading
from datetime import datetime
from typing import Optional, Dict, Any

import paho.mqtt.client as mqtt
import requests
from dataclasses import dataclass, field

# ============== CONFIGURATION ==============

@dataclass
class MQTTConfig:
    """Configuration MQTT"""
    broker: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "fastapi_mqtt_middleware"
    keepalive: int = 60
    reconnect_delay: int = 5


@dataclass
class APIConfig:
    """Configuration API FastAPI"""
    base_url: str = "http://localhost:5000"
    api_key: str = "Votre_Cle_API"
    timeout: int = 10


@dataclass
class TopicsConfig:
    """Configuration des topics MQTT"""
    # Topics d'écoute (données des capteurs)
    sensor_data: str = "incubator/sensors/data"

    # Topics de publication (commandes d'automation)
    automation_status: str = "incubator/automation/status"
    automation_fan: str = "incubator/automation/fan"
    automation_humidifier: str = "incubator/automation/humidifier"
    automation_stepper: str = "incubator/automation/stepper"


# Configuration par défaut
MQTT_CONFIG = MQTTConfig()
API_CONFIG = APIConfig()
TOPICS_CONFIG = TopicsConfig()

# ============== LOGGING ==============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/mqtt_middleware.log')
    ]
)
logger = logging.getLogger('MQTTMiddleware')


# ============== MQTT MIDDLEWARE CLASS ==============

class MQTTMiddleware:
    """
    Middleware MQTT pour faire le pont entre ESP32 et FastAPI
    """

    def __init__(
        self,
        mqtt_config: MQTTConfig = None,
        api_config: APIConfig = None,
        topics_config: TopicsConfig = None
    ):
        self.mqtt_config = mqtt_config or MQTT_CONFIG
        self.api_config = api_config or API_CONFIG
        self.topics_config = topics_config or TOPICS_CONFIG

        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.running = False

        # Thread pour la boucle d'automation
        self.automation_thread: Optional[threading.Thread] = None
        self.automation_interval = 5  # secondes

        # Cache pour éviter les publications redondantes
        self._last_automation_status: Dict[str, Any] = {}

    def _create_client(self) -> mqtt.Client:
        """Crée et configure le client MQTT"""
        client = mqtt.Client(
            client_id=self.mqtt_config.client_id,
            protocol=mqtt.MQTTv311
        )

        # Callbacks
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_publish = self._on_publish

        # Authentification si configurée
        if self.mqtt_config.username:
            client.username_pw_set(
                self.mqtt_config.username,
                self.mqtt_config.password
            )

        # Last Will Testament (message envoyé si déconnexion brutale)
        client.will_set(
            "incubator/middleware/status",
            payload=json.dumps({"status": "offline", "timestamp": datetime.now().isoformat()}),
            qos=1,
            retain=True
        )

        return client

    def _on_connect(self, client, userdata, flags, rc):
        """Callback lors de la connexion au broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connecté au broker MQTT: {self.mqtt_config.broker}:{self.mqtt_config.port}")

            # S'abonner aux topics des capteurs
            client.subscribe(self.topics_config.sensor_data, qos=1)
            logger.info(f"Abonné au topic: {self.topics_config.sensor_data}")

            # Publier le statut online
            self._publish_middleware_status("online")
        else:
            logger.error(f"Échec connexion MQTT, code: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback lors de la déconnexion"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Déconnexion inattendue du broker MQTT (rc={rc})")
        else:
            logger.info("Déconnecté du broker MQTT")

    def _on_message(self, client, userdata, msg):
        """Callback lors de la réception d'un message"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            logger.debug(f"Message reçu sur {topic}: {payload[:100]}...")

            # Traiter les données des capteurs
            if topic == self.topics_config.sensor_data:
                self._handle_sensor_data(payload)

        except Exception as e:
            logger.error(f"Erreur traitement message: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback après publication réussie"""
        logger.debug(f"Message publié (mid={mid})")

    def _handle_sensor_data(self, payload: str):
        """
        Traite les données des capteurs reçues via MQTT
        et les envoie à l'API FastAPI
        """
        try:
            data = json.loads(payload)
            logger.info(f"Données capteurs reçues: T={data.get('average_temperature', 'N/A')}°C, "
                       f"H={data.get('average_humidity', 'N/A')}%")

            # Transformer les données pour l'API si nécessaire
            api_payload = self._transform_sensor_data(data)

            # Envoyer à l'API FastAPI
            success = self._send_to_api(api_payload)

            if success:
                logger.info("Données envoyées à l'API avec succès")
                # Récupérer et publier les commandes d'automation
                self._fetch_and_publish_automation()
            else:
                logger.warning("Échec envoi données à l'API")

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {e}")
        except Exception as e:
            logger.error(f"Erreur traitement données capteurs: {e}")

    def _transform_sensor_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforme les données MQTT au format attendu par l'API
        Format attendu par l'API:
        {
            "average_temperature": float,
            "average_humidity": float,
            "fan_status": bool,
            "humidifier_status": bool,
            "numFailedSensors": int,
            "sensor_1": {"temperature": float, "humidity": float},
            ...
        }
        """
        transformed = {
            "average_temperature": data.get("average_temperature", 0),
            "average_humidity": data.get("average_humidity", 0),
            "fan_status": data.get("fan_status", "OFF") == "ON" if isinstance(data.get("fan_status"), str) else data.get("fan_status", False),
            "humidifier_status": data.get("humidifier_status", "OFF") == "ON" if isinstance(data.get("humidifier_status"), str) else data.get("humidifier_status", False),
            "numFailedSensors": data.get("numFailedSensors", 0)
        }

        # Extraire les données individuelles des capteurs
        for key, value in data.items():
            if key.startswith("sensor_") and isinstance(value, dict):
                transformed[key] = {
                    "temperature": value.get("temperature", 0),
                    "humidity": value.get("humidity", 0)
                }

        return transformed

    def _send_to_api(self, data: Dict[str, Any]) -> bool:
        """Envoie les données à l'API FastAPI"""
        try:
            url = f"{self.api_config.base_url}/api/sensor/values"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_config.api_key
            }

            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=self.api_config.timeout
            )

            if response.status_code in (200, 201):
                logger.debug(f"API Response: {response.json()}")
                return True
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("Timeout lors de l'appel API")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Impossible de se connecter à l'API")
            return False
        except Exception as e:
            logger.error(f"Erreur appel API: {e}")
            return False

    def _fetch_and_publish_automation(self):
        """
        Récupère les commandes d'automation depuis l'API
        et les publie sur MQTT
        """
        try:
            # Récupérer le statut d'automation
            automation_status = self._get_automation_status()
            if automation_status:
                self._publish_automation_status(automation_status)

            # Récupérer la commande stepper
            stepper_status = self._get_stepper_status()
            if stepper_status:
                self._publish_stepper_command(stepper_status)

        except Exception as e:
            logger.error(f"Erreur récupération automation: {e}")

    def _get_automation_status(self) -> Optional[Dict[str, bool]]:
        """Récupère le statut d'automation depuis l'API"""
        try:
            url = f"{self.api_config.base_url}/api/sensor/automation/status"
            headers = {"x-api-key": self.api_config.api_key}

            response = requests.get(url, headers=headers, timeout=self.api_config.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erreur récupération automation status: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erreur API automation status: {e}")
            return None

    def _get_stepper_status(self) -> Optional[Dict[str, bool]]:
        """Récupère la commande stepper depuis l'API"""
        try:
            url = f"{self.api_config.base_url}/api/sensor/automation/stepper"
            headers = {"x-api-key": self.api_config.api_key}

            response = requests.get(url, headers=headers, timeout=self.api_config.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erreur récupération stepper status: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erreur API stepper status: {e}")
            return None

    def _publish_automation_status(self, status: Dict[str, bool]):
        """Publie le statut d'automation complet sur MQTT"""
        if not self.connected or not self.client:
            return

        # Vérifier si le statut a changé
        if status == self._last_automation_status.get('status'):
            logger.debug("Statut automation inchangé, pas de publication")
            return

        self._last_automation_status['status'] = status.copy()

        # Publier le statut complet
        payload = json.dumps(status)
        self.client.publish(
            self.topics_config.automation_status,
            payload,
            qos=1,
            retain=True
        )
        logger.info(f"Automation status publié: fan={status.get('fan')}, humidifier={status.get('humidifier')}")

        # Publier aussi les commandes individuelles
        self.client.publish(
            self.topics_config.automation_fan,
            json.dumps({"state": status.get("fan", False)}),
            qos=1
        )

        self.client.publish(
            self.topics_config.automation_humidifier,
            json.dumps({"state": status.get("humidifier", False)}),
            qos=1
        )

    def _publish_stepper_command(self, status: Dict[str, bool]):
        """Publie la commande stepper sur MQTT"""
        if not self.connected or not self.client:
            return

        stepper_active = status.get("stepper", False)

        # Vérifier si le statut a changé
        if stepper_active == self._last_automation_status.get('stepper'):
            return

        self._last_automation_status['stepper'] = stepper_active

        payload = json.dumps({"activate": stepper_active})
        self.client.publish(
            self.topics_config.automation_stepper,
            payload,
            qos=1
        )

        if stepper_active:
            logger.info("Commande stepper activée")

    def _publish_middleware_status(self, status: str):
        """Publie le statut du middleware"""
        if self.client:
            payload = json.dumps({
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
            self.client.publish(
                "incubator/middleware/status",
                payload,
                qos=1,
                retain=True
            )

    def _automation_loop(self):
        """
        Boucle d'automation qui récupère périodiquement
        les commandes de l'API et les publie sur MQTT
        """
        logger.info("Démarrage de la boucle d'automation")

        while self.running:
            if self.connected:
                self._fetch_and_publish_automation()

            time.sleep(self.automation_interval)

        logger.info("Arrêt de la boucle d'automation")

    def connect(self):
        """Connecte au broker MQTT"""
        try:
            self.client = self._create_client()
            self.client.connect(
                self.mqtt_config.broker,
                self.mqtt_config.port,
                self.mqtt_config.keepalive
            )
            logger.info(f"Connexion au broker {self.mqtt_config.broker}:{self.mqtt_config.port}...")
            return True
        except Exception as e:
            logger.error(f"Erreur connexion MQTT: {e}")
            return False

    def start(self):
        """Démarre le middleware"""
        if not self.client:
            if not self.connect():
                return False

        self.running = True

        # Démarrer la boucle réseau MQTT dans un thread
        self.client.loop_start()

        # Démarrer la boucle d'automation
        self.automation_thread = threading.Thread(target=self._automation_loop, daemon=True)
        self.automation_thread.start()

        logger.info("Middleware MQTT démarré")
        return True

    def stop(self):
        """Arrête le middleware"""
        self.running = False

        if self.client:
            self._publish_middleware_status("offline")
            self.client.loop_stop()
            self.client.disconnect()

        if self.automation_thread:
            self.automation_thread.join(timeout=5)

        logger.info("Middleware MQTT arrêté")

    def run_forever(self):
        """Exécute le middleware en continu"""
        if not self.start():
            logger.error("Impossible de démarrer le middleware")
            return

        try:
            while True:
                # Vérifier la connexion et reconnecter si nécessaire
                if not self.connected:
                    logger.warning("Déconnecté, tentative de reconnexion...")
                    time.sleep(self.mqtt_config.reconnect_delay)
                    self.connect()

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
        finally:
            self.stop()


# ============== MAIN ==============

def create_middleware_from_env() -> MQTTMiddleware:
    """
    Crée le middleware avec configuration depuis variables d'environnement
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    mqtt_config = MQTTConfig(
        broker=os.getenv("MQTT_BROKER", "localhost"),
        port=int(os.getenv("MQTT_PORT", "1883")),
        username=os.getenv("MQTT_USERNAME", ""),
        password=os.getenv("MQTT_PASSWORD", ""),
        client_id=os.getenv("MQTT_CLIENT_ID", "fastapi_mqtt_middleware")
    )

    api_config = APIConfig(
        base_url=os.getenv("API_BASE_URL", "http://localhost:5000"),
        api_key=os.getenv("API_KEY", "Votre_Cle_API")
    )

    topics_config = TopicsConfig(
        sensor_data=os.getenv("MQTT_TOPIC_SENSOR_DATA", "incubator/sensors/data"),
        automation_status=os.getenv("MQTT_TOPIC_AUTOMATION_STATUS", "incubator/automation/status"),
        automation_fan=os.getenv("MQTT_TOPIC_AUTOMATION_FAN", "incubator/automation/fan"),
        automation_humidifier=os.getenv("MQTT_TOPIC_AUTOMATION_HUMIDIFIER", "incubator/automation/humidifier"),
        automation_stepper=os.getenv("MQTT_TOPIC_AUTOMATION_STEPPER", "incubator/automation/stepper")
    )

    return MQTTMiddleware(mqtt_config, api_config, topics_config)


if __name__ == "__main__":
    import os

    # Créer le dossier logs si nécessaire
    os.makedirs("logs", exist_ok=True)

    print("=" * 50)
    print("MQTT Middleware - ESP32 <-> FastAPI Bridge")
    print("=" * 50)

    # Créer et démarrer le middleware
    middleware = create_middleware_from_env()

    print(f"Broker MQTT: {middleware.mqtt_config.broker}:{middleware.mqtt_config.port}")
    print(f"API FastAPI: {middleware.api_config.base_url}")
    print(f"Topic capteurs: {middleware.topics_config.sensor_data}")
    print("=" * 50)
    print("Démarrage du middleware... (Ctrl+C pour arrêter)")
    print()

    middleware.run_forever()
