
#include <WiFi.h>
#include <PubSubClient.h>
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
#define STEPPER_ENABLE_PIN 32  // Enable pin pour couper le courant quand le stepper est à l'arrêt
#define STEPPER_ENABLE_ACTIVE_STATE LOW
#define STEPPER_ENABLE_DISABLE_STATE HIGH
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

// WiFi credentials
const char* ssid = "Airbox-4D56";
const char* password = "16017581";

// MQTT Configuration
const char* mqttServer = "192.168.1.100";  // Adresse du broker MQTT
const int mqttPort = 1883;
const char* mqttUser = "";                 // Laisser vide si pas d'auth
const char* mqttPassword = "";             // Laisser vide si pas d'auth
const char* mqttClientId = "ESP32_SHT30_Incubator";

// MQTT Topics
const char* TOPIC_SENSOR_DATA = "incubator/sensors/data";
const char* TOPIC_AUTOMATION_STATUS = "incubator/automation/status";
const char* TOPIC_AUTOMATION_FAN = "incubator/automation/fan";
const char* TOPIC_AUTOMATION_HUMIDIFIER = "incubator/automation/humidifier";
const char* TOPIC_AUTOMATION_STEPPER = "incubator/automation/stepper";

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
const int MAX_MQTT_RETRIES = 10;  // Nombre max de tentatives avant mode autonome

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

AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_STEP, STEPPER_PIN_DIR);

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ============== VARIABLES D'ÉTAT ==============

bool fanOn = false;
bool humidifierOn = false;
bool autonomousMode = false;
int mqttFailCount = 0;
bool mqttConnected = false;
bool buttonPressed = false;
bool stepperEnabled = false;
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

// ============== MQTT CALLBACK ==============

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.printf("MQTT Message [%s]: %s\n", topic, message.c_str());

  // Parse JSON message
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);

  if (error) {
    Serial.println("Erreur parsing JSON MQTT");
    return;
  }

  // Handle fan command
  if (String(topic) == TOPIC_AUTOMATION_FAN) {
    bool fanStatus = doc["state"] | false;
    digitalWrite(FAN_PIN, fanStatus ? HIGH : LOW);
    fanOn = fanStatus;
    Serial.printf("Fan: %s\n", fanOn ? "ON" : "OFF");
  }

  // Handle humidifier command
  if (String(topic) == TOPIC_AUTOMATION_HUMIDIFIER) {
    bool humidStatus = doc["state"] | false;
    digitalWrite(HUMIDIFIER_PIN, humidStatus ? HIGH : LOW);
    humidifierOn = humidStatus;
    Serial.printf("Humidificateur: %s\n", humidifierOn ? "ON" : "OFF");
  }

  // Handle stepper command
  if (String(topic) == TOPIC_AUTOMATION_STEPPER) {
    bool stepperStatus = doc["activate"] | false;
    if (stepperStatus) {
      Serial.println("Rotation stepper activee via MQTT");
      stepper.setMaxSpeed(STEPPER_SPEED);
      enableStepper();
      stepper.moveTo(stepper.currentPosition() + STEPPER_ROTATION_STEPS);
    }
  }

  // Handle full automation status
  if (String(topic) == TOPIC_AUTOMATION_STATUS) {
    bool fanStatus = doc["fan"] | false;
    digitalWrite(FAN_PIN, fanStatus ? HIGH : LOW);
    fanOn = fanStatus;

    bool humidStatus = doc["humidifier"] | false;
    digitalWrite(HUMIDIFIER_PIN, humidStatus ? HIGH : LOW);
    humidifierOn = humidStatus;

    Serial.printf("Status recu - Fan: %s, Humidificateur: %s\n",
                  fanOn ? "ON" : "OFF",
                  humidifierOn ? "ON" : "OFF");
  }
}

void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  int retries = 0;
  while (!mqttClient.connected() && retries < 5) {
    Serial.print("Connexion MQTT...");

    bool connected;
    if (strlen(mqttUser) > 0) {
      connected = mqttClient.connect(mqttClientId, mqttUser, mqttPassword);
    } else {
      connected = mqttClient.connect(mqttClientId);
    }

    if (connected) {
      Serial.println("connecte!");
      mqttConnected = true;
      mqttFailCount = 0;

      // Subscribe to automation topics
      mqttClient.subscribe(TOPIC_AUTOMATION_STATUS);
      mqttClient.subscribe(TOPIC_AUTOMATION_FAN);
      mqttClient.subscribe(TOPIC_AUTOMATION_HUMIDIFIER);
      mqttClient.subscribe(TOPIC_AUTOMATION_STEPPER);

      Serial.println("Abonne aux topics d'automation");

      // Exit autonomous mode if connected
      if (autonomousMode) {
        Serial.println("Sortie du mode autonome - MQTT reconnecte");
        autonomousMode = false;
      }
    } else {
      Serial.printf("echec, rc=%d - nouvelle tentative...\n", mqttClient.state());
      retries++;
      delay(2000);
    }
  }

  if (!mqttClient.connected()) {
    mqttFailCount++;
    mqttConnected = false;
    checkAutonomousMode();
  }
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

bool publishSensorData(const String& jsonPayload) {
  if (autonomousMode) {
    Serial.println("Mode autonome actif - Pas d'envoi MQTT");
    return false;
  }

  if (!mqttClient.connected()) {
    Serial.println("MQTT non connecte");
    mqttFailCount++;
    checkAutonomousMode();
    return false;
  }

  bool success = mqttClient.publish(TOPIC_SENSOR_DATA, jsonPayload.c_str());

  if (success) {
    Serial.println("Donnees publiees sur MQTT");
    mqttFailCount = 0;
  } else {
    Serial.println("Erreur publication MQTT");
    mqttFailCount++;
    checkAutonomousMode();
  }

  return success;
}

void checkAutonomousMode() {
  if (mqttFailCount >= MAX_MQTT_RETRIES && !autonomousMode) {
    autonomousMode = true;
    Serial.println("\n**************************************************");
    Serial.println("* ATTENTION: Mode autonome active!               *");
    Serial.printf("* %d tentatives de connexion MQTT echouees       *\n", MAX_MQTT_RETRIES);
    Serial.println("* Le systeme fonctionne en mode secours          *");
    Serial.println("**************************************************\n");
  }
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

void enableStepper() {
  if (!stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_STATE);
    stepperEnabled = true;
  }
}

void disableStepper() {
  if (stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_DISABLE_STATE);
    stepperEnabled = false;
  }
}

void checkStepperButton() {
  const unsigned long DEBOUNCE_DELAY = 200;

  if (digitalRead(BUTTON_STEPPER_PIN) == LOW) {
    if (millis() - lastButtonPress > DEBOUNCE_DELAY) {
      lastButtonPress = millis();
      buttonPressed = true;

      Serial.println("Bouton presse - Lancement rotation stepper");

      stepper.setMaxSpeed(STEPPER_SPEED);
      enableStepper();
      stepper.moveTo(stepper.currentPosition() + STEPPER_ROTATION_STEPS);
    }
  }
}

void printStatus(SensorData sensors[], int count, float avgTemp, float avgHumid, int failedCount) {
  Serial.println("\n========== STATUS (SHT30 + MQTT) ==========");
  Serial.printf("Capteur 1: %.1f°C, %.1f%%\n", sensors[0].temperature, sensors[0].humidity);
  Serial.printf("Capteur 2: %.1f°C, %.1f%%\n", sensors[1].temperature, sensors[1].humidity);
  Serial.printf("Capteur 3: %.1f°C, %.1f%%\n", sensors[2].temperature, sensors[2].humidity);
  Serial.printf("Capteur 4: %.1f°C, %.1f%%\n", sensors[3].temperature, sensors[3].humidity);
  Serial.printf("Moyenne: %.1f°C, %.1f%%\n", avgTemp, avgHumid);
  Serial.printf("Ventilateur: %s\n", fanOn ? "ON" : "OFF");
  Serial.printf("Humidificateur: %s\n", humidifierOn ? "ON" : "OFF");
  Serial.printf("Capteurs defaillants: %d\n", failedCount);
  Serial.printf("MQTT connecte: %s\n", mqttClient.connected() ? "Oui" : "Non");
  Serial.println("============================================\n");
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

  Serial.println("\n=== ESP32 SHT30 MQTT Controller ===\n");

  // Connect to WiFi
  connectWiFi();

  // Initialize MQTT
  mqttClient.setServer(mqttServer, mqttPort);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(1024);

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
  pinMode(STEPPER_ENABLE_PIN, OUTPUT);
  disableStepper();
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
  lcd.print("SHT30 MQTT");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");

  // Connect to MQTT
  connectMQTT();

  Serial.println("Initialisation terminee\n");
}

// ============== LOOP ==============

void loop() {
  // Reconnect WiFi if disconnected
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Reconnect MQTT if disconnected
  if (!mqttClient.connected()) {
    connectMQTT();
  }

  // Process MQTT messages
  mqttClient.loop();

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

  // Publish data to MQTT
  bool mqttSuccess = false;
  if (!autonomousMode) {
    mqttSuccess = publishSensorData(jsonPayload);
  }

  // Apply backup logic if in autonomous mode or MQTT disconnected
  if (autonomousMode || !mqttClient.connected()) {
    applyBackupLogic(avgTemperature, avgHumidity);
  }

  // Check manual stepper button
  checkStepperButton();

  // Update status LEDs
  updateStatusLEDs(avgTemperature, avgHumidity, mqttSuccess || mqttConnected);

  // Print status
  printStatus(sensors, NUM_SENSORS, avgTemperature, avgHumidity, numFailedSensors);
  if (autonomousMode) {
    Serial.println(">>> MODE AUTONOME ACTIF <<<");
  }

  // Display on LCD
  displayStatusOnLCD(avgTemperature, avgHumidity);

  // Run stepper if needed
  if (stepper.isRunning()) {
    enableStepper();
    stepper.run();
  } else {
    disableStepper();
  }

  // Wait before next iteration
  delay(SEND_INTERVAL);
}
