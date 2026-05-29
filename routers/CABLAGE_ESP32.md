# Documentation Câblage ESP32 - Contrôleur Incubateur

## Vue d'ensemble

Ce document décrit le câblage complet du système de contrôle d'incubateur basé sur ESP32.

---

## Tableau récapitulatif des connexions

| Module | Pin ESP32 | Description |
|--------|-----------|-------------|
| DHT22 #1 | GPIO 0 | Capteur température/humidité 1 |
| DHT22 #2 | GPIO 2 | Capteur température/humidité 2 |
| DHT22 #3 | GPIO 4 | Capteur température/humidité 3 |
| DHT22 #4 | GPIO 5 | Capteur température/humidité 4 |
| Stepper DIR | GPIO 12 | Direction moteur pas à pas |
| Stepper STEP | GPIO 13 | Pulse/Step moteur pas à pas |
| Ventilateur | GPIO 14 | Contrôle ventilateur (refroidissement) |
| Humidificateur | GPIO 15 | Contrôle humidificateur |
| LED Verte | GPIO 16 | Temp & Humidité OK (±2%) |
| LED Orange | GPIO 17 | Temp ou Humidité < normal |
| LED Rouge | GPIO 18 | Temp ou Humidité > normal |
| LED Bleue | GPIO 19 | Connexion serveur NOK |
| Bouton Stepper | GPIO 23 | Lancement manuel moteur NEMA |
| LCD I2C SDA | GPIO 21 | Données I2C (défaut ESP32) |
| LCD I2C SCL | GPIO 22 | Horloge I2C (défaut ESP32) |

---

## Détail par module

### 1. Capteurs DHT22 (x4)

```
DHT22 #1          DHT22 #2          DHT22 #3          DHT22 #4
┌─────┐           ┌─────┐           ┌─────┐           ┌─────┐
│ VCC │──3.3V     │ VCC │──3.3V     │ VCC │──3.3V     │ VCC │──3.3V
│ DATA│──GPIO 0   │ DATA│──GPIO 2   │ DATA│──GPIO 4   │ DATA│──GPIO 5
│ NC  │           │ NC  │           │ NC  │           │ NC  │
│ GND │──GND      │ GND │──GND      │ GND │──GND      │ GND │──GND
└─────┘           └─────┘           └─────┘           └─────┘
    │                 │                 │                 │
   10kΩ              10kΩ              10kΩ              10kΩ
    │                 │                 │                 │
   3.3V              3.3V              3.3V              3.3V
```

**Note**: Résistance pull-up de 10kΩ entre DATA et VCC pour chaque capteur.

---

### 2. Écran LCD 16x2 I2C

```
LCD I2C Module
┌──────────────┐
│ GND  │───────│── GND
│ VCC  │───────│── 5V (ou 3.3V selon module)
│ SDA  │───────│── GPIO 21
│ SCL  │───────│── GPIO 22
└──────────────┘

Adresse I2C: 0x27 (par défaut, peut être 0x3F)
```

---

### 3. LEDs d'état (x4)

```
         LED Verte      LED Orange     LED Rouge      LED Bleue
            │               │              │              │
         ┌──┴──┐         ┌──┴──┐        ┌──┴──┐        ┌──┴──┐
         │ LED │         │ LED │        │ LED │        │ LED │
         └──┬──┘         └──┬──┘        └──┬──┘        └──┬──┘
            │               │              │              │
           220Ω            220Ω           220Ω           220Ω
            │               │              │              │
         GPIO 16         GPIO 17        GPIO 18        GPIO 19


Toutes les cathodes (–) des LEDs → GND
```

**Signification des LEDs:**
| LED | État | Signification |
|-----|------|---------------|
| Verte | ON | Température ET humidité dans la plage normale (±2%) |
| Orange | ON | Température OU humidité en dessous de la normale |
| Rouge | ON | Température OU humidité au-dessus de la normale |
| Bleue | ON | Connexion serveur NON établie (mode autonome ou échec)

---

### 5. Bouton Stepper (Lancement manuel NEMA)

```
Bouton poussoir
┌─────────┐
│    O────│── GPIO 23 (INPUT_PULLUP)
│    O────│── GND
└─────────┘
```

**Note**: Le bouton utilise la résistance pull-up interne de l'ESP32.
Appuyer sur le bouton connecte GPIO 23 à GND, ce qui déclenche la rotation du moteur.

---

### 4. Moteur pas à pas (Stepper)

#### Option A: Driver TB6600 (RECOMMANDÉ)

```
TB6600 Stepper Driver
┌─────────────────┐
│ +5V  │──────────│── 5V
│ GND  │──────────│── GND
│ DIR  │──────────│── GPIO 12 (Direction)
│ PUL  │──────────│── GPIO 13 (Pulse/Step)
│ ENA  │──────────│── 5V (Enable, toujours activé)
└─────────────────┘
       │
       └── NEMA 17/23 Stepper Motor (24V recommandé)
```

**Avantages TB6600:**
- Contrôle DIR/STEP simple et standardisé
- Support des moteurs 24V/48V
- Microstepping intégré (configurable sur le driver)
- Meilleure performance et couple
- Consommation énergétique optimisée

**Configuration DIP du TB6600:**
- Microstep: Régler selon vos besoins (1/1, 1/2, 1/4, 1/8, 1/16)
- Current: Adapter au moteur utilisé (1A, 2A, 3A, 4A)

---

#### Option B: Driver A4988 (Compatible)

```
A4988 Stepper Driver
┌─────────────────────┐
│ DIR  │──────────────│── GPIO 12 (Direction)
│ STEP │──────────────│── GPIO 13 (Step)
│ MS1, MS2, MS3 │────│── Config Microstep (optionnel)
│ ENABLE │────────────│── GND (toujours activé)
│ GND  │──────────────│── GND
│ +5V  │──────────────│── 5V
└─────────────────────┘
       │
       └── NEMA 17 Stepper Motor (12V)
```

**Mode de fonctionnement:**
- Si MS1/MS2/MS3 non connectés: Full-step
- Connecter des pins GPIO pour contrôler le microstep

**Avantages A4988:**
- Support des moteurs 12V
- Flexible avec configuration microstep par GPIO
- Moins de puissance

---

#### Option C: Driver ULN2003 (Retro-compatibilité)

```
ULN2003 Driver Module
┌─────────────────┐
│ IN1  │──────────│── GPIO 12
│ IN2  │──────────│── GPIO 13
│ IN3  │──────────│── GPIO 25 (optionnel)
│ IN4  │──────────│── GPIO 26 (optionnel)
│ VCC  │──────────│── 5V
│ GND  │──────────│── GND
└─────────────────┘
```

**Note**: ULN2003 est limité à 500mA par canal, moins recommandé.

---

### 6. Relais Ventilateur & Humidificateur

```
Module Relais (2 canaux)
┌────────────────────────┐
│ VCC   │────────────────│── 5V
│ GND   │────────────────│── GND
│ IN1   │────────────────│── GPIO 14 (Ventilateur)
│ IN2   │────────────────│── GPIO 15 (Humidificateur)
└────────────────────────┘
        │
        ├── COM ────── 220V/12V (selon appareil)
        ├── NO  ────── Ventilateur/Humidificateur
        └── NC  ────── (non utilisé)
```

**ATTENTION**: Manipuler le 220V avec précaution!

---

## Schéma de câblage complet

```
                                    ┌─────────────────┐
                                    │     ESP32       │
                                    │                 │
    DHT22 #1 ──────────────────────│ GPIO 0          │
    DHT22 #2 ──────────────────────│ GPIO 2          │
    DHT22 #3 ──────────────────────│ GPIO 4          │
    DHT22 #4 ──────────────────────│ GPIO 5          │
                                    │                 │
    Stepper IN1 ───────────────────│ GPIO 12         │
    Stepper IN2 ───────────────────│ GPIO 13         │
                                    │                 │
    Relais Ventilateur ────────────│ GPIO 14         │
    Relais Humidificateur ─────────│ GPIO 15         │
                                    │                 │
    LED Verte (+ 220Ω) ────────────│ GPIO 16         │
    LED Orange (+ 220Ω) ───────────│ GPIO 17         │
    LED Rouge (+ 220Ω) ────────────│ GPIO 18         │
    LED Bleue (+ 220Ω) ────────────│ GPIO 19         │
                                    │                 │
    Bouton Stepper ────────────────│ GPIO 23         │
                                    │                 │
    LCD SDA ───────────────────────│ GPIO 21         │
    LCD SCL ───────────────────────│ GPIO 22         │
                                    │                 │
    Alimentation ──────────────────│ 3.3V / 5V / GND │
                                    └─────────────────┘
```

---

## Alimentation

| Composant | Tension | Courant estimé |
|-----------|---------|----------------|
| ESP32 | 3.3V (via USB 5V) | 240mA max |
| DHT22 (x4) | 3.3V | 2.5mA chacun |
| LCD I2C | 5V | 20mA |
| LEDs (x4) | 3.3V | 20mA chacune |
| Module Relais | 5V | 70mA par canal |
| Moteur Stepper | 5-12V | 200-500mA |

**Recommandation**: Utiliser une alimentation 5V/2A minimum.

---

## Configuration logicielle

```cpp
// Valeurs cibles
const float TEMP_TARGET = 37.7;           // °C - Température cible
const float HUMIDITY_TARGET = 45.0;       // % - Humidité cible
const float TOLERANCE_PERCENT = 2.0;      // Tolérance ±2%

// Seuils calculés automatiquement
// TEMP_MIN = 36.95°C, TEMP_MAX = 38.45°C
// HUMIDITY_MIN = 44.1%, HUMIDITY_MAX = 45.9%

// Logique de contrôle (mode autonome)
// - Ventilateur ON si température < TEMP_MIN (distribue la chaleur)
// - Humidificateur ON si humidité < HUMIDITY_MIN

// Tentatives avant mode autonome
const int MAX_SERVER_RETRIES = 10;

// Intervalle d'envoi des données
const unsigned long SEND_INTERVAL = 5000;  // 5 secondes

// Configuration serveur
const char* serverIP = "192.168.1.100";
const int serverPort = 5000;
```

### Logique des LEDs

| Condition | LED |
|-----------|-----|
| Temp ET Humidité dans ±2% de la cible | Verte |
| Temp OU Humidité < minimum | Orange |
| Temp OU Humidité > maximum | Rouge |
| Serveur non connecté | Bleue |

---

## Liste de matériel

- [ ] 1x ESP32 DevKit
- [ ] 4x Capteurs DHT22
- [ ] 4x Résistances 10kΩ (pull-up DHT22)
- [ ] 1x Écran LCD 16x2 avec module I2C
- [ ] 4x LEDs (verte, orange, rouge, bleue)
- [ ] 4x Résistances 220Ω (LEDs)
- [ ] 1x Bouton poussoir (pour stepper manuel)
- [ ] 1x Module relais 2 canaux
- [ ] 1x Moteur NEMA pas à pas + driver (A4988/DRV8825)
- [ ] 1x Ventilateur 12V
- [ ] 1x Humidificateur ultrasonique
- [ ] Fils de connexion (jumper wires)
- [ ] Breadboard ou PCB
- [ ] Alimentation 5V/2A

---

## Dépannage

| Problème | Solution |
|----------|----------|
| LCD n'affiche rien | Vérifier adresse I2C (0x27 ou 0x3F), ajuster contraste |
| DHT22 retourne NaN | Vérifier câblage et résistance pull-up |
| LEDs ne s'allument pas | Vérifier polarité et résistances |
| Pas de connexion WiFi | Vérifier SSID/mot de passe |
| Mode autonome activé | Vérifier connexion serveur (IP, port) |

---

## Configuration du Driver Stepper (TB6600 vs A4988)

### 🔧 Comment changer de driver ?

Voir le guide complet : [STEPPER_DRIVER_GUIDE.md](../STEPPER_DRIVER_GUIDE.md)

**Résumé rapide :**

1. Ouvrez le fichier C++ de votre choix (par exemple `main.cpp`)
2. Modifiez la première ligne de configuration :
   ```cpp
   #define STEPPER_DRIVER_TYPE "TB6600"  // Ou "A4988"
   ```
3. Recompliez et téléversez sur l'ESP32

### ⚡ Recommandations

**Utilisez TB6600 si :**
- ✅ Vous avez un moteur NEMA 17/23
- ✅ Vous avez une alimentation 24V disponible
- ✅ Vous avez besoin de performances optimales

**Utilisez A4988 si :**
- ✅ Vous avez un moteur NEMA 17 (12V)
- ✅ Vous avez une alimentation 12V
- ✅ Vous prototypez ou testez

### 📋 Vérification du Driver dans les Logs

À l'initialisation, consultez la sortie série :

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
