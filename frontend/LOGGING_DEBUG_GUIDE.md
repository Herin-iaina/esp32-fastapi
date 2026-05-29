# Guide de Débogage avec Logging 🔍

Un système de logging complet a été intégré pour tracer les clics des boutons et les interactions de l'application.

## 🚀 Accéder aux Logs

Ouvrez la **Console JavaScript** avec:
- **Chrome/Firefox**: `F12` → Onglet **Console**
- **Firefox**: `Ctrl+Shift+K` (ou `Cmd+Option+K` sur Mac)
- **Chrome**: `Ctrl+Shift+J` (ou `Cmd+Option+J` sur Mac)

## 📊 Utilisation du Logger

### 1. **Voir tous les logs formatés**
```javascript
window.logger.printSummary()
```
Affiche un tableau des tous les logs en console.

### 2. **Obtenir tous les logs**
```javascript
const allLogs = window.logger.getLogs()
console.log(allLogs)
```

### 3. **Filtrer les logs par composant**
```javascript
// Voir tous les logs du composant Settings
const settingsLogs = window.logger.getLogsByComponent('Settings')
console.log(settingsLogs)

// Voir tous les logs du composant Dashboard
const dashboardLogs = window.logger.getLogsByComponent('Dashboard')
console.log(dashboardLogs)
```

### 4. **Filtrer les logs par niveau**
```javascript
// Voir seulement les erreurs
const errors = window.logger.getLogsByLevel('ERROR')

// Voir seulement les avertissements
const warnings = window.logger.getLogsByLevel('WARN')

// Voir seulement les infos
const infos = window.logger.getLogsByLevel('INFO')

// Voir seulement les débogages
const debugs = window.logger.getLogsByLevel('DEBUG')
```

### 5. **Exporter les logs en JSON**
```javascript
const logsJSON = window.logger.exportLogs()
console.log(logsJSON)

// Ou copier dans le presse-papiers
copy(logsJSON)
```

### 6. **Effacer les logs**
```javascript
window.logger.clearLogs()
```

## 🔍 Boutons Loggés

### Page **Settings** 📋
Les logs suivants sont disponibles:

- **Bouton "Se connecter"**
  - Enregistre les tentatives de connexion
  - Trace le nom d'utilisateur
  - Enregistre les erreurs d'authentification
  
- **Bouton "Déconnexion"**
  - Enregistre la déconnexion de l'utilisateur
  
- **Bouton "Mode sombre/clair"**
  - Enregistre les changements de thème
  
- **Bouton "Sauvegarder les paramètres"**
  - Enregistre les tentatives de sauvegarde
  - Inclut les paramètres modifiés
  - Enregistre les résultats (succès/erreur)

### Page **Dashboard** 📊
- Enregistre le montage et le démontage du composant
- Trace les chargements de données
- Enregistre l'utilisation des données fictives
- Enregistre les avertissements (capteurs défaillants, etc.)

## 🎯 Exemple d'Utilisation pour Déboguer

### Scénario: Bouton de connexion ne fonctionne pas

1. **Ouvrez la console** (F12)
2. **Cliquez sur le bouton "Se connecter"**
3. **Vérifiez les logs:**
```javascript
// Filtrer pour voir seulement les logs de Settings
window.logger.getLogsByComponent('Settings')

// Afficher le résumé
window.logger.printSummary()
```

4. **Observez les informations:**
   - L'heure exacte du clic
   - Le nom d'utilisateur utilisé
   - Les erreurs d'authentification
   - Les appels API

### Scénario: Vérifier la séquence d'actions

```javascript
// Afficher les 10 derniers logs
const logs = window.logger.getLogs()
console.table(logs.slice(-10))
```

## 📋 Format des Logs

Chaque log contient:
- **timestamp**: L'heure précise (HH:MM:SS.mmm)
- **level**: INFO, DEBUG, WARN, ou ERROR
- **component**: Le composant React (Settings, Dashboard, API)
- **action**: La description de l'action
- **details**: Les données additionnelles (optionnel)

### Exemple de log:
```
[14:32:45.123] [INFO] Settings - Bouton cliqué: Se connecter
  {username: "admin"}
```

## 🛠️ Intégration dans les Composants

Pour ajouter du logging dans d'autres composants:

```typescript
import { logger } from '../utils/logger'

// Dans une fonction
logger.logButtonClick('Nom du bouton', 'NomComposant', { données })
logger.logInfo('NomComposant', 'Message', { données })
logger.logError('NomComposant', 'Message erreur', error)
logger.logAPICall('GET', '/api/endpoint', 'status')
```

## 💾 Sauvegarder les Logs pour Rapport

Pour générer un rapport:

```javascript
// Créer un fichier texte avec les logs
const logs = window.logger.exportLogs()
const blob = new Blob([logs], {type: 'application/json'})
const url = URL.createObjectURL(blob)
const a = document.createElement('a')
a.href = url
a.download = `logs_${new Date().toISOString()}.json`
a.click()
```

## 🎨 Couleurs dans la Console

- **INFO** (Bleu) - Informations normales
- **DEBUG** (Gris) - Détails de débogage
- **WARN** (Orange) - Avertissements
- **ERROR** (Rouge) - Erreurs

## 📌 Tips Utiles

- Les logs sont stockés localement (max 500 entrées)
- Les anciens logs sont automatiquement supprimés
- Utilisez `copy(logs)` en console pour copier les logs
- Utilisez `console.table()` pour un meilleur affichage
- Nettoyez régulièrement avec `window.logger.clearLogs()`

---

**Besoin d'ajouter des logs?** Importez `logger` dans votre composant et utilisez ses méthodes! 🚀
