#!/bin/bash

# Script d'arrêt - Système d'Incubation
# Usage: ./stop.sh

echo "🛑 Arrêt du Système d'Incubation..."
echo ""

docker compose down

echo ""
echo "✅ Services arrêtés avec succès"
echo ""
echo "💾 Les données ont été sauvegardées en PostgreSQL"
echo "🔄 Pour redémarrer: ./start.sh"
echo ""
