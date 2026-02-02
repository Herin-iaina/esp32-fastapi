
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>
#include "DHT.h"

// ============== CONFIGURATION ==============

// Pin Definitions
#define DHT_SENSOR_TYPE DHT22
#define DHT_1_PIN_DATA  0
#define DHT_2_PIN_DATA  2
#define DHT_3_PIN_DATA  4
#define DHT_4_PIN_DATA  5
#define STEPPER_PIN_1   12
#define STEPPER_PIN_2   13
#define FAN_PIN         14
#define HUMIDIFIER_PIN  15

// LED Status Pins
#define LED_GREEN_PIN   16  // Température et humidité OK (±2%)
#define LED_ORANGE_PIN  17  // Température ou humidité < normal
#define LED_RED_PIN     18  // Température ou humidité > normal
#define LED_BLUE_PIN    19  // Connexion serveur NOK

// Button Pin
#define BUTTON_STEPPER_PIN  23  // Bouton pour lancer le stepper manuellement

// LCD I2C (adresse 0x27 par défaut, ajuster si nécessaire)
#define LCD_ADDRESS     0x27
#define LCD_COLS        16
#define LCD_ROWS        2

// WiFi credentials
const char* ssid = "Airbox-4D56";
const char* password = "16017581";

// Server configuration
const char* serverIP = "192.168.1.100";  // Remplacer par l'IP du serveur
const int serverPort = 5000;
const char* apiKey = "Votre_Cle_API";

// Thresholds for backup mode
const float TEMP_TARGET = 37.7;           // Température cible
const float HUMIDITY_TARGET = 45.0;       // Humidité cible
const float TOLERANCE_PERCENT = 2.0;      // Tolérance ±2%

// Seuils calculés
const float TEMP_MIN = TEMP_TARGET * (1.0 - TOLERANCE_PERCENT / 100.0);   // 36.95°C
const float TEMP_MAX = TEMP_TARGET * (1.0 + TOLERANCE_PERCENT / 100.0);   // 38.45°C
const float HUMIDITY_MIN = HUMIDITY_TARGET * (1.0 - TOLERANCE_PERCENT / 100.0);  // 44.1%
const float HUMIDITY_MAX = HUMIDITY_TARGET * (1.0 + TOLERANCE_PERCENT / 100.0);  // 45.9%

// Timing
const unsigned long SEND_INTERVAL = 5000;  // 5 secondes

// Mode autonome
const int MAX_SERVER_RETRIES = 10;  // Nombre max de tentatives avant mode autonome

// ============== OBJETS GLOBAUX ==============

DHT dht_1(DHT_1_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_2(DHT_2_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_3(DHT_3_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_4(DHT_4_PIN_DATA, DHT_SENSOR_TYPE);

AccelStepper stepper(AccelStepper::FULL4WIRE, STEPPER_PIN_1, STEPPER_PIN_2);

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// ============== VARIABLES D'ÉTAT ==============

bool fanOn = false;
bool humidifierOn = false;
bool autonomousMode = false;        // Mode autonome activé
int serverFailCount = 0;            // Compteur d'échecs de connexion au serveur
bool serverConnected = false;       // État de connexion au serveur
bool buttonPressed = false;         // État du bouton stepper
unsigned long lastButtonPress = 0;  // Anti-rebond bouton

struct SensorData {
  float temperature;
  float humidity;
  bool valid;
};

// ============== FONCTIONS UTILITAIRES ==============

void connectWiFi() {
  Serial.print("Connexion WiFi");
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnecte au WiFi");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nEchec connexion WiFi - Mode autonome");
  }
}

SensorData readSensor(DHT& dht, int sensorNum) {
  SensorData data;
  data.humidity = dht.readHumidity();
  data.temperature = dht.readTemperature();
  data.valid = !isnan(data.humidity) && !isnan(data.temperature);

  if (!data.valid) {
    Serial.printf("Capteur %d: ERREUR de lecture\n", sensorNum);
    data.temperature = 0;
    data.humidity = 0;
  }

  return data;
}

void calculateAverages(SensorData sensors[], int count, float& avgTemp, float& avgHumid, int& failedCount) {
  float totalTemp = 0;
  float totalHumid = 0;
  int validCount = 0;
  failedCount = 0;

  for (int i = 0; i < count; i++) {
    if (sensors[i].valid) {
      totalTemp += sensors[i].temperature;
      totalHumid += sensors[i].humidity;
      validCount++;
    } else {
      failedCount++;
    }
  }

  if (validCount > 0) {
    avgTemp = totalTemp / validCount;
    avgHumid = totalHumid / validCount;
  } else {
    avgTemp = 0;
    avgHumid = 0;
  }
}

String buildServerUrl(const char* endpoint) {
  return String("http://") + serverIP + ":" + String(serverPort) + endpoint;
}

// ============== FONCTIONS LED STATUS ==============

void initLEDs() {
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_ORANGE_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);

  // Toutes les LEDs éteintes au démarrage
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_ORANGE_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
}

void setAllLEDsOff() {
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_ORANGE_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
}

void updateStatusLEDs(float avgTemp, float avgHumid, bool serverOk) {
  setAllLEDsOff();

  // LED Bleue: Connexion serveur NOK (Non OK)
  if (!serverOk || autonomousMode) {
    digitalWrite(LED_BLUE_PIN, HIGH);
  }

  // Vérifier si les valeurs sont valides
  if (avgTemp <= 0 || avgHumid <= 0) {
    // Pas de données valides - LED rouge
    digitalWrite(LED_RED_PIN, HIGH);
    return;
  }

  // Déterminer l'état température/humidité
  bool tempOk = (avgTemp >= TEMP_MIN && avgTemp <= TEMP_MAX);
  bool humidOk = (avgHumid >= HUMIDITY_MIN && avgHumid <= HUMIDITY_MAX);
  bool tempLow = (avgTemp < TEMP_MIN);
  bool humidLow = (avgHumid < HUMIDITY_MIN);
  bool tempHigh = (avgTemp > TEMP_MAX);
  bool humidHigh = (avgHumid > HUMIDITY_MAX);

  // Logique des LEDs d'état
  if (tempOk && humidOk) {
    // Tout est OK (dans la plage ±2%)
    digitalWrite(LED_GREEN_PIN, HIGH);
  } else if (tempHigh || humidHigh) {
    // Température OU humidité trop haute -> Rouge
    digitalWrite(LED_RED_PIN, HIGH);
  } else if (tempLow || humidLow) {
    // Température OU humidité trop basse -> Orange
    digitalWrite(LED_ORANGE_PIN, HIGH);
  }
}

bool sendDataToServer(const String& jsonPayload) {
  // Si en mode autonome, ne pas essayer de se connecter au serveur
  if (autonomousMode) {
    Serial.println("Mode autonome actif - Pas d'envoi au serveur");
    return false;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi non connecte");
    serverFailCount++;
    checkAutonomousMode();
    return false;
  }

  HTTPClient http;
  http.begin(buildServerUrl("/sensor/values"));
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", apiKey);

  int httpCode = http.POST(jsonPayload);

  if (httpCode > 0) {
    Serial.printf("POST /data - Code: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_CREATED) {
      Serial.println("Donnees envoyees avec succes");
      serverFailCount = 0;  // Reset du compteur en cas de succès
      serverConnected = true;
    }
  } else {
    Serial.printf("Erreur POST: %s\n", http.errorToString(httpCode).c_str());
    serverFailCount++;
    serverConnected = false;
    checkAutonomousMode();
  }

  http.end();
  return httpCode > 0;
}

void checkAutonomousMode() {
  if (serverFailCount >= MAX_SERVER_RETRIES && !autonomousMode) {
    autonomousMode = true;
    Serial.println("\n**************************************************");
    Serial.println("* ATTENTION: Mode autonome active!               *");
    Serial.printf("* %d tentatives de connexion echouees            *\n", MAX_SERVER_RETRIES);
    Serial.println("* Le systeme fonctionne en mode secours          *");
    Serial.println("**************************************************\n");
  }
}

void tryReconnectToServer() {
  // Tentative de reconnexion périodique même en mode autonome
  static unsigned long lastReconnectAttempt = 0;
  const unsigned long RECONNECT_INTERVAL = 60000;  // 1 minute

  if (autonomousMode && (millis() - lastReconnectAttempt > RECONNECT_INTERVAL)) {
    lastReconnectAttempt = millis();
    Serial.println("Tentative de reconnexion au serveur...");

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(buildServerUrl("/sensor/automation/status"));
      int httpCode = http.GET();

      if (httpCode == 200) {
        Serial.println("Serveur accessible! Sortie du mode autonome.");
        autonomousMode = false;
        serverFailCount = 0;
        serverConnected = true;
      }
      http.end();
    }
  }
}

bool getAutomationStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin(buildServerUrl("/sensor/automation/status"));
  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("Status recu: " + response);

    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, response);

    if (!error) {
      // Fan control (true si temperature < seuil)
      bool fanStatus = doc["fan"] | false;
      digitalWrite(FAN_PIN, fanStatus ? HIGH : LOW);
      fanOn = fanStatus;

      // Humidifier control (true si humidite < seuil)
      bool humidStatus = doc["humidifier"] | false;
      digitalWrite(HUMIDIFIER_PIN, humidStatus ? HIGH : LOW);
      humidifierOn = humidStatus;

      http.end();
      return true;
    } else {
      Serial.println("Erreur parsing JSON status");
    }
  } else {
    Serial.printf("GET /automation/status - Erreur: %d\n", httpCode);
  }

  http.end();
  return false;
}

bool getStepperCommand() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin(buildServerUrl("/sensor/automation/stepper"));
  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("Stepper recu: " + response);

    StaticJsonDocument<128> doc;
    DeserializationError error = deserializeJson(doc, response);

    if (!error) {
      bool stepperStatus = doc["stepper"] | false;
      if (stepperStatus) {
        Serial.println("Rotation stepper activee");
        stepper.moveTo(stepper.currentPosition() + 200);
        stepper.setSpeed(100);
      }
      http.end();
      return true;
    } else {
      Serial.println("Erreur parsing JSON stepper");
    }
  } else {
    Serial.printf("GET /automation/stepper - Erreur: %d\n", httpCode);
  }

  http.end();
  return false;
}

void applyBackupLogic(float avgTemp, float avgHumid) {
  Serial.println("Mode autonome - Logique de secours");

  // Fan control: s'active si température < normale (pour distribuer la chaleur)
  if (avgTemp > 0 && avgTemp < TEMP_MIN) {
    digitalWrite(FAN_PIN, HIGH);
    fanOn = true;
    Serial.println("Fan ON - Temperature basse, distribution chaleur");
  } else {
    digitalWrite(FAN_PIN, LOW);
    fanOn = false;
  }

  // Humidifier control: s'active si humidité < normale
  if (avgHumid > 0 && avgHumid < HUMIDITY_MIN) {
    digitalWrite(HUMIDIFIER_PIN, HIGH);
    humidifierOn = true;
    Serial.println("Humidificateur ON - Humidite basse");
  } else {
    digitalWrite(HUMIDIFIER_PIN, LOW);
    humidifierOn = false;
  }
}

// ============== GESTION BOUTON STEPPER ==============

void checkStepperButton() {
  const unsigned long DEBOUNCE_DELAY = 200;  // Anti-rebond 200ms

  // Lecture du bouton (INPUT_PULLUP = LOW quand pressé)
  if (digitalRead(BUTTON_STEPPER_PIN) == LOW) {
    // Anti-rebond
    if (millis() - lastButtonPress > DEBOUNCE_DELAY) {
      lastButtonPress = millis();
      buttonPressed = true;

      Serial.println("Bouton presse - Lancement rotation stepper");

      // Lancer le stepper (1 tour complet = 200 pas pour un moteur 1.8°/pas)
      stepper.moveTo(stepper.currentPosition() + 200);
      stepper.setSpeed(100);
    }
  }
}

void printStatus(SensorData sensors[], int count, float avgTemp, float avgHumid, int failedCount) {
  Serial.println("\n========== STATUS ==========");
  for (int i = 0; i < count; i++) {
    Serial.printf("Capteur %d: %.1f°C, %.1f%% %s\n",
                  i + 1,
                  sensors[i].temperature,
                  sensors[i].humidity,
                  sensors[i].valid ? "" : "[ERREUR]");
  }
  Serial.printf("Moyenne: %.1f°C, %.1f%%\n", avgTemp, avgHumid);
  Serial.printf("Ventilateur: %s\n", fanOn ? "ON" : "OFF");
  Serial.printf("Humidificateur: %s\n", humidifierOn ? "ON" : "OFF");
  Serial.printf("Capteurs defaillants: %d\n", failedCount);
  Serial.println("============================\n");
}

void displayStatusOnLCD(float avgTemp, float avgHumid) {
  lcd.clear();

  // Ligne 1: Temperature et Humidite moyennes
  // Format: "T:37.5C H:45.2%" ou "T:37.5C H:45% A" (A = Autonome)
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(avgTemp, 1);
  lcd.print("C H:");
  lcd.print(avgHumid, 0);  // 0 décimale pour laisser place au mode
  lcd.print("%");
  if (autonomousMode) {
    lcd.print(" A");  // Indicateur mode autonome
  }

  // Ligne 2: Etat Fan et Humidificateur
  // Format: "Fan:ON  Hum:OFF"
  lcd.setCursor(0, 1);
  lcd.print("Fan:");
  lcd.print(fanOn ? "ON " : "OFF");
  lcd.print(" Hum:");
  lcd.print(humidifierOn ? "ON" : "OFF");
}

// ============== SETUP ==============

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n=== ESP32 Sensor Controller ===\n");

  // Connect to WiFi
  connectWiFi();

  // Initialize DHT sensors
  dht_1.begin();
  dht_2.begin();
  dht_3.begin();
  dht_4.begin();

  // Initialize stepper motor
  stepper.setMaxSpeed(300);
  stepper.setAcceleration(1000);

  // Initialize output pins
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HUMIDIFIER_PIN, OUTPUT);
  digitalWrite(FAN_PIN, LOW);
  digitalWrite(HUMIDIFIER_PIN, LOW);

  // Initialize status LEDs
  initLEDs();
  digitalWrite(LED_BLUE_PIN, HIGH);  // LED bleue pendant l'initialisation

  // Initialize stepper button (with internal pull-up)
  pinMode(BUTTON_STEPPER_PIN, INPUT_PULLUP);

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("ESP32 Sensor");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");

  Serial.println("Initialisation terminee\n");
}

// ============== LOOP ==============

void loop() {
  // Reconnect WiFi if disconnected
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Read all sensors
  SensorData sensors[4];
  sensors[0] = readSensor(dht_1, 1);
  sensors[1] = readSensor(dht_2, 2);
  sensors[2] = readSensor(dht_3, 3);
  sensors[3] = readSensor(dht_4, 4);

  // Calculate averages
  float avgTemperature, avgHumidity;
  int numFailedSensors;
  calculateAverages(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);

  // Build JSON payload
  StaticJsonDocument<1024> payload;

  for (int i = 0; i < 4; i++) {
    String sensorKey = "sensor_" + String(i + 1);
    payload[sensorKey]["temperature"] = sensors[i].temperature;
    payload[sensorKey]["humidity"] = sensors[i].humidity;
    payload[sensorKey]["valid"] = sensors[i].valid;
  }

  payload["average_temperature"] = avgTemperature;
  payload["average_humidity"] = avgHumidity;
  payload["fan_status"] = fanOn ? "ON" : "OFF";
  payload["humidifier_status"] = humidifierOn ? "ON" : "OFF";
  payload["numFailedSensors"] = numFailedSensors;

  String jsonPayload;
  serializeJson(payload, jsonPayload);

  // Send data to server (sauf si mode autonome)
  bool serverSuccess = false;
  if (!autonomousMode) {
    serverSuccess = sendDataToServer(jsonPayload);
  }

  // Get automation commands from server or use backup logic
  if (autonomousMode) {
    // Mode autonome: toujours utiliser la logique de secours
    applyBackupLogic(avgTemperature, avgHumidity);
    // Tenter une reconnexion périodique
    tryReconnectToServer();
  } else if (!getAutomationStatus()) {
    applyBackupLogic(avgTemperature, avgHumidity);
  }

  // Get stepper command from server (seulement si connecté)
  if (!autonomousMode) {
    getStepperCommand();
  }

  // Check manual stepper button
  checkStepperButton();

  // Update status LEDs
  updateStatusLEDs(avgTemperature, avgHumidity, serverSuccess || serverConnected);

  // Print status
  printStatus(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);
  if (autonomousMode) {
    Serial.println(">>> MODE AUTONOME ACTIF <<<");
  }

  // Display on LCD
  displayStatusOnLCD(avgTemperature, avgHumidity);

  // Run stepper if needed
  while (stepper.isRunning()) {
    stepper.run();
  }

  // Wait before next iteration
  delay(SEND_INTERVAL);
}
