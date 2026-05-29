# Guide de Configuration des Drivers Stepper (TB6600 vs A4988)

## Vue d'ensemble

Le système supporte maintenant deux drivers stepper avec configuration flexible :
- **TB6600** : Driver DIR/STEP haute performance (recommandé) 
- **A4988** : Driver DIR/STEP standard

## 1. Sélection du Driver

### Pour changer le driver utilisé :

Ouvrez le fichier `.cpp` correspondant et modifiez la première ligne de configuration :

```cpp
// ============== SÉLECTION DU DRIVER STEPPER ==============
// Options: "TB6600" ou "A4988"
#define STEPPER_DRIVER_TYPE "TB6600"  // ← Changer ici : "TB6600" ou "A4988"
```

### Fichiers C++ à modifier (tous identiques) :
- `main.cpp`
- `main_sht30.cpp`
- `main_mqtt.cpp`
- `main_sht30_mqtt.cpp`

---

## 2. Caractéristiques Comparées

| Aspect | TB6600 | A4988 |
|--------|--------|-------|
| **Mode** | DIR/STEP | DIR/STEP |
| **Tension** | 24-48V | 12V |
| **Courant Max** | 4A | 2A |
| **Microstep** | Configurable sur driver | Configurable sur driver |
| **Vitesse Max** | 1000 steps/sec | 300 steps/sec |
| **Accélération** | 2000 steps/sec² | 1000 steps/sec² |
| **Performance** | Excellente | Bonne |
| **Coût** | Moyen | Économique |

---

## 3. Câblage

### Schéma Common (TB6600 et A4988)

```
ESP32                     Driver Stepper
┌────────────────┐        ┌─────────────────┐
│ GPIO 12 (DIR)  ├────────│ DIR  (Direction) │
│ GPIO 13 (STEP) ├────────│ PUL  (Pulse)     │
│ GND            ├────────│ GND              │
└────────────────┘        └─────────────────┘
                                  │
                          NEMA 17/23 Motor
                          (24V ou 12V selon driver)
```

### Configuration TB6600

```
TB6600 Driver (Vue des connexions)
┌────────────────────────────────┐
│ Alimentation Logique:          │
│  +5V    → 5V                   │
│  GND    → GND                  │
│                                │
│ Signaux de Contrôle:           │
│  DIR+   → GPIO 12              │
│  DIR-   → GND                  │
│  PUL+   → GPIO 13              │
│  PUL-   → GND                  │
│  ENA+   → 5V (Enable)          │
│  ENA-   → GND                  │
│                                │
│ Alimentation Moteur:           │
│  +24V   → 24-48V               │
│  GND    → GND (masse moteur)   │
└────────────────────────────────┘
```

**Explication des symboles ± :**
- **+** = Signal actif (connecter au GPIO pour direction/pulse, ou à 5V pour enable)
- **-** = Masse/Retour (connecter à GND)

**Tableau des connexions TB6600 :**

| TB6600 Pin | Signal | Connexion ESP32 | Alternative |
|-----------|--------|-----------------|-------------|
| DIR+ | Direction+ | GPIO 12 | Pulsé (reçoit le signal) |
| DIR- | Direction- | **GND** | Ou laisser flottant |
| PUL+ | Pulse+ | GPIO 13 | Pulsé (reçoit les steps) |
| PUL- | Pulse- | **GND** | Ou laisser flottant |
| ENA+ | Enable+ | **5V** | Toujours actif |
| ENA- | Enable- | **GND** | Ou laisser flottant |

**Configuration DIP du TB6600 :**
- **Microstep Selection** (MS1, MS2, MS3) :
  - 1/1 (Full-step)
  - 1/2 
  - 1/4
  - 1/8 
  - 1/16 
- **Current Setting** : Adapter au moteur (1A, 2A, 3A, 4A)

### Configuration A4988

```
A4988 Driver
┌──────────────────────┐
│ DIR  ├──────────────→ GPIO 12
│ STEP ├──────────────→ GPIO 13
│ ENABLE ├────────────→ GND (toujours actif)
│ GND  ├──────────────→ GND
│ +5V  ├──────────────→ 5V
│ +12V ├──────────────→ 12V (Motor power)
│ GND  ├──────────────→ GND (Motor)
└──────────────────────┘
```

**Configuration Microstep (optionnel) :**
```
MS1 → GPIO 25 (optionnel)
MS2 → GPIO 26 (optionnel)
MS3 → GND (optionnel)
```

---

## 4. Configuration des Paramètres

Les paramètres suivants sont automatiquement ajustés selon le driver sélectionné :

```cpp
// ============== CONFIGURATION STEPPER PAR DRIVER ==============

// TB6600
#define STEPPER_MAX_SPEED         1000    // steps/sec
#define STEPPER_ACCELERATION      2000    // steps/sec²
#define STEPPER_STEPS_PER_ROTATION 200    // 200 steps = 1 rotation
#define STEPPER_ROTATION_STEPS    1000    // 5 rotations (5 * 200)
#define STEPPER_SPEED             300     // Speed pour les commandes

// A4988 (limite inférieure pour stabilité)
#define STEPPER_MAX_SPEED         300     // steps/sec
#define STEPPER_ACCELERATION      1000    // steps/sec²
#define STEPPER_STEPS_PER_ROTATION 200
#define STEPPER_ROTATION_STEPS    1000
#define STEPPER_SPEED             100
```

### Personnalisation des Paramètres

Pour modifier les performances, éditez directement les macros :

```cpp
#if defined(STEPPER_DRIVER_TYPE) && strcmp(STEPPER_DRIVER_TYPE, "TB6600") == 0
  #define STEPPER_MAX_SPEED         1000    // ← Ajuster ici (800-1200)
  #define STEPPER_ACCELERATION      2000    // ← Ajuster ici (1000-3000)
  #define STEPPER_ROTATION_STEPS    1000    // ← Nombre de steps par rotation
  #define STEPPER_SPEED             300     // ← Vitesse des commandes
```

---

## 5. Utilisation et Contrôle

### Via API REST (HTTP)

```bash
# Déclencher une rotation manuelle
curl -X GET http://192.168.1.100:5000/sensor/automation/stepper

# Réponse
{"stepper": true}  # Déclenche la rotation
```

### Via MQTT

```
Topic: incubator/automation/stepper
Payload: {"activate": true}
```

### Bouton Manuel

Appuyez sur le bouton connecté à **GPIO 23** pour déclencher une rotation.

---

## 6. Débogage et Messages Serial

Lors du démarrage, vérifiez les logs serial :

```
=== ESP32 Sensor Controller v2 ===

Stepper Driver: TB6600 (DIR/STEP)
Max Speed: 1000 steps/sec
Acceleration: 2000 steps/sec²
```

Ou avec A4988 :

```
Stepper Driver: A4988 (DIR/STEP)
Max Speed: 300 steps/sec
Acceleration: 1000 steps/sec²
```

---

## 7. Troubleshooting

### Le moteur ne tourne pas

1. Vérifiez le câblage (GPIO 12 et 13)
2. Vérifiez l'alimentation du driver (5V logique + moteur)
3. Vérifiez que `STEPPER_DRIVER_TYPE` est bien configuré
4. Consultez les logs serial pour les erreurs

### Le moteur tourne trop rapidement / lentement

- **TB6600** : Ajustez le microstep sur le driver DIP
- **A4988** : Modifiez `STEPPER_MAX_SPEED` dans le code

### Vibrations/Bruit excessif

1. Réduisez `STEPPER_ACCELERATION`
2. Vérifiez le courant configuré sur le driver
3. Vérifiez la tension d'alimentation du moteur

### Le moteur perd de pas

1. Réduisez `STEPPER_MAX_SPEED`
2. Augmentez le courant du driver
3. Vérifiez que le moteur n'est pas surcharché

---

## 8. Spécifications Techniques

### AccelStepper Library

Le code utilise la bibliothèque `AccelStepper` en mode **DRIVER** :

```cpp
// Mode DIR/STEP (type 1)
AccelStepper stepper(AccelStepper::DRIVER, 
                     STEPPER_PIN_DIR,   // GPIO 12
                     STEPPER_PIN_STEP); // GPIO 13
```

### Séquences de Contrôle

**Pour une rotation (STEPPER_ROTATION_STEPS = 1000 steps) :**

1. Définir la direction : Set GPIO 12 HIGH/LOW
2. Générer les pulses : Toggle GPIO 13 à la vitesse configurée
3. Nombre de pulses : 1000 (5 rotations complètes si 200 steps/rotation)

---

## 9. Migration depuis l'Ancienne Configuration

### Avant (FULL4WIRE)
```cpp
AccelStepper stepper(AccelStepper::FULL4WIRE, STEPPER_PIN_1, STEPPER_PIN_2);
stepper.setMaxSpeed(300);
stepper.setAcceleration(1000);
```

### Après (DIR/STEP - Recommandé)
```cpp
AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_DIR, STEPPER_PIN_STEP);
stepper.setMaxSpeed(STEPPER_MAX_SPEED);  // Auto-configuré
stepper.setAcceleration(STEPPER_ACCELERATION);  // Auto-configuré
```

---

## 10. Recommandations

✅ **Recommandé :**
- **TB6600** pour les applications de production
  - Moteurs plus puissants
  - Meilleure performance
  - Plus stable

✅ **Pour le prototypage :**
- **A4988** pour tests et expérimentation
  - Plus économique
  - Facile à trouver
  - Limite la consommation

---

## 11. Ressources

- [AccelStepper Documentation](http://www.airspayce.com/mikem/arduino/AccelStepper/)
- [TB6600 Datasheet](https://datasheets.com/en/part/TB6600)
- [A4988 Datasheet](https://datasheets.com/en/part/A4988)
- [NEMA Stepper Motor Specs](https://en.wikipedia.org/wiki/Stepper_motor)

---

## Changelog

**v2.0** - Support multi-driver
- ✅ TB6600 (DIR/STEP) - Mode optimisé
- ✅ A4988 (DIR/STEP) - Mode compatible
- ✅ Configuration automatique des paramètres
- ✅ Tous les fichiers C++ alignés
- ✅ Logs serial pour debug
