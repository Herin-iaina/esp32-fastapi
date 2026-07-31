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

## Logging et Debugging

### Vue d'ensemble

Le frontend intègre un système de logging complet pour tracer les interactions, les appels API et les erreurs.
Ce système fonctionne avec un logger global exporté dans `frontend/src/utils/logger.ts` et un hook React `useLogger`.
Il permet aussi d'afficher un panneau de debug en temps réel et d'exporter les logs en JSON.

### Fichiers principaux

- `frontend/src/utils/logger.ts` : implémentation du logger global
- `frontend/src/hooks/useLogger.ts` : hook React recommandé
- `frontend/src/components/DebugPanel.tsx` : panneau de débogage visuel
- `frontend/src/components/DebugPanel.css` : styles du panneau

### Comment utiliser

#### Option 1 — Hook recommandé

```tsx
import { useLogger } from './hooks/useLogger'

function MonComposant() {
  const { logButtonClick, logInfo, logError } = useLogger('MonComposant')

  const handleClick = () => {
    logButtonClick('Mon Bouton', { details: 'optionnelles' })
  }

  return <button onClick={handleClick}>Cliquer</button>
}
```

#### Option 2 — Logger direct

```tsx
import { logger } from './utils/logger'

function MonComposant() {
  const handleClick = () => {
    logger.logButtonClick('Mon Bouton', 'MonComposant', { id: 123 })
  }

  return <button onClick={handleClick}>Cliquer</button>
}
```

### Debugging dans la console

Ouvrez la console JavaScript et utilisez :

```js
window.logger.printSummary()
const allLogs = window.logger.getLogs()
const errors = window.logger.getLogsByLevel('ERROR')
const settingsLogs = window.logger.getLogsByComponent('Settings')
```

### Exporter et filtrer

- `window.logger.exportLogs()` : export JSON
- `window.logger.getLogsByComponent('Dashboard')` : logs par composant
- `window.logger.getLogsByLevel('DEBUG')` : logs par niveau

### Notes

- Le panneau de debug est disponible en bas à droite de l'application
- Le hook `useLogger` est optimisé avec `useCallback` et nomme automatiquement le composant
- Le logging couvre les clics, les soumissions, les appels API et les erreurs
