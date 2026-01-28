# 🐔 Guide Utilisateur - Système d'Incubation

## Démarrage Rapide

### 1. Accéder à l'Application
Ouvrez votre navigateur et accédez à: **http://localhost:8000**

### 2. Authentification
Cliquez sur **"Paramètres"** dans la barre de navigation, puis:
- Entrez votre **nom d'utilisateur**: `admin`
- Entrez votre **mot de passe**: `test123456`
- Cliquez sur **"Se connecter"**

> ℹ️ Vous devez être connecté pour modifier les paramètres d'incubation.

## Paramètres d'Incubation

### 📋 Espèce
Sélectionnez le type d'oeuf que vous allez incuber:
- **Poule** (21 jours) - Température: 37.5°C
- **Canard** (28 jours) - Température: 37.5°C
- **Dinde** (28 jours) - Température: 37.5°C
- **Autre** - Température: 37.5°C

### ⏰ Jours jusqu'à l'éclosion
Le nombre de jours avant l'éclosion. Varie selon l'espèce:
- Poule: **21 jours**
- Canard: **28 jours**
- Dinde: **28 jours**

### 🔄 Rotations par jour
Nombre de rotations recommandées par jour:
- Valeur standard: **5 rotations**
- Plus élevé = meilleur développement

## 🌡️ Contrôle de Température

### Température cible
La température idéale pour l'incubation:
- **Standard**: 37.5°C (tous les oiseaux)
- Précision: ±0.2°C (très important!)

### Température actuelle
Affichage de la température mesurée en temps réel par les capteurs.
Cette valeur est **mise à jour automatiquement**.

> ⚠️ Si la température s'écarte de plus de 1°C, vérifiez votre incubateur!

## 💧 Contrôle d'Humidité

### Humidité cible (%)
L'humidité relative idéale varie selon le stade d'incubation:

**Jours 1-18 (développement)**:
- Humidité cible: **40-50%**

**Jours 19+ (préparation éclosion)**:
- Humidité cible: **70-75%**

### Humidité actuelle
Affichage de l'humidité mesurée en temps réel.
Cette valeur est **mise à jour automatiquement**.

## ⚙️ Configuration du Matériel

### Moteur de rotation automatique
- ✅ **Activé**: L'incubateur tourne automatiquement les oeufs
- ❌ **Désactivé**: Rotation manuelle requise

> 💡 Recommandé: Activé pour plus de fiabilité

### Nombre de tourneurs
Nombre de systèmes de rotation physiques:
- Typique: **2-4 tourneurs**
- Dépend de la taille de votre incubateur

## 📅 Date de Début du Cycle

Sélectionnez la date et l'heure de démarrage de l'incubation.
Le système calculera automatiquement la date d'éclosion prévue.

Exemple:
- Date de début: 28 janvier 2025 à 14:00
- Espèce: Poule (21 jours)
- Date d'éclosion prévue: **18 février 2025**

## 🎨 Mode Sombre

Cliquez sur l'icône **Sun/Moon** en haut à droite pour basculer entre:
- ☀️ **Mode clair**: Idéal en journée
- 🌙 **Mode sombre**: Idéal la nuit (moins de fatigue oculaire)

Votre préférence est **automatiquement sauvegardée**.

## 💾 Sauvegarder les Paramètres

Une fois tous les paramètres configurés:
1. Vérifiez que vous êtes **connecté**
2. Cliquez sur **"Sauvegarder"** en bas
3. Attendez le message de confirmation ✅

> ℹ️ Vos paramètres sont stockés dans la base de données et restaurés automatiquement à chaque visite.

## 📊 Tableau de Bord

Cliquez sur **"Tableau de Bord"** pour voir:
- 📈 **Graphique de température** (dernières 24h)
- 💧 **Graphique d'humidité** (dernières 24h)
- 🔌 **État du système**
- ⏱️ **Temps restant jusqu'à l'éclosion**

## 🔒 Déconnexion

Cliquez sur **"Se Déconnecter"** pour terminer votre session.

> ℹ️ Vos paramètres restent sauvegardés pour la prochaine session.

## ❌ Dépannage

### "Identifiants invalides"
- Vérifiez l'orthographe du nom d'utilisateur
- Assurez-vous que Caps Lock est désactivé
- Réessayez avec: `admin` / `test123456`

### Les paramètres ne se sauvegardent pas
- Assurez-vous d'être **connecté**
- Vérifiez que le bouton "Sauvegarder" est **actif** (pas grisé)
- Essayez de rafraîchir la page

### Température/Humidité n'affichent pas de valeurs
- Vérifiez que les capteurs sont correctement connectés
- Vérifiez que l'incubateur est sous tension
- Regardez l'onglet "Tableau de Bord" pour les détails

### L'application ne charge pas
- Vérifiez que vous accédez à: `http://localhost:8000` (pas HTTPS)
- Vérifiez que Docker Compose est en cours d'exécution
- Essayez de vider le cache du navigateur (Ctrl+Shift+Delete)

## 📚 Ressources Supplémentaires

### Incubation Générale
- Température: 37.5°C (±0.2°C)
- Humidité: Adaptée au stade (voir ci-dessus)
- Ventilation: Importante pour l'oxygène
- Rotation: 5+ fois par jour si possible

### Calcul d'Éclosion
Pour calculer manuellement:
- Poule: Date démarrage + 21 jours
- Canard: Date démarrage + 28 jours
- Dinde: Date démarrage + 28 jours

---

**Dernière mise à jour**: 28 Janvier 2025
**Version**: 2.0.0
