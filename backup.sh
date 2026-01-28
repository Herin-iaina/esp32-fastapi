#!/bin/bash

# 💾 Backup Script - Système d'Incubation v2.0
# Sauvegarde la base de données PostgreSQL

set -e  # Exit on error

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/smartelia_db_$TIMESTAMP.sql"
CONTAINER_NAME="esp32-db"
DB_NAME="smartelia_db"
DB_USER="user"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}💾 Backup Database - Système d'Incubation v2.0${NC}"
echo "================================================"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if Docker container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ Erreur: Conteneur $CONTAINER_NAME n'est pas en cours d'exécution${NC}"
    exit 1
fi

echo -e "${YELLOW}⏳ Sauvegarde en cours...${NC}"
echo "Destination: $BACKUP_FILE"

# Execute backup
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup réussi!${NC}"
    echo "Fichier: $BACKUP_FILE"
    echo "Taille: $SIZE"
    
    # Keep only last 10 backups
    echo -e "${YELLOW}🧹 Nettoyage des anciens backups...${NC}"
    cd "$BACKUP_DIR"
    ls -t smartelia_db_*.sql | tail -n +11 | xargs rm -f 2>/dev/null || true
    echo -e "${GREEN}✅ Nettoyage fait (10 derniers backups conservés)${NC}"
else
    echo -e "${RED}❌ Erreur: Backup n'a pas pu être créé${NC}"
    exit 1
fi

echo "================================================"
echo -e "${GREEN}✅ Opération terminée avec succès!${NC}"
