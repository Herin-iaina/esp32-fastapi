# 🧪 Guide de Test avec Données Fictives

## Vue d'ensemble

L'application est maintenant dotée d'un système complet de **données fictives (mock data)** pour tester sans base de données !

## 🚀 Démarrage Rapide

### Option 1 : Script Automatisé

```bash
chmod +x test-mock.sh
./test-mock.sh
```

### Option 2 : Démarrage Manuel

**Terminal 1 - Démarrer les services :**
```bash
./start-dev.sh
```

**Terminal 2 - Tester l'API (optionnel) :**
```bash
# Santé du backend
curl http://localhost:8000/api/health | jq

# Données fictives (mode test)
curl "http://localhost:8000/api/sensor/values?mock=true" | jq

# Historique 24h
curl "http://localhost:8000/api/sensor/history?hours=24&mock=true" | jq
```

### Option 3 : Test Instantané

```bash
# Terminal 1
python run.py

# Terminal 2
cd frontend && npm run dev

# Terminal 3
# Visitez http://localhost:5173
```

## 📊 Fonctionnalités de Test

### Données Fictives Disponibles

#### 1. **Valeurs Actuelles** (`GET /api/sensor/values?mock=true`)
```json
{
  "message": "Données fictives (mode test)",
  "data": {
    "average_temperature": 23.5,
    "average_humidity": 55.2,
    "fan_status": false,
    "humidifier_status": true,
    "numFailedSensors": 0,
    "sensors": {
      "sensor_01": {"temperature": 23.1, "humidity": 54.5},
      "sensor_02": {"temperature": 23.9, "humidity": 55.9},
      "sensor_03": {"temperature": 23.4, "humidity": 55.2}
    },
    "is_mock": true
  }
}
```

#### 2. **Historique** (`GET /api/sensor/history?hours=24&mock=true`)
```json
{
  "message": "Historique fictif (24 heures)",
  "data": {
    "history": [
      {
        "timestamp": "2026-01-27T12:24:00",
        "temperature": 20.5,
        "humidity": 45.2,
        "sensor": "sensor_01"
      },
      ...
    ],
    "total_points": 24,
    "hours": 24,
    "is_mock": true
  }
}
```

## 🎨 Frontend avec Données Fictives

Le frontend affiche automatiquement un badge **"🧪 Mode Test"** quand les données fictives sont utilisées.

### Comportement

1. **Au chargement** : Le dashboard récupère les données fictives
2. **Auto-refresh** : Les données se mettent à jour toutes les 10s
3. **Graphiques** : Les graphiques Recharts s'affichent normalement
4. **Indicateur** : Un badge bleu indique que c'est des données de test

## 🔄 Caractéristiques des Données Fictives

### Réalisme
- ✅ Variation réaliste des capteurs (-2 à +2°C par rapport à la moyenne)
- ✅ Humidité dans les plages normales (40-65%)
- ✅ Nombre de capteurs variable (2-5)
- ✅ État des équipements cohérent (fan si > 25°C, humidificateur si < 50%)

### Génération
```python
# Dans core/mock_data.py
generate_mock_sensor_data()       # Données actuelles
generate_mock_sensor_history()    # Historique 24h
get_mock_dashboard_stats()        # Stats du tableau de bord
get_mock_system_info()            # Info système
```

## 📝 Tests à Effectuer

### 1️⃣ Test Backend

```bash
# Vérifier que le backend démarre
curl http://localhost:8000/api/health

# Vérifier les données fictives
curl "http://localhost:8000/api/sensor/values?mock=true"

# Vérifier l'historique
curl "http://localhost:8000/api/sensor/history?hours=24&mock=true"
```

### 2️⃣ Test Frontend

- [ ] Ouvrir http://localhost:5173
- [ ] Vérifier que le dashboard charge
- [ ] Vérifier que les données s'affichent
- [ ] Vérifier que le badge "🧪 Mode Test" est visible
- [ ] Attendre 10s pour vérifier l'auto-refresh
- [ ] Cliquer sur "Paramètres" pour vérifier la navigation
- [ ] Vérifier les graphiques (BarChart, RadarChart)

### 3️⃣ Test Complet

```bash
./test-mock.sh
```

Cela va :
1. Démarrer Docker Compose
2. Tester la santé du backend
3. Récupérer les données fictives
4. Afficher l'historique
5. Fournir les URLs d'accès

## 🔧 Personnaliser les Données Fictives

### Modifier la plage de température

**File : `core/mock_data.py`**

```python
def generate_mock_sensor_data() -> ValuesRequest:
    base_temp = random.uniform(18, 28)  # ← Modifier ici
    base_humidity = random.uniform(40, 65)
    ...
```

### Ajouter plus de capteurs

```python
num_sensors = random.randint(2, 5)  # ← Modifier pour random.randint(2, 10)
```

### Modifier la variation de capteurs

```python
temp = base_temp + random.uniform(-2, 2)  # ← Modifier la plage (-5, 5)
```

## 📊 Données Générées

### Exemple de réponse complète

```bash
curl "http://localhost:8000/api/sensor/values?mock=true" | jq '.'
```

Réponse :
```json
{
  "message": "Données fictives (mode test)",
  "data": {
    "average_temperature": 24.3,
    "average_humidity": 52.1,
    "fan_status": true,
    "humidifier_status": false,
    "numFailedSensors": 0,
    "sensors": {
      "sensor_01": {
        "temperature": 24.1,
        "humidity": 51.5
      },
      "sensor_02": {
        "temperature": 24.5,
        "humidity": 52.7
      },
      "sensor_03": {
        "temperature": 24.2,
        "humidity": 52.0
      }
    },
    "timestamp": "2026-01-28T12:24:35.123456",
    "is_mock": true
  },
  "success": true
}
```

## 🚨 Dépannage

### Les données ne changent pas
- C'est normal ! Les données fictives changent aléatoirement
- Attendez que le frontend se rafraîchisse (10s)

### Le badge "🧪 Mode Test" ne s'affiche pas
- Vérifier que `isMockData` est à true dans le store
- Vérifier que l'API retourne `"is_mock": true`

### CORS Error
- Vérifier que le backend s'exécute sur port 8000
- Vérifier les paramètres CORS dans `run.py`

## 🎯 Prochaines Étapes

Après les tests avec données fictives :

1. ✅ Connecter une vraie base de données PostgreSQL
2. ✅ Implémenter l'authentification frontend
3. ✅ Créer des formulaires pour envoyer des données réelles
4. ✅ Ajouter des tests unitaires
5. ✅ Déployer en production

## 📚 Ressources

- Backend : [FastAPI Docs](http://localhost:8000/docs)
- Frontend : [React Docs](https://react.dev/)
- Mock Data : `core/mock_data.py`
- Store : `frontend/src/store/sensorStore.ts`
