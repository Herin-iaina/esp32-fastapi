#!/bin/bash

# Script de démarrage - Système d'Incubation
# Usage: ./start.sh

set -e

echo "🚀 Démarrage du Système d'Incubation..."
echo ""

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

echo "✅ Docker détecté"
echo ""

# Arrêter les conteneurs existants
echo "🛑 Arrêt des conteneurs existants..."
docker compose down -v 2>/dev/null || true
sleep 2

# Démarrer les services
echo "🔧 Démarrage des services..."
docker compose up -d

# Attendre que PostgreSQL soit prêt
echo "⏳ Attente de PostgreSQL..."
max_attempts=30
attempt=0
while ! docker exec esp32-db pg_isready -U user -d smartelia_db &>/dev/null; do
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ PostgreSQL n'est pas disponible après 30 tentatives"
        exit 1
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done

echo ""
echo "✅ PostgreSQL est prêt"
echo ""

# Attendre que le backend soit prêt
echo "⏳ Attente du Backend..."
attempt=0
while ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; do
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ Backend n'est pas disponible après 30 tentatives"
        exit 1
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done

echo ""
echo "✅ Backend est prêt"
echo ""

# Afficher un résumé
echo "=========================================="
echo "🎉 Système Démarré avec Succès!"
echo "=========================================="
echo ""
echo "📍 Accès:"
echo "   🌐 Application:  http://localhost:8000"
echo "   📚 API Docs:     http://localhost:8000/docs"
echo "   🐘 PostgreSQL:   localhost:5432"
echo ""
echo "🔐 Credentials:"
echo "   Username: admin"
echo "   Password: test123456"
echo ""
echo "📖 Documentation:"
echo "   - README.md (Documentation centralisée)"
echo "   - CONFIGURATION.md (Variables d'environnement et déploiement)"
echo ""
echo "🛑 Pour arrêter:"
echo "   docker compose down"
echo ""
echo "📊 Pour voir les logs:"
echo "   docker compose logs -f backend"
echo ""
