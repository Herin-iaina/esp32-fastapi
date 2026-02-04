#!/bin/bash
set -e

# Script d'entrée pour lancer soit l'API HTTP, soit le middleware MQTT
# Usage: MODE=http|mqtt

MODE=${MODE:-http}

echo "============================================"
echo "Smartelia - Mode: $MODE"
echo "============================================"

case "$MODE" in
    http|api|fastapi)
        echo "Démarrage de l'API FastAPI (HTTP)..."
        exec python run.py
        ;;
    mqtt|middleware)
        echo "Démarrage du middleware MQTT..."
        exec python mqtt_middleware.py
        ;;
    both)
        echo "Démarrage des deux services..."
        # Lancer le middleware MQTT en arrière-plan
        python mqtt_middleware.py &
        MQTT_PID=$!
        echo "Middleware MQTT démarré (PID: $MQTT_PID)"

        # Lancer l'API FastAPI au premier plan
        python run.py &
        API_PID=$!
        echo "API FastAPI démarrée (PID: $API_PID)"

        # Attendre les deux processus
        wait $MQTT_PID $API_PID
        ;;
    *)
        echo "Mode inconnu: $MODE"
        echo "Modes disponibles: http, mqtt, both"
        exit 1
        ;;
esac
