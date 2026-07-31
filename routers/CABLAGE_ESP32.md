# Documentation Câblage ESP32 - Contrôleur Incubateur

## Vue d'ensemble

Ce document décrit le câblage complet du système de contrôle d'incubateur basé sur ESP32.

---

## Guide d'assemblage sur breadboard

**Consignes importantes**

- Ne branchez pas l'alimentation secteur (220V ou 12V/24V) tant que le câblage 3.3V/5V n'est pas terminé.
- L'ESP32 fonctionne en logique 3.3V. N'appliquez jamais de signal 5V sur ses pins d'entrée (GPIO 33, 34, 35, 36).
- Les broches GPIO 34, 35 et 36 sont uniquement des entrées (`Input Only`). Elles ne possèdent pas de résistances internes de pull-up, les résistances externes de 10kΩ pour les DHT22 sont donc obligatoires.

### Étape 1. Alimentation des rails de la breadboard

- Ligne rouge (+) supérieure → Broche 5V (ou VIN) de l'ESP32.
- Ligne bleue (-) supérieure → Broche GND de l'ESP32.
- Ligne rouge (+) inférieure → Broche 3.3V de l'ESP32 (pour DHT22 et TB6600 PUL+/DIR+/ENA+).
- Ligne bleue (-) inférieure → Relier au rail GND supérieur pour partager une masse commune.

### Étape 2. Capteurs DHT22 (x4)

Chaque capteur DHT22 comporte 4 broches (vue de face, de gauche à droite : 1=VCC, 2=DATA, 3=NC, 4=GND).

- DHT22 #1 : VCC → 3.3V, DATA → GPIO 33, GND → GND.
- DHT22 #2 : VCC → 3.3V, DATA → GPIO 34, GND → GND.
- DHT22 #3 : VCC → 3.3V, DATA → GPIO 35, GND → GND.
- DHT22 #4 : VCC → 3.3V, DATA → GPIO 36, GND → GND.

Pour chaque DHT22 : placer une résistance de 10kΩ entre VCC et DATA.

### Étape 3. Écran LCD 16x2 I2C

- GND → rail GND
- VCC → rail 5V
- SDA → GPIO 21
- SCL → GPIO 22

Adresse I2C : 0x27 (par défaut, peut être 0x3F).

### Étape 4. Driver TB6600

Le TB6600 est câblé en logique anode commune (cathodes contrôlées par l'ESP32) :

- PUL+ → 3.3V
- DIR+ → 3.3V
- ENA+ → 3.3V
- PUL- → GPIO 13
- DIR- → GPIO 12
- ENA- → GPIO 32
- VCC / GND du TB6600 → alimentation externe 12V ou 24V
- A+, A-, B+, B- → Moteur pas à pas NEMA

> Important : utiliser une masse commune entre l'ESP32 et l'alimentation du TB6600 si les signaux sont référencés au même circuit.

### Étape 5. Module relais 2 canaux

- VCC du relais → rail 5V
- GND du relais → rail GND
- IN1 (ventilateur) → GPIO 14
- IN2 (humidificateur) → GPIO 15

### Étape 6. LEDs de statut (x4)

Pour chaque LED : anode (+) → GPIO, cathode (-) → résistance 220Ω → rail GND.

- LED Verte : GPIO 16
- LED Orange : GPIO 17
- LED Rouge : GPIO 18
- LED Bleue : GPIO 19

### Étape 7. Boutons poussoirs (x2)

Les boutons utilisent la résistance `INPUT_PULLUP` interne de l'ESP32.

- Bouton Stepper : GPIO 23 → bouton → GND
- Bouton LCD (scroll logs) : GPIO 27 → bouton → GND

---

## Tableau récapitulatif des connexions

| Module | Pin ESP32 | Description |
|--------|-----------|-------------|
| DHT22 #1 | GPIO 33 | Capteur température/humidité 1 |
| DHT22 #2 | GPIO 34 | Capteur température/humidité 2 |
| DHT22 #3 | GPIO 35 | Capteur température/humidité 3 |
| DHT22 #4 | GPIO 36 | Capteur température/humidité 4 |
| Stepper DIR | GPIO 12 | Direction moteur pas à pas |
| Stepper STEP | GPIO 13 | Pulse/Step moteur pas à pas |
| Stepper ENABLE | GPIO 32 | Enable moteur pas à pas (actif bas pour TB6600/A4988) |
| Ventilateur | GPIO 14 | Contrôle ventilateur (refroidissement) |
| Humidificateur | GPIO 15 | Contrôle humidificateur |
| LED Verte | GPIO 16 | Temp & Humidité OK (±1.5%) |
| LED Orange | GPIO 17 | Temp ou Humidité < normal |
| LED Rouge | GPIO 18 | Temp ou Humidité > normal |
| LED Bleue | GPIO 19 | Connexion serveur NOK |
| Bouton Stepper | GPIO 23 | Lancement manuel moteur NEMA |
| Bouton LCD Scroll | GPIO 27 | Défilement manuel écran LCD |
| LCD I2C SDA | GPIO 21 | Données I2C (défaut ESP32) |
| LCD I2C SCL | GPIO 22 | Horloge I2C (défaut ESP32) |

> Attention : les broches GPIO0, GPIO2 et GPIO15 sont des strapping pins sur ESP32. Les utiliser pour des capteurs DHT22 peut empêcher le démarrage normal du module. Le code source utilise les broches GPIO 33, 34, 35 et 36 pour les capteurs DHT.

---

## Détail par module

### 1. Capteurs DHT22 (x4)

```
DHT22 #1          DHT22 #2          DHT22 #3          DHT22 #4
┌─────┐           ┌─────┐           ┌─────┐           ┌─────┐
│ VCC │──3.3V     │ VCC │──3.3V     │ VCC │──3.3V     │ VCC │──3.3V
│ DATA│──GPIO 33  │ DATA│──GPIO 34  │ DATA│──GPIO 35  │ DATA│──GPIO 36
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
| Verte | ON | Température ET humidité dans la plage normale (±1.5%) |
| Orange | ON | Température OU humidité en dessous de la normale |
| Rouge | ON | Température OU humidité au-dessus de la normale |
| Bleue | ON | Connexion serveur NON établie (mode autonome ou échec)

---

### 4. Boutons poussoirs (x2)

```
Bouton poussoir
┌─────────┐
│    O────│── GPIO 23 (INPUT_PULLUP)
│    O────│── GND
└─────────┘
```

- Bouton Stepper : GPIO 23 → bouton → GND
- Bouton LCD Scroll : GPIO 27 → bouton → GND

**Note**: Les boutons utilisent la résistance pull-up interne de l'ESP32.
Appuyer sur le bouton connecte la pin GPIO à GND.

---

### 5. Moteur pas à pas (Stepper)

#### Option A: Driver TB6600 (RECOMMANDÉ)

```
TB6600 Stepper Driver
┌─────────────────────────────────────────────────┐
│ PUL+ (5V/3.3V) │─────────────────│── 3.3V       │
│ DIR+ (5V/3.3V) │─────────────────│── 3.3V       │
│ ENA+ (5V/3.3V) │─────────────────│── 3.3V       │
│ PUL- (STEP)    │─────────────────│── GPIO 13    │
│ DIR- (DIR)     │─────────────────│── GPIO 12    │
│ ENA- (ENABLE)  │─────────────────│── GPIO 32    │
├─────────────────────────────────────────────────┤
│ VCC / GND      │─────────────────│── Alim 12V-24V
│ A+, A-, B+, B- │─────────────────│── Moteur NEMA
└─────────────────────────────────────────────────┘
```

> Pour l’ESP32, utilisez la logique 3.3V sur PUL+/DIR+/ENA+. Assurez-vous que le GND de l’ESP32 est commun avec l’alimentation du TB6600 si vous utilisez la référence de signal du module.

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
│ DIR    │──────────────│── GPIO 12 (Direction)
│ STEP   │──────────────│── GPIO 13 (Step)
│ MS1, MS2, MS3 │────│── Config Microstep (optionnel)
│ ENABLE │──────────────│── GPIO 32 (Enable, actif bas)
│ GND    │──────────────│── GND
│ +5V    │──────────────│── 5V
└─────────────────────┘
       │
       └── NEMA 17 Stepper Motor (12V)
```

**Mode de fonctionnement:**
- Si MS1/MS2/MS3 non connectés: Full-step
- Connecter des pins GPIO pour contrôler le microstep
- `ENABLE` est actif bas : LOW active le driver, HIGH désactive les bobines

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
    DHT22 #1 ──────────────────────│ GPIO 33         │
    DHT22 #2 ──────────────────────│ GPIO 34         │
    DHT22 #3 ──────────────────────│ GPIO 35         │
    DHT22 #4 ──────────────────────│ GPIO 36         │
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
    Bouton LCD Scroll ──────────────│ GPIO 27         │
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
const float TOLERANCE_PERCENT = 1.5;      // Tolérance ±1.5%

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
| Temp ET Humidité dans ±1.5% de la cible | Verte |
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
