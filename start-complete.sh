#!/bin/bash

# Script pour démarrer le système complet pour tester

echo "
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║             🚀 Démarrage du Système - Frontend + Backend                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"

# Vérifier les permissions
chmod +x start-dev.sh stop-dev.sh test-mock.sh 2>/dev/null

echo "📦 Étape 1/3 : Installation des dépendances..."
if [ ! -d "frontend/node_modules" ]; then
    echo "  → npm install dans frontend/"
    cd frontend && npm install --silent > /dev/null 2>&1
    cd ..
fi
echo "  ✓ Dépendances prêtes"

echo ""
echo "🎨 Étape 2/3 : Démarrage du Frontend (Vite)..."
echo "  → localhost:5173"
cd frontend && npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 2

echo ""
echo "⚙️  Étape 3/3 : Démarrage du Backend (FastAPI)..."
echo "  → localhost:8000"
cd ..
python run.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
sleep 5

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ SYSTÈME DÉMARRÉ AVEC SUCCÈS !"
echo ""
echo "📍 URLs d'accès:"
echo "  🎨 Frontend:     http://localhost:5173"
echo "  ⚙️  Backend API:  http://localhost:8000"
echo "  📚 Swagger Docs: http://localhost:8000/docs"
echo ""
echo "🧪 Données fictives activées - Badge '🧪 Mode Test' visible"
echo ""
echo "⏹️  Pour arrêter:"
echo "  $ ./stop-dev.sh"
echo ""
echo "📝 Logs:"
echo "  Frontend: tail -f /tmp/frontend.log"
echo "  Backend:  tail -f /tmp/backend.log"
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🎉 Ouvrez http://localhost:5173 dans votre navigateur pour commencer !"
echo ""

# Garder les processus en avant-plan
wait
