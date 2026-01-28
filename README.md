# 🐔 Système d'Incubation - Monitoring des Capteurs v2.0

Système de surveillance en temps réel pour incubateurs avec capteurs ESP32. Architecture **frontend et backend séparés** avec authentification, persistance en base de données, et interface responsive.

## ✨ Caractéristiques

- ✅ **Frontend moderne** : React 18 + TypeScript + Vite
- ✅ **Authentification JWT** : Login sécurisé avec tokens
- ✅ **Mode Sombre** : Interface adaptable avec thème
- ✅ **Paramètres persistants** : Sauvegardés en PostgreSQL
- ✅ **Graphiques temps réel** : Recharts (temperature & humidité)
- ✅ **API REST** : FastAPI robuste et performante
- ✅ **Base de données** : PostgreSQL avec historique
- ✅ **Containerisé** : Docker & Docker Compose
- ✅ **Responsive Design** : Mobile & Desktop

## 📋 Architecture

```
┌─────────────────────────────────────────────────┐
│          Frontend (React + Vite)                │
│      http://localhost:5173                      │
│  - Dashboard interactif                         │
│  - Graphiques Recharts                          │
│  - Paramètres système                           │
└──────────────────┬──────────────────────────────┘
                   │ API HTTP
┌──────────────────▼──────────────────────────────┐
│       Backend (FastAPI)                         │
│      http://localhost:8000                      │
│  - REST API complète                            │
│  - Authentification JWT                         │
│  - Gestion des capteurs                         │
└──────────────────┬──────────────────────────────┘
                   │ SQL
┌──────────────────▼──────────────────────────────┐
│       Database (PostgreSQL)                     │
│      localhost:5432                             │
└─────────────────────────────────────────────────┘
```

## 🚀 Démarrage Rapide

### Avec Docker (Recommandé) ✨

```bash
# Démarrer tous les services (Backend + Frontend + Database)
docker compose up -d

# Vérifier l'état
docker compose ps
```

Accès:
- **Application** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs
- **Credentials** : admin / test123456

### Installation Locale (développement)

#### Backend

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python run.py
```

#### Frontend (développement)

```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

## 📁 Structure du Projet

```
projet_esp_32/
├── backend/
│   ├── apps/                 # Logique métier
│   ├── routers/              # Routes API
│   ├── models/               # Models Pydantic & SQLAlchemy
│   ├── core/                 # Configuration, logging
│   ├── run.py                # Point d'entrée FastAPI
│   └── requirements.txt       # Dépendances Python
│
├── frontend/                 # Application React
│   ├── src/
│   │   ├── components/       # Composants réutilisables
│   │   ├── pages/            # Pages (Dashboard, Settings)
│   │   ├── store/            # Zustand store
│   │   └── App.tsx           # Composant root
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
│
├── docker-compose.yml        # Orchestration des services
├── start-dev.sh              # Script de démarrage
└── stop-dev.sh               # Script d'arrêt
```

## 🛠 Technologies

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool ultra-rapide
- **Recharts** - Graphiques interactifs
- **Zustand** - State management minimaliste
- **Lucide Icons** - Icônes modernes
- **CSS3** - Styles modernes (Flexbox, Grid)

### Backend
- **FastAPI** - Framework web async
- **SQLAlchemy** - ORM robuste
- **Pydantic** - Validation de données
- **PostgreSQL** - Base de données
- **Python 3.11+** - Langage

## 🎨 Graphiques sans Chart.js

Le projet utilise **Recharts** à la place de Chart.js pour:
- ✅ Meilleure performance
- ✅ Composants React natifs
- ✅ Plus facile à personnaliser
- ✅ Design moderne par défaut

Types de graphiques inclus:
- 📊 Graphiques en barres (Température/Humidité)
- 🎯 Graphiques en radar (Analyse des capteurs)
- 📈 Extensible pour ajouter LineCharts, AreaCharts, etc.

## � Authentification & Sécurité

### Login
```bash
POST /api/auth/login
{
  "username": "admin",
  "password": "test123456"
}
```

Réponse:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "admin",
  "user_id": 1
}
```

### Protection des paramètres
- ✅ Token JWT requis pour modifier les paramètres
- ✅ Roles utilisateurs supportés (future)
- ✅ Mots de passe hachés avec bcrypt

## 🐔 Paramètres d'Incubation

Le système gère les paramètres spécifiques pour chaque espèce:

### Poule
- **Durée**: 21 jours
- **Température**: 37.5°C (±0.2°C)
- **Humidité**: 40-50% (J1-J18), 70-75% (J19+)
- **Rotations**: 5+ par jour

### Canard
- **Durée**: 28 jours
- **Température**: 37.5°C (±0.2°C)
- **Humidité**: 40-50% (J1-J25), 75-80% (J26+)
- **Rotations**: 5+ par jour (arrêt J25)

### Dinde
- **Durée**: 28 jours
- **Température**: 37.5°C (±0.2°C)
- **Humidité**: 40-50% (J1-J20), 70% (J21+)
- **Rotations**: 5+ par jour

## 📊 Dashboard Temps Réel

### Graphiques Inclus
- 📈 **Historique Température** (dernières 24h)
- 💧 **Historique Humidité** (dernières 24h)
- ⏱️ **Compteur d'éclosion** (jours restants)
- 🔌 **État des capteurs**

### Mises à jour
- Chargement automatique toutes les 5 secondes
- Persistance des données en PostgreSQL
- Historique conservé (paramétrable)


### Paramètres
```http
GET /api/settings
POST /api/settings              # Mettre à jour
```

## 🔧 Configuration

Les variables d'environnement principales:

```env
# Backend
APP_DATABASE_URL=postgresql://user:password@db:5432/smartelia_db
APP_ENVIRONMENT=dev
CORS_ORIGINS=http://localhost:5173

# Frontend
VITE_API_URL=http://localhost:8000/api
```

## 📝 Logs & Debugging

```bash
# Voir tous les logs
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

## 🐛 Troubleshooting

### Port déjà utilisé
```bash
# Changer les ports dans docker-compose.yml
```

### Base de données non accessible
```bash
docker-compose logs db
# Réinitialiser: docker-compose down -v
```

### Frontend ne se connecte pas
- Vérifier CORS dans `run.py`
- Vérifier l'URL API dans `vite.config.ts`

## 🚀 Déploiement en Production

Pour la production:
1. Utiliser des images Docker optimisées
2. Configurer les variables d'environnement
3. Utiliser un reverse proxy (Nginx)
4. Activer HTTPS/SSL
5. Configurer les backups PostgreSQL

## 📖 Ressources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Recharts Documentation](https://recharts.org/)
- [Vite Documentation](https://vitejs.dev/)

## 📄 Licence

MIT

## ✉️ Support

Pour toute question ou problème, veuillez ouvrir une issue sur le repository.
    Edit `.env` if necessary (e.g., to change secrets or database credentials).

3.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4.  **Access the Application:**
    - **Dashboard**: [http://localhost:8000](http://localhost:8000)
    - **Settings**: [http://localhost:8000/settings](http://localhost:8000/settings)
    - **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Local Development (Without Docker)

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set Environment Variables:**
    Ensure your `.env` file is configured. You may need to run a local PostgreSQL instance and update `APP_DATABASE_URL`.

3.  **Run the Server:**
    ```bash
    python run.py
    ```

## Configuration

Configuration is managed via environment variables (see `.env.example`).
Key settings include:
- `APP_APP_NAME`: Name of the application.
- `APP_DATABASE_URL`: Database connection string.
- `APP_SECRET_KEY`: Secret key for security (must be 32+ chars).

## Project Layout

- `core/`: Core configuration and logging.
- `routers/`: API and Page routes.
- `templates/`: HTML templates (Jinja2).
- `static/`: Static assets (CSS, JS, Images).
- `docker/`: Docker related files.
