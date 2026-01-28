# ESP32 Sensor Monitoring System - Frontend

## Installation

```bash
cd frontend
npm install
```

## Développement

```bash
npm run dev
```

Le frontend sera disponible sur `http://localhost:5173`

## Build

```bash
npm run build
```

## Technologies

- **React 18** - Framework UI
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Recharts** - Graphiques interactifs (pas de Chart.js)
- **Zustand** - State management
- **Lucide Icons** - Icônes modernes
- **Axios** - HTTP client

## Structure du projet

```
frontend/
├── src/
│   ├── components/      # Composants réutilisables
│   ├── pages/          # Pages principales
│   ├── store/          # Zustand stores
│   ├── App.tsx         # Composant principal
│   └── main.tsx        # Entry point
├── public/             # Assets statiques
├── vite.config.ts      # Config Vite
├── tsconfig.json       # Config TypeScript
└── package.json
```

## API

Le frontend se connecte au backend FastAPI sur `/api`:

- `GET /api/health` - Vérification de santé
- `POST /api/auth/login` - Authentification
- `GET /api/sensor/values` - Dernières données
- `POST /api/settings` - Sauvegarder les paramètres
