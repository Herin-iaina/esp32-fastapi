#!/bin/bash

# Script pour tester l'application avec des données fictives

echo "
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║               🧪 TEST - Données Fictives (Mock Data)  🧪                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}1️⃣  Démarrage des services Docker...${NC}"
docker-compose up -d

echo -e "${YELLOW}⏳ Attente du démarrage du backend (10s)...${NC}"
sleep 10

# URLs
BACKEND_URL="http://localhost:8000"
API_HEALTH="$BACKEND_URL/api/health"
API_VALUES="$BACKEND_URL/api/sensor/values"
API_HISTORY="$BACKEND_URL/api/sensor/history"
FRONTEND_URL="http://localhost:5173"

echo -e "${BLUE}2️⃣  Test de santé du backend...${NC}"
curl -s "$API_HEALTH" | jq . || echo "❌ Backend pas encore prêt"

echo ""
echo -e "${BLUE}3️⃣  Test de récupération des données fictives...${NC}"
echo "GET $API_VALUES?mock=true"
curl -s "$API_VALUES?mock=true" | jq .

echo ""
echo -e "${BLUE}4️⃣  Test de l'historique fictif (24h)...${NC}"
echo "GET $API_HISTORY?hours=24&mock=true"
curl -s "$API_HISTORY?hours=24&mock=true" | jq '.data.total_points, .data.hours'

echo ""
echo -e "${GREEN}✅ Tests complétés!${NC}"
echo ""
echo -e "${BLUE}📍 URLs d'accès:${NC}"
echo -e "  ${GREEN}Frontend${NC}     → $FRONTEND_URL"
echo -e "  ${GREEN}Backend API${NC}  → $BACKEND_URL"
echo -e "  ${GREEN}Docs API${NC}     → $BACKEND_URL/docs"
echo -e "  ${GREEN}Health Check${NC} → $API_HEALTH"
echo ""
echo -e "${YELLOW}💡 Commandes utiles:${NC}"
echo "  Logs du backend:    docker-compose logs -f backend"
echo "  Logs du frontend:   docker-compose logs -f frontend"
echo "  Arrêter les services: docker-compose down"
echo ""
