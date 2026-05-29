
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include "Adafruit_SHT31.h"

// ============== CONFIGURATION ==============

// ============== SÉLECTION DU DRIVER STEPPER ==============
#define STEPPER_DRIVER_TYPE_TB6600 1
#define STEPPER_DRIVER_TYPE_A4988  2
#define STEPPER_DRIVER_TYPE STEPPER_DRIVER_TYPE_TB6600  // Changer à STEPPER_DRIVER_TYPE_A4988 pour utiliser l'autre driver

// Pin Definitions
#define STEPPER_PIN_DIR   12  // Direction (pour TB6600 et A4988)
#define STEPPER_PIN_STEP  13  // Step/Pulse (pour TB6600 et A4988)
#define STEPPER_PIN_3     25  // Optionnel pour A4988 FULL4WIRE
#define STEPPER_PIN_4     26  // Optionnel pour A4988 FULL4WIRE
#define FAN_PIN         14
#define HUMIDIFIER_PIN  15

// LED Status Pins
#define LED_GREEN_PIN   16  // Température et humidité OK (±2%)
#define LED_ORANGE_PIN  17  // Température ou humidité < normal
#define LED_RED_PIN     18  // Température ou humidité > normal
#define LED_BLUE_PIN    19  // Connexion serveur NOK

// Button Pin
#define BUTTON_STEPPER_PIN  23  // Bouton pour lancer le stepper manuellement

// I2C Pins (ESP32 default)
#define I2C_SDA         21
#define I2C_SCL         22

// LCD I2C (adresse 0x27 par défaut, ajuster si nécessaire)
#define LCD_ADDRESS     0x27
#define LCD_COLS        16
#define LCD_ROWS        2

// SHT30 I2C Addresses (peuvent être 0x44 ou 0x45)
#define SHT30_1_ADDRESS 0x44
#define SHT30_2_ADDRESS 0x45
// Pour plus de capteurs, utiliser un multiplexeur I2C (TCA9548A)

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
const float TOLERANCE_PERCENT = 1.5;      // Tolérance ±1.5%

// Seuils calculés
const float TEMP_MIN = TEMP_TARGET * (1.0 - (TOLERANCE_PERCENT / 100.0));
const float TEMP_MAX = TEMP_TARGET * (1.0 + TOLERANCE_PERCENT / 100.0);
const float HUMIDITY_MIN = HUMIDITY_TARGET * (1.0 - TOLERANCE_PERCENT / 100.0);
const float HUMIDITY_MAX = HUMIDITY_TARGET * (1.0 + TOLERANCE_PERCENT / 100.0);

// Timing
const unsigned long SEND_INTERVAL = 5000;  // 5 secondes

// Mode autonome
const int MAX_SERVER_RETRIES = 10;  // Nombre max de tentatives avant mode autonome

// ============== CONFIGURATION STEPPER PAR DRIVER ==============
#if STEPPER_DRIVER_TYPE == STEPPER_DRIVER_TYPE_TB6600
  #define STEPPER_MAX_SPEED         1000    // steps/sec
  #define STEPPER_ACCELERATION      2000    // steps/sec²
  #define STEPPER_STEPS_PER_ROTATION 200    // 200 steps = 1 rotation
  #define STEPPER_ROTATION_STEPS    (STEPPER_STEPS_PER_ROTATION * 5)  // 5 rotations
  #define STEPPER_SPEED             300
  static const char* DRIVER_NAME = "TB6600 (DIR/STEP)";
#else
  #define STEPPER_MAX_SPEED         300     // steps/sec
  #define STEPPER_ACCELERATION      1000    // steps/sec²
  #define STEPPER_STEPS_PER_ROTATION 200
  #define STEPPER_ROTATION_STEPS    (STEPPER_STEPS_PER_ROTATION * 5)
  #define STEPPER_SPEED             100
  static const char* DRIVER_NAME = "A4988 (DIR/STEP)";
#endif

// ============== OBJETS GLOBAUX ==============

// SHT30 sensors (2 capteurs avec adresses différentes)
Adafruit_SHT31 sht30_1 = Adafruit_SHT31();
Adafruit_SHT31 sht30_2 = Adafruit_SHT31();

AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_DIR, STEPPER_PIN_STEP);

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// ============== VARIABLES D'ÉTAT ==============

bool fanOn = false;
bool humidifierOn = false;
bool autonomousMode = false;
int serverFailCount = 0;
bool serverConnected = false;
bool buttonPressed = false;
unsigned long lastButtonPress = 0;

// Nombre de capteurs SHT30 disponibles
const int NUM_SENSORS = 2;
bool sensorAvailable[NUM_SENSORS] = {false, false};

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

bool initSHT30Sensors() {
  Wire.begin(I2C_SDA, I2C_SCL);

  // Initialiser capteur 1 (adresse 0x44)
  if (sht30_1.begin(SHT30_1_ADDRESS)) {
    Serial.println("SHT30 #1 (0x44) detecte");
    sensorAvailable[0] = true;
  } else {
    Serial.println("SHT30 #1 (0x44) non detecte");
    sensorAvailable[0] = false;
  }

  // Initialiser capteur 2 (adresse 0x45)
  if (sht30_2.begin(SHT30_2_ADDRESS)) {
    Serial.println("SHT30 #2 (0x45) detecte");
    sensorAvailable[1] = true;
  } else {
    Serial.println("SHT30 #2 (0x45) non detecte");
    sensorAvailable[1] = false;
  }

  return sensorAvailable[0] || sensorAvailable[1];
}

SensorData readSHT30(Adafruit_SHT31& sensor, int sensorNum) {
  SensorData data;

  if (!sensorAvailable[sensorNum - 1]) {
    data.valid = false;
    data.temperature = 0;
    data.humidity = 0;
    return data;
  }

  data.temperature = sensor.readTemperature();
  data.humidity = sensor.readHumidity();
  data.valid = !isnan(data.humidity) && !isnan(data.temperature);

  if (!data.valid) {
    Serial.printf("Capteur SHT30 #%d: ERREUR de lecture\n", sensorNum);
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

  if (!serverOk || autonomousMode) {
    digitalWrite(LED_BLUE_PIN, HIGH);
  }

  if (avgTemp <= 0 || avgHumid <= 0) {
    digitalWrite(LED_RED_PIN, HIGH);
    return;
  }

  bool tempOk = (avgTemp >= TEMP_MIN && avgTemp <= TEMP_MAX);
  bool humidOk = (avgHumid >= HUMIDITY_MIN && avgHumid <= HUMIDITY_MAX);
  bool tempLow = (avgTemp < TEMP_MIN);
  bool humidLow = (avgHumid < HUMIDITY_MIN);
  bool tempHigh = (avgTemp > TEMP_MAX);
  bool humidHigh = (avgHumid > HUMIDITY_MAX);

  if (tempOk && humidOk) {
    digitalWrite(LED_GREEN_PIN, HIGH);
  } else if (tempHigh || humidHigh) {
    digitalWrite(LED_RED_PIN, HIGH);
  } else if (tempLow || humidLow) {
    digitalWrite(LED_ORANGE_PIN, HIGH);
  }
}

bool sendDataToServer(const String& jsonPayload) {
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
      serverFailCount = 0;
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
  static unsigned long lastReconnectAttempt = 0;
  const unsigned long RECONNECT_INTERVAL = 60000;

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
      bool fanStatus = doc["fan"] | false;
      digitalWrite(FAN_PIN, fanStatus ? HIGH : LOW);
      fanOn = fanStatus;

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
        stepper.moveTo(stepper.currentPosition() + STEPPER_ROTATION_STEPS);
        stepper.setSpeed(STEPPER_SPEED);
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

  if (avgTemp > 0 && avgTemp < TEMP_MIN) {
    digitalWrite(FAN_PIN, HIGH);
    fanOn = true;
    Serial.println("Fan ON - Temperature basse, distribution chaleur");
  } else {
    digitalWrite(FAN_PIN, LOW);
    fanOn = false;
  }

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
  const unsigned long DEBOUNCE_DELAY = 200;

  if (digitalRead(BUTTON_STEPPER_PIN) == LOW) {
    if (millis() - lastButtonPress > DEBOUNCE_DELAY) {
      lastButtonPress = millis();
      buttonPressed = true;

      Serial.println("Bouton presse - Lancement rotation stepper");

      stepper.moveTo(stepper.currentPosition() + STEPPER_ROTATION_STEPS);
      stepper.setSpeed(STEPPER_SPEED);
    }
  }
}

void printStatus(SensorData sensors[], int count, float avgTemp, float avgHumid, int failedCount) {
  Serial.println("\n========== STATUS (SHT30) ==========");
  Serial.printf("Capteur 1: %.1f°C, %.1f%%\n", sensors[0].temperature, sensors[0].humidity);
  Serial.printf("Capteur 2: %.1f°C, %.1f%%\n", sensors[1].temperature, sensors[1].humidity);
  Serial.printf("Capteur 3: %.1f°C, %.1f%%\n", sensors[2].temperature, sensors[2].humidity);
  Serial.printf("Capteur 4: %.1f°C, %.1f%%\n", sensors[3].temperature, sensors[3].humidity);
  Serial.printf("Moyenne: %.1f°C, %.1f%%\n", avgTemp, avgHumid);
  Serial.printf("Ventilateur: %s\n", fanOn ? "ON" : "OFF");
  Serial.printf("Humidificateur: %s\n", humidifierOn ? "ON" : "OFF");
  Serial.printf("Capteurs defaillants: %d\n", failedCount);
  Serial.println("=====================================\n");
}

void displayStatusOnLCD(float avgTemp, float avgHumid) {
  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(avgTemp, 1);
  lcd.print("C H:");
  lcd.print(avgHumid, 0);
  lcd.print("%");
  if (autonomousMode) {
    lcd.print(" A");
  }

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

  Serial.println("\n=== ESP32 SHT30 Sensor Controller ===\n");

  // Connect to WiFi
  connectWiFi();

  // Initialize SHT30 sensors
  if (!initSHT30Sensors()) {
    Serial.println("ATTENTION: Aucun capteur SHT30 detecte!");
  }

  // Initialize stepper motor with configured parameters
  Serial.printf("Stepper Driver: %s\n", DRIVER_NAME);
  Serial.printf("Max Speed: %d steps/sec\n", STEPPER_MAX_SPEED);
  Serial.printf("Acceleration: %d steps/sec²\n", STEPPER_ACCELERATION);
  stepper.setMaxSpeed(STEPPER_MAX_SPEED);
  stepper.setAcceleration(STEPPER_ACCELERATION);

  // Initialize output pins
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HUMIDIFIER_PIN, OUTPUT);
  digitalWrite(FAN_PIN, LOW);
  digitalWrite(HUMIDIFIER_PIN, LOW);

  // Initialize status LEDs
  initLEDs();
  digitalWrite(LED_BLUE_PIN, HIGH);

  // Initialize stepper button
  pinMode(BUTTON_STEPPER_PIN, INPUT_PULLUP);

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("ESP32 SHT30");
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

  // Read all SHT30 sensors
  SensorData sensors[NUM_SENSORS];
  sensors[0] = readSHT30(sht30_1, 1);
  sensors[1] = readSHT30(sht30_2, 2);

  // Calculate averages
  float avgTemperature, avgHumidity;
  int numFailedSensors;
  calculateAverages(sensors, NUM_SENSORS, avgTemperature, avgHumidity, numFailedSensors);

  // Build JSON payload
  StaticJsonDocument<1024> payload;

  for (int i = 0; i < NUM_SENSORS; i++) {
    String sensorKey = "sensor_" + String(i + 1);
    payload[sensorKey]["temperature"] = sensors[i].temperature;
    payload[sensorKey]["humidity"] = sensors[i].humidity;
    payload[sensorKey]["valid"] = sensors[i].valid;
    payload[sensorKey]["type"] = "SHT30";
  }

  payload["average_temperature"] = avgTemperature;
  payload["average_humidity"] = avgHumidity;
  payload["fan_status"] = fanOn ? "ON" : "OFF";
  payload["humidifier_status"] = humidifierOn ? "ON" : "OFF";
  payload["numFailedSensors"] = numFailedSensors;

  String jsonPayload;
  serializeJson(payload, jsonPayload);

  // Send data to server
  bool serverSuccess = false;
  if (!autonomousMode) {
    serverSuccess = sendDataToServer(jsonPayload);
  }

  // Get automation commands from server or use backup logic
  if (autonomousMode) {
    applyBackupLogic(avgTemperature, avgHumidity);
    tryReconnectToServer();
  } else if (!getAutomationStatus()) {
    applyBackupLogic(avgTemperature, avgHumidity);
  }

  // Get stepper command from server
  if (!autonomousMode) {
    getStepperCommand();
  }

  // Check manual stepper button
  checkStepperButton();

  // Update status LEDs
  updateStatusLEDs(avgTemperature, avgHumidity, serverSuccess || serverConnected);

  // Print status
  printStatus(sensors, NUM_SENSORS, avgTemperature, avgHumidity, numFailedSensors);
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
