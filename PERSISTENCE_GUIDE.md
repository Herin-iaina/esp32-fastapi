# 💾 Persistance des Données - Redéploiement et Volumes

## ✅ BONNE NOUVELLE: Les Données Sont Persistantes!

Vos modifications manuelles à la base de données **SERONT CONSERVÉES** lors des redéploiements.

---

## 🔍 Pourquoi?

### Le Volume Docker `postgres_data`

Regardez le `docker-compose.yml`:

```yaml
volumes:
  postgres_data:              # ← Volume nommé
```

Et dans le service PostgreSQL:

```yaml
db:
  image: postgres:15-alpine
  volumes:
    - postgres_data:/var/lib/postgresql/data  # ← Données persistées ici
```

**Ce que cela signifie:**
- Les données PostgreSQL sont stockées dans un **volume Docker persistant**
- Ce volume existe **indépendamment** du conteneur
- Même si vous supprimez/redémarrez les conteneurs → **données intact**
- Même si vous redéployez → **données intactes**

---

## 📊 Flux de Données

### 1️⃣ Première Fois (`./start.sh`)
```
Docker Compose démarre
↓
PostgreSQL conteneur démarre
↓
Volume `postgres_data` créé (vide)
↓
BD initialisée (schéma créé)
↓
Admin user créé manuellement: admin/test123456
↓
Données sauvegardées dans volume
```

### 2️⃣ Redéploiement (`docker compose restart` ou `./stop.sh && ./start.sh`)
```
Docker Compose redémarre
↓
PostgreSQL conteneur redémarre
↓
Volume `postgres_data` RÉCUPÉRÉ (données existantes!)
↓
BD restaurée (toutes les données présentes!)
↓
Admin user toujours là
↓
Tous vos paramètres/configs intacts
```

### 3️⃣ Production (`docker compose down` puis `up`)
```
Services arrêtés
↓
Conteneurs supprimés
↓
Volume `postgres_data` CONSERVÉ ✅
↓
Redémarrage
↓
Volume reconnecté
↓
Données 100% intactes ✅
```

---

## ⚠️ Attention: Cas d'Exception

### ❌ Cela SUPPRIME les données:
```bash
docker compose down -v  # Le -v supprime les volumes!
```

### ✅ Cela CONSERVE les données:
```bash
docker compose down     # Sans -v (données sauvegardées)
docker compose up -d    # Redémarrage (données restaurées)
```

### ✅ Cela CONSERVE les données:
```bash
docker compose restart  # Redémarrage simple
docker compose stop     # Arrêt simple
```

---

## 🔍 Vérifier que Vos Données Existent

### Check 1: Vérifier le volume Docker
```bash
docker volume ls | grep postgres
# Doit afficher: projet_esp_32_postgres_data
```

### Check 2: Voir où sont les données
```bash
docker volume inspect projet_esp_32_postgres_data
# Voir: "Mountpoint": "/var/lib/docker/volumes/..."
```

### Check 3: Vérifier l'admin user après redéploiement
```bash
docker exec esp32-db psql -U user -d smartelia_db \
  -c "SELECT username, status FROM login WHERE username='admin';"
# Doit afficher: admin | t (active)
```

---

## 📋 Stratégies de Sécurité

### 1️⃣ Backups Réguliers (Recommandé pour Production)

```bash
# Backup la BD complète
docker exec esp32-db pg_dump -U user smartelia_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore depuis backup
docker exec -i esp32-db psql -U user smartelia_db < backup_20250128_120000.sql
```

### 2️⃣ Export des Paramètres Critiques

```bash
# Exporter les utilisateurs
docker exec esp32-db psql -U user -d smartelia_db \
  -c "COPY login TO STDOUT;" > login_backup.csv

# Exporter les paramètres
docker exec esp32-db psql -U user -d smartelia_db \
  -c "COPY parameter_data TO STDOUT;" > parameters_backup.csv
```

### 3️⃣ Script de Backup Automatique

Créez `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Backing up database..."
docker exec esp32-db pg_dump -U user smartelia_db > \
  $BACKUP_DIR/smartelia_db_$TIMESTAMP.sql

echo "Backup saved to: $BACKUP_DIR/smartelia_db_$TIMESTAMP.sql"
```

Exécutez quotidiennement:
```bash
crontab -e
# Ajouter: 0 2 * * * /Users/arthur_smartelia/projet_esp_32/backup.sh
```

---

## 🏭 Production: Checklist Persistance

- [x] Volume `postgres_data` existe dans docker-compose.yml
- [x] Database URL correcte (en .env ou hardcodée)
- [x] Credentials sécurisés (changer password par défaut!)
- [x] Backups programmés (quotidien)
- [x] Test de restore (vital!)
- [x] Monitoring (docker ps, logs, health check)
- [x] Disaster recovery plan (comment restaurer?)

---

## 📚 Documentation Associée

Pour plus d'infos sur:
- **Configuration persistance**: [CONFIGURATION.md](CONFIGURATION.md) (section Database)
- **Deployment**: [CONFIGURATION.md](CONFIGURATION.md) (section Production)
- **Troubleshooting données**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Backup/Restore**: [CONFIGURATION.md](CONFIGURATION.md) (section Backup)

---

## 💡 Réponse à Votre Question

**Q: Modifications manuelles = à refaire à chaque déploiement?**

**R: NON! ✅**

```
Scenario 1: ./stop.sh && ./start.sh
├─ Données: ✅ INTACTES

Scenario 2: docker compose restart
├─ Données: ✅ INTACTES

Scenario 3: Déploiement nouveau serveur (ATTENTION!)
├─ Besoin: ✅ Backup + Restore
├─ Données: ✅ MIGRÉES

Scenario 4: docker compose down -v (sans backup)
├─ Données: ❌ SUPPRIMÉES (catastrophe!)
├─ Récupération: ❌ Impossible (sans backup)
```

---

## ⚡ Quick Reference

| Action | Données Conservées? |
|--------|---------------------|
| `./start.sh` | ✅ Oui |
| `./stop.sh` | ✅ Oui (juste arrêt) |
| `docker compose restart` | ✅ Oui |
| `docker compose down` | ✅ Oui |
| `docker compose down -v` | ❌ Non! CATASTROPHE! |
| `docker volume rm` | ❌ Non! CATASTROPHE! |
| Redémarrage serveur | ✅ Oui (volume persistant) |
| Nouveau déploiement | ⚠️ Dépend du backup |

---

## 🎯 Conclusion

✅ **Vos modifications sont permanentes**
✅ **Redéploiements sans perte de données**
⚠️ **SAUF si vous utilisez `docker compose down -v`**
✅ **Mettez en place un backup régulier**

**Vous êtes sauvagé!** 🎉

Pour les backups en production, consultez [CONFIGURATION.md](CONFIGURATION.md) section "Backup & Restore".
