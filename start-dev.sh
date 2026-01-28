#!/bin/bash

echo "🚀 Démarrage du système ESP32 Sensor Monitoring..."
echo ""

# Vérifier si Docker est disponible
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker."
    exit 1
fi

echo "📦 Démarrage des services Docker..."
docker-compose up -d

echo "⏳ Attente du démarrage des services..."
sleep 3

echo ""
echo "✅ Services démarrés !"
echo ""
echo "URLs d'accès:"
echo "  🎨 Frontend:  http://localhost:5173"
echo "  ⚙️  Backend:   http://localhost:8000"
echo "  📚 Docs API:  http://localhost:8000/docs"
echo "  🗄️  Database: localhost:5432"
echo ""
echo "Pour arrêter: docker-compose down"
echo "Pour voir les logs: docker-compose logs -f"
