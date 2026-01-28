#!/bin/bash

# 🔄 Restore Script - Système d'Incubation v2.0
# Restaure la base de données PostgreSQL depuis un backup

set -e  # Exit on error

CONTAINER_NAME="esp32-db"
DB_NAME="smartelia_db"
DB_USER="user"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Restore Database - Système d'Incubation v2.0${NC}"
echo "================================================"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Backups disponibles:${NC}"
    ls -lh ./backups/smartelia_db_*.sql 2>/dev/null | tail -5 || echo "❌ Aucun backup trouvé"
    echo ""
    echo -e "${BLUE}Usage: ./restore.sh <backup_file>${NC}"
    echo -e "${BLUE}Exemple: ./restore.sh ./backups/smartelia_db_20250128_120000.sql${NC}"
    exit 1
fi

BACKUP_FILE="$1"

# Validate backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Erreur: Fichier $BACKUP_FILE n'existe pas${NC}"
    exit 1
fi

# Check if Docker container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ Erreur: Conteneur $CONTAINER_NAME n'est pas en cours d'exécution${NC}"
    echo -e "${YELLOW}Démarrez le système avec: ./start.sh${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  ATTENTION: Ceci va REMPLACER la base de données actuelle${NC}"
echo "Fichier: $BACKUP_FILE"
echo "Taille: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo -n "Êtes-vous sûr? (tapez 'oui' pour confirmer): "
read -r CONFIRM

if [ "$CONFIRM" != "oui" ]; then
    echo -e "${RED}❌ Opération annulée${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⏳ Restauration en cours...${NC}"
echo "Cela peut prendre quelques minutes..."

# Restore from backup
cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Restauration réussie!${NC}"
    echo ""
    echo "Base de données restaurée avec succès"
    echo "Vérifiez les données:"
    echo "  docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c \"SELECT * FROM login LIMIT 5;\""
else
    echo -e "${RED}❌ Erreur lors de la restauration${NC}"
    exit 1
fi

echo "================================================"
echo -e "${GREEN}✅ Opération terminée!${NC}"
