# 🔧 Dépannage - Système d'Incubation

## 🆘 Problèmes Courants

### Application ne charge pas

#### ❌ "Connection refused" sur http://localhost:8000

**Cause**: Les services ne sont pas en cours d'exécution

**Solution**:
```bash
docker compose up -d
docker compose logs -f
```

#### ❌ Page blanche ou "Cannot GET /"

**Cause**: Le frontend n'a pas été compilé

**Solution**:
```bash
cd frontend
npm install
npm run build
cd ..
docker compose restart backend
```

#### ❌ Erreur CORS

**Cause**: Navigateur bloque les requêtes cross-origin

**Solution**:
- Vérifier que l'URL est http:// (pas https://)
- Vérifier que frontend et backend tournent sur le même port (production)
- Pour développement local: utiliser les ports différents (5173 frontend, 8000 backend)

---

### Authentification

#### ❌ "Invalid credentials"

**Cause possible 1**: Mauvais mot de passe
- Vérifier: `admin` / `test123456`
- Attention: Majuscules/minuscules comptent!

**Cause possible 2**: Utilisateur inexistant
- Vérifier en base de données:
```bash
docker exec esp32-db psql -U user -d smartelia_db -c \
  "SELECT user_name, status FROM login;"
```

**Solution**: Créer l'utilisateur admin
```bash
docker exec esp32-db psql -U user -d smartelia_db << 'EOF'
INSERT INTO login (user_name, password, mail_id, status) VALUES
('admin', '$2b$12$1o6AivzrWUHg2gLpMyQtqudLlfWow18z1P7UZV/JJUzSu9wAI94tm', 
 'admin@smartelia.local', true);
EOF
```

#### ❌ Token JWT expiré

**Cause**: Token d'authentification a expiré

**Solution**: Se déconnecter et se reconnecter
```bash
localStorage.removeItem('auth_token')  # Dans la console du navigateur
```

---

### Base de Données

#### ❌ "Connection refused" sur PostgreSQL

**Cause**: PostgreSQL n'est pas en cours d'exécution

**Solution**:
```bash
docker compose up -d esp32-db
docker compose logs esp32-db
```

#### ❌ "database does not exist: smartelia_db"

**Cause**: Base de données non créée

**Solution**:
```bash
docker exec esp32-db psql -U user -c "CREATE DATABASE smartelia_db;"
docker compose restart backend
```

#### ❌ Table "parameter_data" inexistante

**Cause**: Schéma de base non initialisé

**Solution**:
```bash
docker exec esp32-db psql -U user -d smartelia_db << 'EOF'
CREATE TABLE IF NOT EXISTS parameter_data (
  id SERIAL PRIMARY KEY,
  espece VARCHAR(50) DEFAULT 'poule',
  timetoclose INTEGER DEFAULT 21,
  temp_incubation NUMERIC(5,2) DEFAULT 37.5,
  humidity_target NUMERIC(5,2) DEFAULT 60,
  rotation_count INTEGER DEFAULT 5,
  user_id INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
EOF
```

---

### Performance

#### ⚠️ L'application est lente

**Cause possible**: Les conteneurs manquent de ressources

**Solution**:
```bash
# Vérifier l'utilisation des ressources
docker stats

# Augmenter les ressources Docker Desktop
# Docker → Preferences → Resources → Memory/CPU

# Ou nettoyer les données anciennes
docker compose down -v
docker system prune -a
docker compose up -d
```

#### ⚠️ Graphiques ne s'affichent pas

**Cause**: Données manquantes dans les capteurs

**Vérifier**:
```bash
docker exec esp32-db psql -U user -d smartelia_db -c \
  "SELECT COUNT(*) FROM data_temp;"
```

**Solution**: 
- Attendre que les capteurs envoient des données
- Ou insérer des données fictives (voir TEST_PLAN.md)

---

### Frontend

#### ❌ "Cannot find module '..'"

**Cause**: Les dépendances npm ne sont pas installées

**Solution**:
```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

#### ❌ Styles CSS ne s'appliquent pas

**Cause**: Le mode sombre a changé les variables CSS

**Solution**:
```javascript
// Dans la console du navigateur
document.documentElement.classList.remove('dark')
localStorage.setItem('darkMode', 'false')
location.reload()
```

#### ❌ Les paramètres ne se sauvegardent pas

**Cause possible 1**: Pas connecté
- Vérifier qu'un utilisateur est connecté

**Cause possible 2**: Token expiré
- Se déconnecter et reconnecter

**Cause possible 3**: Erreur API
- Vérifier les logs du backend:
```bash
docker compose logs -f backend
```

---

### Backend

#### ❌ "ModuleNotFoundError: No module named '...'"

**Cause**: Les dépendances Python ne sont pas installées

**Solution**:
```bash
docker compose down
docker compose build --no-cache backend
docker compose up -d
```

#### ❌ "Error binding to port 8000"

**Cause**: Un autre processus utilise le port 8000

**Solution - Option 1**: Arrêter les services existants
```bash
docker compose down
docker compose up -d
```

**Solution - Option 2**: Utiliser un autre port
```bash
# Modifier docker-compose.yml:
# ports:
#   - "8001:8000"
docker compose up -d
# Accès: http://localhost:8001
```

#### ❌ "FATAL: Ident authentication failed"

**Cause**: Erreur d'authentification PostgreSQL

**Solution**: Vérifier les credentials dans docker-compose.yml
```bash
# Backend doit utiliser:
# - POSTGRES_USER=user
# - POSTGRES_PASSWORD=password
# - POSTGRES_DB=smartelia_db
```

---

## 🔍 Déboguer Pas à Pas

### 1. Vérifier que Docker fonctionne
```bash
docker ps  # Liste tous les conteneurs
```

### 2. Vérifier la santé des services
```bash
curl http://localhost:8000/api/health
```

### 3. Vérifier la base de données
```bash
docker exec esp32-db psql -U user -d smartelia_db \
  -c "SELECT 1;"  # Connexion simple
```

### 4. Voir les logs
```bash
docker compose logs -f backend    # Backend
docker compose logs -f postgres   # Database
docker compose logs -f esp32-frontend  # Frontend
```

### 5. Tester l'API directement
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123456"}'

# Récupérer paramètres
curl http://localhost:8000/api/parameter
```

### 6. Vérifier les fichiers de logs
```bash
# Logs Docker
docker compose logs backend > logs/backend.log

# Logs filesystem (dans les conteneurs)
docker exec esp32-backend tail -f /app/logs/app.log
```

---

## 📞 Support

### Avant de contacter le support

1. ✅ Lancer `docker compose down -v` et `docker compose up -d`
2. ✅ Vérifier que tous les conteneurs sont "Up"
3. ✅ Vérifier les logs: `docker compose logs -f`
4. ✅ Consulter ce fichier de dépannage
5. ✅ Essayer dans un navigateur privé/incognito

### Informations à fournir

Quand vous demandez de l'aide:
```bash
# Collecter les infos de débogage
docker compose ps
docker compose logs > logs.txt
curl http://localhost:8000/api/health > health.json

# Fournir ces fichiers et une description du problème
```

---

## 🧹 Nettoyage Complet

Si rien ne fonctionne, réinitialiser complètement:

```bash
# Arrêter tous les services
docker compose down -v

# Nettoyer les images non utilisées
docker system prune -a

# Reconstruire tout from scratch
docker compose build --no-cache
docker compose up -d

# Vérifier
docker compose ps
curl http://localhost:8000/api/health
```

---

**Dernière mise à jour**: 28 Janvier 2025
