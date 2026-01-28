#!/bin/bash

# Script pour lancer la version PRODUCTION (Frontend + Backend intégrés)

echo "
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                   🚀 PRODUCTION - Backend + Frontend                      ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"

# Vérifier si le build existe
if [ ! -d "frontend/dist" ]; then
    echo "❌ Erreur: frontend/dist n'existe pas"
    echo "   Compile d'abord avec: cd frontend && npm run build"
    exit 1
fi

echo "⏹️  Arrêt des services existants..."
killall python node 2>/dev/null
sleep 1

echo ""
echo "⚙️  Démarrage du Backend (FastAPI)..."
echo "  → http://localhost:8000"
cd /Users/arthur_smartelia/projet_esp_32 && python run.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
sleep 5

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ SYSTÈME PRODUCTION DÉMARRÉ !"
echo ""
echo "📍 URL d'accès:"
echo "  🌐 Application:  http://localhost:8000"
echo "  📚 Swagger:      http://localhost:8000/docs"
echo ""
echo "🧪 Données fictives activées en mode dev"
echo ""
echo "⏹️  Pour arrêter:"
echo "  $ killall python"
echo ""
echo "📝 Logs:"
echo "  Backend: tail -f /tmp/backend.log"
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🎉 Ouvrez http://localhost:8000 dans votre navigateur !"
echo ""

wait
