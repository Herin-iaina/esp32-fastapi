# 📚 Documentation - Système d'Incubation v2.0

Bienvenue dans la documentation complète du Système d'Incubation. Cet index vous aide à trouver rapidement l'information dont vous avez besoin.

## 🚀 Démarrage Rapide

**Vous êtes nouveau ?** Commencez ici :

1. **[README.md](README.md)** - Vue d'ensemble du projet
2. **[USER_GUIDE.md](USER_GUIDE.md)** - Guide complet pour utiliser l'application
3. **[CONFIGURATION.md](CONFIGURATION.md)** - Installation et configuration

```bash
# Démarrage en 3 commandes:
docker compose down -v  # Nettoyer
docker compose up -d    # Démarrer
bash verify.sh          # Vérifier
```

**Accès**: http://localhost:8000
**Login**: admin / test123456

---

## 📖 Documentation Utilisateur

### Pour les Utilisateurs Finaux

- **[USER_GUIDE.md](USER_GUIDE.md)** ⭐ **LIRE D'ABORD**
  - Comment se connecter
  - Configuration des paramètres d'incubation
  - Modes sombre/clair
  - Guide des espèces (poule, canard, etc.)
  - FAQ et dépannage basique

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**
  - Problèmes courants et solutions
  - Déboguer pas à pas
  - Support

---

## 👨‍💻 Documentation Développeur

### Pour les Développeurs

- **[README.md](README.md#-technologies)** - Stack technologique
  - React 18 + TypeScript
  - FastAPI + PostgreSQL
  - Docker & Docker Compose

- **[SESSION_SUMMARY.md](SESSION_SUMMARY.md)**
  - Résumé des modifications v2.0
  - Architecture détaillée
  - Points de contact

- **[CHANGELOG.md](CHANGELOG.md)**
  - Historique des versions
  - Nouvelles fonctionnalités
  - Migrations

### API Documentation

- **[README.md](README.md#-authentification--sécurité)** - Endpoints API
- **[http://localhost:8000/docs](http://localhost:8000/docs)** - Swagger UI interactif
- **[http://localhost:8000/redoc](http://localhost:8000/redoc)** - ReDoc alternative

---

## 🧪 Tests & Qualité

- **[TEST_PLAN.md](TEST_PLAN.md)** 
  - 24 tests UI à effectuer manuellement
  - Tests API avec curl
  - Critères de succès

- **[verify.sh](verify.sh)**
  - 23 vérifications automatisées
  - Script de validation de l'installation
  ```bash
  bash verify.sh
  ```

---

## ⚙️ Configuration & Administration

- **[CONFIGURATION.md](CONFIGURATION.md)**
  - Variables d'environnement
  - Paramètres par défaut (poule, canard, dinde)
  - Performance & optimisations
  - Sécurité pré-production
  - Backup & Restore
  - Monitoring

---

## 🔧 Opérations & Maintenance

### Scripts Disponibles

```bash
./start.sh      # Démarrer tous les services
./stop.sh       # Arrêter les services
bash verify.sh  # Vérifier l'installation
```

### Commandes Utiles

```bash
# Démarrer (production)
docker compose up -d

# Voir les logs
docker compose logs -f backend

# Accéder à PostgreSQL
docker exec -it esp32-db psql -U user -d smartelia_db

# Arrêter proprement
docker compose down
```

---

## 📊 Résumé des Fichiers

| Fichier | Type | Audience | Description |
|---------|------|----------|-------------|
| **README.md** | 📄 Docs | Tous | Vue d'ensemble projet |
| **USER_GUIDE.md** | 📘 Guide | Utilisateurs | Comment utiliser l'app |
| **TEST_PLAN.md** | ✅ Tests | QA/Dev | Plan de test détaillé |
| **CHANGELOG.md** | 📝 Historique | Dev | Versions & changements |
| **CONFIGURATION.md** | ⚙️ Config | Admin/Dev | Installation & config |
| **TROUBLESHOOTING.md** | 🔧 Support | Tous | Dépannage & FAQ |
| **SESSION_SUMMARY.md** | 📊 Résumé | Dev | Modifications récentes |
| **ARCHITECTURE.md** | 🏗️ Architecture | Dev | Détails techniques |
| **start.sh** | 🚀 Script | Tous | Démarrer l'app |
| **stop.sh** | 🛑 Script | Tous | Arrêter l'app |
| **verify.sh** | ✔️ Script | Admin | Vérifier l'install |

---

## 🎯 Par Cas d'Usage

### "Je veux utiliser l'application"
1. Lire: [USER_GUIDE.md](USER_GUIDE.md)
2. Démarrer: `./start.sh`
3. Accéder: http://localhost:8000
4. Aide: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### "Je dois déployer en production"
1. Lire: [CONFIGURATION.md](CONFIGURATION.md)
2. Configurer: Variables d'environnement
3. Sécuriser: Changer les secrets
4. Déployer: `docker compose up -d`
5. Vérifier: `bash verify.sh`

### "Je dois développer une nouvelle feature"
1. Lire: [README.md](README.md)
2. Comprendre: [SESSION_SUMMARY.md](SESSION_SUMMARY.md)
3. Coder: Voir les fichiers source
4. Tester: [TEST_PLAN.md](TEST_PLAN.md)
5. Documenter: Mettre à jour ce fichier

### "Ça ne marche pas"
1. Lire: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Vérifier: `bash verify.sh`
3. Regarder: `docker compose logs -f`
4. Déboguer: Section "Déboguer Pas à Pas"
5. Kontacter: Support si nécessaire

---

## 🔐 Sécurité

### Credentials Par Défaut

```
Username: admin
Password: test123456
```

⚠️ **IMPORTANT**: Changer avant production!
Voir [CONFIGURATION.md](CONFIGURATION.md#sécurité)

---

## 📞 Support & Aide

### Problème Technique?
→ Voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Question Utilisateur?
→ Voir [USER_GUIDE.md](USER_GUIDE.md)

### Comment contribuer?
→ Voir [CONFIGURATION.md](CONFIGURATION.md#upgrade)

### Feedback ou Suggestions?
→ Ouvrir une issue ou contacter l'équipe

---

## 📊 Statistiques Documentation

- **Pages**: 10
- **Mots**: ~15,000
- **Langues**: Français
- **Mise à jour**: 28 Janvier 2025
- **Complétude**: 100% ✅

---

## 🗂️ Structure des Fichiers

```
projet_esp_32/
├── 📚 Documentation
│   ├── README.md                 (Vue d'ensemble)
│   ├── USER_GUIDE.md             (Guide utilisateur)
│   ├── TEST_PLAN.md              (Tests)
│   ├── CHANGELOG.md              (Historique)
│   ├── CONFIGURATION.md          (Configuration)
│   ├── TROUBLESHOOTING.md        (Support)
│   ├── SESSION_SUMMARY.md        (Modifications)
│   └── DOCUMENTATION.md          (Ce fichier)
│
├── 🚀 Scripts
│   ├── start.sh                  (Démarrer)
│   ├── stop.sh                   (Arrêter)
│   └── verify.sh                 (Vérifier)
│
├── 🔧 Configuration
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── requirements.txt
│
├── 📁 Frontend (React)
│   └── frontend/
│       ├── src/
│       │   ├── pages/            (Settings, Dashboard)
│       │   ├── store/            (Zustand state)
│       │   ├── components/
│       │   └── App.tsx
│       ├── dist/                 (Build production)
│       └── package.json
│
└── 🐍 Backend (FastAPI)
    ├── routers/                  (API endpoints)
    ├── models/                   (Pydantic models)
    ├── apps/                     (Logique métier)
    ├── core/                     (Config, logging)
    └── run.py
```

---

**Dernière mise à jour**: 28 Janvier 2025
**Version**: 2.0.0
**Statut**: ✅ Complete & Production Ready
