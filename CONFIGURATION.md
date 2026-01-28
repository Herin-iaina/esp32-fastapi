# Configuration - Système d'Incubation

## Variables d'Environnement

### Backend (.env ou docker-compose.yml)

```env
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=smartelia_db
DATABASE_URL=postgresql://user:password@esp32-db:5432/smartelia_db

# API
API_HOST=0.0.0.0
API_PORT=8000

# JWT
SECRET_KEY=your_secret_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=10080  # 7 days

# Logging
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:8000", "localhost"]

# App
APP_NAME=Smartelia API
ENABLE_DOCS=true  # Désactiver en production
```

### Frontend (.env.local)

```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Smartelia Incubation
```

## Paramètres par Défaut

### Poule
```json
{
  "espece": "poule",
  "timetoclose": 21,
  "temp_incubation": 37.5,
  "humidity_target": 60,
  "rotation_count": 5,
  "humidity_ranges": {
    "stage1_18": "40-50%",
    "stage19_21": "70-75%"
  }
}
```

### Canard
```json
{
  "espece": "canard",
  "timetoclose": 28,
  "temp_incubation": 37.5,
  "humidity_target": 60,
  "rotation_count": 5,
  "humidity_ranges": {
    "stage1_25": "40-50%",
    "stage26_28": "75-80%"
  }
}
```

### Dinde
```json
{
  "espece": "dinde",
  "timetoclose": 28,
  "temp_incubation": 37.5,
  "humidity_target": 60,
  "rotation_count": 5,
  "humidity_ranges": {
    "stage1_20": "40-50%",
    "stage21_28": "70%"
  }
}
```

## Configuration Docker

### Ports
- Frontend: 80 (nginx)
- Backend: 8000 (FastAPI)
- Database: 5432 (PostgreSQL)
- Base de données: 5433 (optionnel - seconde instance)

### Volumes
- `postgres_data`: Persistance PostgreSQL
- `logs`: Logs de l'application

### Networks
- `esp32-network`: Réseau interne (default bridge)

## Performance

### Recommandations
- **RAM**: Minimum 4GB (2GB par service)
- **CPU**: Minimum 2 cores (1 core par service)
- **Disk**: Minimum 5GB (1GB app + 4GB logs/data)

### Optimisations
```bash
# Limiter les ressources Docker
docker compose down
# Éditer docker-compose.yml:
# services:
#   backend:
#     mem_limit: 1024m
#     cpus: 0.5

docker compose up -d
```

## Sécurité

### Avant Production

1. **Changer les secrets**
   ```bash
   # Générer une nouvelle clé JWT
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Mettre à jour SECRET_KEY
   ```

2. **Changer les passwords**
   ```bash
   # Générer un nouveau password admin
   python3 << 'EOF'
   import bcrypt
   password = input("Nouveau password: ")
   hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
   print(f"Hash: {hashed}")
   EOF
   ```

3. **HTTPS**
   ```nginx
   # Ajouter SSL à nginx (docker-compose.yml)
   server {
     listen 443 ssl;
     ssl_certificate /etc/nginx/certs/cert.pem;
     ssl_certificate_key /etc/nginx/certs/key.pem;
   }
   ```

4. **Désactiver les docs API**
   ```env
   ENABLE_DOCS=false
   ```

## Backup & Restore

### Sauvegarde PostgreSQL
```bash
# Full backup
docker exec esp32-db pg_dump -U user smartelia_db > backup.sql

# Backup comprimé
docker exec esp32-db pg_dump -U user smartelia_db | gzip > backup.sql.gz
```

### Restauration
```bash
# Depuis un fichier SQL
docker exec -i esp32-db psql -U user smartelia_db < backup.sql

# Depuis un fichier comprimé
gunzip < backup.sql.gz | docker exec -i esp32-db psql -U user smartelia_db
```

## Monitoring

### Logs Application
```bash
# En direct
docker compose logs -f backend

# Sauvegarder dans un fichier
docker compose logs backend > logs/backend.log
```

### Métriques Docker
```bash
# Utilisation ressources
docker stats esp32-backend

# Informations conteneur
docker inspect esp32-backend
```

### Health Check
```bash
# API health
curl http://localhost:8000/api/health

# Database connectivity
docker exec esp32-db pg_isready -U user
```

## Upgrade

### De v1.0 à v2.0
```bash
# Backup data
docker exec esp32-db pg_dump -U user smartelia_db > backup_v1.sql

# Update application
git pull
docker compose down
docker compose build --no-cache
docker compose up -d

# Vérifier
bash verify.sh
```

---

**Dernière mise à jour**: 28 Janvier 2025
