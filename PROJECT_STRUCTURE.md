# 📁 Arborescence Complète - Système d'Incubation v2.0

```
projet_esp_32/
│
├── 📚 DOCUMENTATION (10 fichiers)
│   ├── README.md                    ← Vue d'ensemble projet
│   ├── QUICK_START.md               ← Points clés session
│   ├── USER_GUIDE.md                ← Guide utilisateur complet
│   ├── TEST_PLAN.md                 ← Plan de test (24 tests)
│   ├── CHANGELOG.md                 ← Historique versions
│   ├── CONFIGURATION.md             ← Installation & config
│   ├── TROUBLESHOOTING.md           ← Dépannage & FAQ
│   ├── ARCHITECTURE.md              ← Design technique
│   ├── SESSION_SUMMARY.md           ← Résumé modifications
│   └── DOCUMENTATION.md             ← Index documentation
│
├── 🚀 SCRIPTS (3 fichiers)
│   ├── start.sh                     ← Démarrer services
│   ├── stop.sh                      ← Arrêter services
│   └── verify.sh                    ← Vérifier installation
│
├── 🐳 DOCKER & DEPLOYMENT
│   ├── docker-compose.yml           ← Orchestration 3 services
│   ├── Dockerfile                   ← Backend container
│   ├── frontend/Dockerfile          ← Frontend container
│   └── requirements.txt             ← Dependencies Python
│
├── 🐍 BACKEND (FastAPI - Python)
│   ├── run.py                       ← Entry point
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                  ← Auth endpoints (LOGIN)
│   │   ├── parameter.py             ← Parameter endpoints (GET/POST)
│   │   ├── sensor_values.py         ← Sensor data endpoints
│   │   ├── system.py                ← System endpoints
│   │   └── pages.py                 ← Page serving
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── login.py                 ← LoginModel + auth functions
│   │   └── sensor.py                ← SensorModel
│   │
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── database_configuration.py ← SQLAlchemy setup
│   │   ├── post_temp_humidity.py    ← Data processing
│   │   └── post_temp_humidity2.py   ← Data processing v2
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                ← Configuration settings
│   │   ├── logging.py               ← Logger setup
│   │   └── security.py              ← JWT + auth utilities
│   │
│   └── logs/
│       └── app.log                  ← Application logs
│
├── ⚛️ FRONTEND (React - TypeScript)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   │
│   ├── src/
│   │   ├── main.tsx                 ← App entry point
│   │   ├── App.tsx                  ← Root component
│   │   ├── App.css                  ← Dark mode CSS variables
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx        ← Charts & sensors
│   │   │   ├── Dashboard.css
│   │   │   ├── Settings.tsx         ← Login + incubation config
│   │   │   └── Settings.css         ← Settings styling
│   │   │
│   │   ├── store/
│   │   │   ├── appStore.ts          ← Zustand (Auth + Theme)
│   │   │   └── sensorStore.ts       ← Zustand (Sensors)
│   │   │
│   │   ├── components/
│   │   │   ├── SensorCard.tsx
│   │   │   └── ChartComponent.tsx
│   │   │
│   │   └── assets/
│   │       └── styles.css
│   │
│   ├── dist/                        ← Production build
│   │   ├── index.html
│   │   ├── assets/
│   │   │   ├── index-*.css
│   │   │   └── index-*.js
│   │   └── vite.svg
│   │
│   └── node_modules/                ← Dependencies
│
├── 🐘 DATABASE (PostgreSQL)
│   └── smartelia_db
│       ├── login                    ← Users table
│       ├── parameter_data           ← Incubation settings
│       ├── data_temp                ← Sensor measurements
│       └── stepper                  ← Motor status
│
├── 📁 OTHER
│   ├── explication_code/            ← Explanations
│   │   └── [...documentation...]
│   │
│   ├── static/                      ← Legacy (not used)
│   │   ├── app.js
│   │   ├── style.css
│   │   ├── bootstrap-icons/
│   │   └── ...
│   │
│   ├── templates/                   ← Legacy (not used)
│   │   ├── layout.html
│   │   ├── main.html
│   │   └── ...
│   │
│   ├── old/                         ← Archive
│   │   ├── main.py
│   │   ├── best_of.py
│   │   └── ...
│   │
│   ├── fastapi/                     ← Venv (not included in git)
│   │   ├── bin/
│   │   └── lib/
│   │
│   └── __pycache__/                 ← Python cache (ignored)
│
└── 📄 ROOT CONFIGURATION
    ├── .gitignore
    ├── .dockerignore
    └── .env (optional)
```

---

## 🔑 Fichiers Critiques (À Connaître)

### Pour l'Utilisateur
1. **[USER_GUIDE.md](USER_GUIDE.md)** - Comment utiliser l'appli
2. **[http://localhost:8000](http://localhost:8000)** - L'application elle-même

### Pour le Développeur
1. **[run.py](run.py)** - Point d'entrée FastAPI
2. **[routers/auth.py](routers/auth.py)** - Authentification
3. **[routers/parameter.py](routers/parameter.py)** - Paramètres incubateur
4. **[frontend/src/pages/Settings.tsx](frontend/src/pages/Settings.tsx)** - Formulaire config
5. **[frontend/src/store/appStore.ts](frontend/src/store/appStore.ts)** - State global

### Pour l'Admin
1. **[docker-compose.yml](docker-compose.yml)** - Configuration Docker
2. **[CONFIGURATION.md](CONFIGURATION.md)** - Variables d'env
3. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Dépannage

---

## 📊 Taille des Fichiers (Estimation)

| Type | Fichiers | Taille |
|------|----------|--------|
| Documentation | 10 | ~80 KB |
| Backend Python | 15 | ~150 KB |
| Frontend TypeScript | 20 | ~200 KB |
| Frontend Build | ~50 | ~600 KB |
| Docker Images | 3 | ~2 GB (runtime) |
| Database | 1 | ~100 MB (data) |

---

## 🔄 Fichiers Modifiés dans cette Session

```
MODIFIED:
├── routers/parameter.py          (180 lines - DB persistence)
├── routers/auth.py               (60 lines - JWT login)
├── frontend/src/pages/Settings.tsx (180 lines - UI form)
├── frontend/src/pages/Settings.css (270 lines - dark mode)
├── frontend/src/App.tsx          (15 lines - theme integration)
├── frontend/src/App.css          (150 lines - theme variables)
├── requirements.txt              (added pyjwt)
└── README.md                     (updated with v2.0 features)

CREATED:
├── frontend/src/store/appStore.ts     (30 lines - Zustand)
├── start.sh                      (50 lines - automation)
├── stop.sh                       (20 lines - automation)
├── verify.sh                     (150 lines - verification)
├── USER_GUIDE.md                 (300 lines)
├── TEST_PLAN.md                  (200 lines)
├── CHANGELOG.md                  (250 lines)
├── TROUBLESHOOTING.md            (400 lines)
├── CONFIGURATION.md              (300 lines)
├── ARCHITECTURE.md               (400 lines)
├── SESSION_SUMMARY.md            (300 lines)
├── QUICK_START.md                (250 lines)
└── DOCUMENTATION.md              (200 lines)

TOTAL:
≈ 4,000 lines of new/modified code
≈ 15,000 words of documentation
```

---

## 🎯 Fichiers à Consulter Pour...

### "Comment ça marche?"
→ [ARCHITECTURE.md](ARCHITECTURE.md)

### "Je veux l'utiliser"
→ [USER_GUIDE.md](USER_GUIDE.md)

### "Ça ne marche pas"
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### "Je veux développer"
→ [ARCHITECTURE.md](ARCHITECTURE.md) + code source

### "Je dois déployer"
→ [CONFIGURATION.md](CONFIGURATION.md)

### "Je dois tester"
→ [TEST_PLAN.md](TEST_PLAN.md)

### "Quoi de neuf?"
→ [CHANGELOG.md](CHANGELOG.md)

### "Resumerézzézzé?"
→ [QUICK_START.md](QUICK_START.md)

---

## 🔗 Relations entre Fichiers

```
FRONTEND FLOW:
App.tsx
├─ imports: appStore
├─ imports: Dashboard
└─ imports: Settings
    ├─ imports: appStore
    ├─ calls: /api/auth/login
    └─ calls: /api/parameter

BACKEND FLOW:
run.py
├─ imports: routers/auth
├─ imports: routers/parameter
└─ imports: routers/sensor_values
    └─ imports: models/login
        ├─ bcrypt (password hashing)
        └─ SQLAlchemy (ORM)

DATABASE SCHEMA:
docker-compose.yml
└─ esp32-db (PostgreSQL)
   ├─ login table
   ├─ parameter_data table
   ├─ data_temp table
   └─ stepper table
```

---

## 📦 Dépendances Principales

### Frontend
- react@18
- typescript
- vite
- recharts (graphiques)
- zustand (state)
- lucide-react (icons)

### Backend
- fastapi==0.104.1
- sqlalchemy==2.0.43
- pydantic==2.5.0
- pyjwt==2.8.1
- bcrypt==4.3.0
- psycopg2-binary==2.9.9

### Infrastructure
- postgresql:15-alpine
- nginx:latest
- docker
- docker-compose

---

**Dernière mise à jour**: 28 Janvier 2025
**Version**: 2.0.0
