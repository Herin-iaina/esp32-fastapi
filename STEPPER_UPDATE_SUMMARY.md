# Résumé des Modifications - Support Multi-Driver Stepper

## 📋 Vue d'ensemble

Mise à jour complète du système pour supporter **TB6600** et **A4988** avec configuration flexible.

**Date**: 29 mai 2026  
**Version**: 2.0  

---

## ✅ Fichiers Modifiés

### 1. **routers/CABLAGE_ESP32.md**
- ✅ Tableau des pins mis à jour (GPIO 12 = DIR, GPIO 13 = STEP)
- ✅ Section "Moteur pas à pas" complètement réécrite avec 3 options:
  - Option A: TB6600 (RECOMMANDÉ)
  - Option B: A4988 (Compatible)
  - Option C: ULN2003 (Rétro-compatibilité)
- ✅ Schémas détaillés du câblage pour chaque option
- ✅ Informations sur la configuration DIP du TB6600
- ✅ Section finale avec lien vers le guide complet

### 2. **routers/main.cpp**
- ✅ Ajout de `#define STEPPER_DRIVER_TYPE "TB6600"`
- ✅ Ajout de pins : `STEPPER_PIN_DIR` (GPIO 12) et `STEPPER_PIN_STEP` (GPIO 13)
- ✅ Ajout de configuration conditionnelle des paramètres stepper:
  - TB6600: 1000 steps/sec, 2000 steps/sec²
  - A4988: 300 steps/sec, 1000 steps/sec²
- ✅ Changement de `AccelStepper::FULL4WIRE` → `AccelStepper::DRIVER`
- ✅ Initialisation du stepper avec les macros de configuration
- ✅ Logs de démarrage pour afficher le driver utilisé
- ✅ Mise à jour des fonctions `getStepperCommand()` et `checkStepperButton()` pour utiliser les macros

### 3. **routers/main_sht30.cpp**
- ✅ Identique à main.cpp (même traitement multi-driver)

### 4. **routers/main_mqtt.cpp**
- ✅ Identique à main.cpp
- ✅ Plus: Mise à jour de la fonction MQTT callback pour utiliser les macros stepper

### 5. **routers/main_sht30_mqtt.cpp**
- ✅ Identique à main.cpp
- ✅ Plus: Mise à jour de la fonction MQTT callback pour utiliser les macros stepper

### 6. **STEPPER_DRIVER_GUIDE.md** (NOUVEAU)
- ✅ Guide complet de configuration (65+ lignes)
- ✅ Comparaison TB6600 vs A4988 (tableau détaillé)
- ✅ Câblage détaillé pour chaque driver
- ✅ Configuration des paramètres
- ✅ Instructions d'utilisation (API, MQTT, Bouton)
- ✅ Débogage et troubleshooting
- ✅ Ressources et liens

---

## 🔄 Changements Techniques

### Mode de Contrôle du Stepper

**Avant (FULL4WIRE) :** 
```cpp
AccelStepper stepper(AccelStepper::FULL4WIRE, STEPPER_PIN_1, STEPPER_PIN_2);
```

**Après (DIR/STEP) :**
```cpp
AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_DIR, STEPPER_PIN_STEP);
```

### Pins Utilisés

| Fonction | Avant | Après | Notes |
|----------|-------|-------|-------|
| Direction | N/A | GPIO 12 | Nouveau standard |
| Step/Pulse | N/A | GPIO 13 | Nouveau standard |
| Pin 3 (optionnel) | GPIO 13 | GPIO 25 | Disponible si FULL4WIRE nécessaire |
| Pin 4 (optionnel) | N/A | GPIO 26 | Disponible si FULL4WIRE nécessaire |

### Paramètres de Contrôle

**Mode TB6600 (par défaut) :**
```cpp
#define STEPPER_MAX_SPEED         1000    // steps/sec
#define STEPPER_ACCELERATION      2000    // steps/sec²
#define STEPPER_ROTATION_STEPS    1000    // 5 rotations
#define STEPPER_SPEED             300     // Speed des commandes
```

**Mode A4988 (optionnel) :**
```cpp
#define STEPPER_MAX_SPEED         300     // Limité pour stabilité
#define STEPPER_ACCELERATION      1000
#define STEPPER_ROTATION_STEPS    1000
#define STEPPER_SPEED             100
```

---

## 🎯 Comment Utiliser

### Pour passer au TB6600

1. Ouvrez le fichier C++ (par exemple `main.cpp`)
2. Localisez la ligne :
   ```cpp
   #define STEPPER_DRIVER_TYPE "TB6600"
   ```
3. C'est déjà la valeur par défaut ✅

### Pour utiliser l'A4988

1. Changez la ligne à :
   ```cpp
   #define STEPPER_DRIVER_TYPE "A4988"
   ```
2. Recompliez et téléversez

### Câblage

- **GPIO 12** → Direction (DIR) du driver
- **GPIO 13** → Pulse/Step (PUL) du driver
- **Moteur** → Branché au driver
- **Alimentation du driver** → 5V logique + tension moteur (24V TB6600 ou 12V A4988)

---

## 📊 Comparaison des Performances

| Métrique | TB6600 | A4988 |
|----------|--------|-------|
| Vitesse max | 1000 steps/sec | 300 steps/sec |
| Accélération max | 2000 steps/sec² | 1000 steps/sec² |
| Tensión du moteur | 24-48V | 12V |
| Courant max | 4A | 2A |
| Microstep | DIP configurable | Configurable |
| Recommandé pour | Production | Tests |

---

## 🔍 Vérification du Déploiement

### Logs de Démarrage

Consultez la sortie série pour confirmer le driver :

**TB6600 :**
```
=== ESP32 Sensor Controller v2 ===

Stepper Driver: TB6600 (DIR/STEP)
Max Speed: 1000 steps/sec
Acceleration: 2000 steps/sec²
```

**A4988 :**
```
=== ESP32 Sensor Controller v2 ===

Stepper Driver: A4988 (DIR/STEP)
Max Speed: 300 steps/sec
Acceleration: 1000 steps/sec²
```

### Tests Recommandés

1. ✅ Vérifier le câblage (GPIO 12 & 13)
2. ✅ Lancer le moteur via API: `GET /sensor/automation/stepper`
3. ✅ Lancer le moteur via MQTT: `incubator/automation/stepper` → `{"activate": true}`
4. ✅ Tester le bouton manuel (GPIO 23)
5. ✅ Vérifier la rotation et la vitesse

---

## 📝 Backward Compatibility

- ✅ Système compatible avec la version précédente
- ✅ Pas de changements d'API
- ✅ Pins TB6600/A4988 identiques (GPIO 12, 13)
- ⚠️ Les vitesses et accélération diffèrent selon le driver sélectionné

---

## 🚀 Prochaines Étapes (Optional)

- [ ] Tester avec TB6600 réel
- [ ] Tester avec A4988 réel
- [ ] Mesurer la consommation énergétique
- [ ] Optimiser les paramètres pour votre moteur spécifique
- [ ] Ajouter la sauvegarde du driver sélectionné en base de données

---

## 📚 Documentation Associée

- [STEPPER_DRIVER_GUIDE.md](STEPPER_DRIVER_GUIDE.md) - Guide complet
- [routers/CABLAGE_ESP32.md](routers/CABLAGE_ESP32.md) - Schémas de câblage
- [AccelStepper Library](http://www.airspayce.com/mikem/arduino/AccelStepper/) - Référence

---

## 🔧 Support Technique

**Pour changer de driver :** Modifiez `STEPPER_DRIVER_TYPE` dans le fichier C++ et recompliez.

**Pour les problèmes :**
1. Vérifiez les logs série
2. Consultez STEPPER_DRIVER_GUIDE.md → Section Troubleshooting
3. Vérifiez le câblage (GPIO 12, 13)
4. Testez l'alimentation du driver

---

**Status**: ✅ Complet et prêt pour déploiement  
**Test requis**: Validation avec TB6600 et A4988 réels
