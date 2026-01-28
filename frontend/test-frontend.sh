#!/bin/bash

echo "
╔════════════════════════════════════════════════════════════════════════════╗
║                   🧪 TEST DU FRONTEND - RAPPORT                          ║
╚════════════════════════════════════════════════════════════════════════════╝
"

echo "📍 Vérification des services..."
echo ""

# Test du backend
echo "🔍 Backend API:"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  ✅ Backend running on http://localhost:8000"
    
    # Test des données fictives
    echo ""
    echo "  📊 Données fictives:"
    SENSOR_DATA=$(curl -s "http://localhost:8000/api/sensor/values?mock=true" | jq '.data.sensors | length' 2>/dev/null)
    if [ ! -z "$SENSOR_DATA" ]; then
        echo "    ✅ $SENSOR_DATA capteurs détectés"
    fi
else
    echo "  ❌ Backend NOT running (expected)"
fi

echo ""
echo "🔍 Frontend:"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "  ✅ Frontend running on http://localhost:5173"
else
    echo "  ⏳ Frontend not yet fully loaded (starting...)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🚀 POUR TESTER:"
echo "  1️⃣  Ouvrir http://localhost:5173 dans votre navigateur"
echo "  2️⃣  Vérifier que le dashboard se charge"
echo "  3️⃣  Chercher le badge '🧪 Mode Test'"
echo "  4️⃣  Vérifier les graphiques Recharts"
echo "  5️⃣  Attendre 10s pour voir l'auto-refresh"
echo ""
echo "📚 API Endpoints disponibles:"
echo "  • Health Check:  http://localhost:8000/api/health"
echo "  • Mock Data:     http://localhost:8000/api/sensor/values?mock=true"
echo "  • Mock History:  http://localhost:8000/api/sensor/history?hours=24&mock=true"
echo "  • Swagger Docs:  http://localhost:8000/docs"
echo ""
