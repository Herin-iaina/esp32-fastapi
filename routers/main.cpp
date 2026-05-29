
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>          // v7+ : JsonDocument
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>
#include "DHT.h"

// ============================================================
//  SÉLECTION DU DRIVER STEPPER
// ============================================================
#define STEPPER_DRIVER_TYPE_TB6600  1
#define STEPPER_DRIVER_TYPE_A4988   2
#define STEPPER_DRIVER_TYPE  STEPPER_DRIVER_TYPE_TB6600

// ============================================================
//  DÉFINITION DES PINS
// ============================================================
#define DHT_SENSOR_TYPE     DHT22
#define DHT_1_PIN_DATA      0
#define DHT_2_PIN_DATA      2
#define DHT_3_PIN_DATA      4
#define DHT_4_PIN_DATA      5

#define STEPPER_PIN_DIR     12
#define STEPPER_PIN_STEP    13
#define STEPPER_PIN_3       25    // Optionnel A4988 FULL4WIRE
#define STEPPER_PIN_4       26    // Optionnel A4988 FULL4WIRE
#define STEPPER_ENABLE_PIN  32    // Enable pin pour couper le courant quand le stepper est à l'arrêt
#define STEPPER_ENABLE_ACTIVE_STATE LOW
#define STEPPER_ENABLE_DISABLE_STATE HIGH

#define FAN_PIN             14
#define HUMIDIFIER_PIN      15

#define LED_GREEN_PIN       16    // Temp + humidité dans les seuils
#define LED_ORANGE_PIN      17    // Temp ou humidité en dessous du min
#define LED_RED_PIN         18    // Temp ou humidité au dessus du max
#define LED_BLUE_PIN        19    // Serveur inaccessible / mode autonome

#define BUTTON_STEPPER_PIN      23
#define BUTTON_LCD_SCROLL_PIN   27    // ✅ FIX : était 25, conflit avec STEPPER_PIN_3

#define LCD_ADDRESS         0x27
#define LCD_COLS            16
#define LCD_ROWS            2

// ============================================================
//  WIFI & SERVEUR
// ============================================================
const char* ssid       = "Airbox-AB84";
const char* password   = "7ddd6jVJPUR-deEJbxc";
const char* serverIP   = "192.168.1.100";
const int   serverPort = 5000;
const char* apiKey     = "Votre_Cle_API";

// ============================================================
//  SEUILS TEMPÉRATURE / HUMIDITÉ
// ============================================================
const float TEMP_TARGET       = 37.7f;
const float HUMIDITY_TARGET   = 45.0f;
const float TOLERANCE_PERCENT = 1.5f;

const float TEMP_MIN     = TEMP_TARGET     * (1.0f - TOLERANCE_PERCENT / 100.0f);
const float TEMP_MAX     = TEMP_TARGET     * (1.0f + TOLERANCE_PERCENT / 100.0f);
const float HUMIDITY_MIN = HUMIDITY_TARGET * (1.0f - TOLERANCE_PERCENT / 100.0f);
const float HUMIDITY_MAX = HUMIDITY_TARGET * (1.0f + TOLERANCE_PERCENT / 100.0f);

// ============================================================
//  TIMING & BUFFERS
// ============================================================
const unsigned long SEND_INTERVAL        = 5000UL;   // ms entre chaque cycle capteurs
const unsigned long LCD_SCROLL_INTERVAL  = 3000UL;   // ms entre chaque défilement auto
const unsigned long RECONNECT_INTERVAL   = 60000UL;  // ms entre tentatives de reconnexion
const unsigned long WIFI_TIMEOUT         = 15000UL;  // ms max pour connexion WiFi

const int LCD_LOG_BUFFER_SIZE = 6;
const int MAX_SERVER_RETRIES  = 10;

// ============================================================
//  CONFIGURATION STEPPER
// ============================================================
#if STEPPER_DRIVER_TYPE == STEPPER_DRIVER_TYPE_TB6600
  #define STEPPER_MAX_SPEED          1000
  #define STEPPER_ACCELERATION       2000
  #define STEPPER_STEPS_PER_ROTATION  200
  #define STEPPER_SPEED               300
  static const char* DRIVER_NAME = "TB6600 (DIR/STEP)";
#else
  #define STEPPER_MAX_SPEED           300
  #define STEPPER_ACCELERATION       1000
  #define STEPPER_STEPS_PER_ROTATION  200
  #define STEPPER_SPEED               100
  static const char* DRIVER_NAME = "A4988 (DIR/STEP)";
#endif

#define STEPPER_ROTATION_STEPS  (STEPPER_STEPS_PER_ROTATION * 5)

// ============================================================
//  OBJETS GLOBAUX
// ============================================================
DHT dht_1(DHT_1_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_2(DHT_2_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_3(DHT_3_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_4(DHT_4_PIN_DATA, DHT_SENSOR_TYPE);

AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_STEP, STEPPER_PIN_DIR);
//                                                       ^^^^        ^^^
// AccelStepper::DRIVER → (STEP, DIR) — ordre important !

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// ============================================================
//  STRUCTURES DE DONNÉES
// ============================================================
struct SensorData {
  float temperature = 0.0f;
  float humidity    = 0.0f;
  bool  valid       = false;
};

// ============================================================
//  VARIABLES D'ÉTAT GLOBALES
// ============================================================
bool  fanOn           = false;
bool  humidifierOn    = false;
bool  autonomousMode  = false;
bool  serverConnected = false;
bool  serverSuccess   = false;
int   serverFailCount = 0;

float avgTemperature  = 0.0f;
float avgHumidity     = 0.0f;
int   numFailedSensors = 0;
bool  stepperEnabled   = false;

// Boutons
unsigned long lastButtonPress       = 0;
unsigned long lastScrollButtonPress = 0;

// LCD log ring buffer
String lcdLogBuffer[LCD_LOG_BUFFER_SIZE];
int    lcdLogCount = 0;
int    lcdLogIndex = 0;
unsigned long lastLogScroll = 0;

// ============================================================
//  UTILITAIRES LCD LOG
// ============================================================

void printLCDLine(int row, const String& line) {
  lcd.setCursor(0, row);
  lcd.print(line);
  // Efface le reste de la ligne sans lcd.clear() → évite le scintillement
  for (int i = line.length(); i < LCD_COLS; i++) lcd.print(' ');
}

void pushLCDLog(const String& msg) {
  String text = (msg.length() > LCD_COLS) ? msg.substring(0, LCD_COLS) : msg;
  // Déduplique les messages consécutifs identiques
  if (lcdLogCount > 0 && lcdLogBuffer[(lcdLogCount - 1) % LCD_LOG_BUFFER_SIZE] == text) return;

  if (lcdLogCount < LCD_LOG_BUFFER_SIZE) {
    lcdLogBuffer[lcdLogCount++] = text;
  } else {
    // Décale le buffer (FIFO circulaire)
    for (int i = 0; i < LCD_LOG_BUFFER_SIZE - 1; i++) {
      lcdLogBuffer[i] = lcdLogBuffer[i + 1];
    }
    lcdLogBuffer[LCD_LOG_BUFFER_SIZE - 1] = text;
    if (lcdLogIndex > 0) lcdLogIndex--;
  }
}

void setLCDLog(const String& msg) { pushLCDLog(msg); }

String getCurrentLCDLog() {
  if (lcdLogCount == 0) return "";
  if (lcdLogIndex >= lcdLogCount) lcdLogIndex = 0;
  return lcdLogBuffer[lcdLogIndex];
}

void advanceLCDLog() {
  if (lcdLogCount > 1) lcdLogIndex = (lcdLogIndex + 1) % lcdLogCount;
}

void updateLCDScroll(unsigned long now) {
  if (now - lastLogScroll >= LCD_SCROLL_INTERVAL) {
    lastLogScroll = now;
    advanceLCDLog();
  }
}

// ============================================================
//  AFFICHAGE LCD
// ============================================================

void displayStatusOnLCD(float avgTemp, float avgHumid) {
  // Ligne 1 : "T:37.5C H:45%" + " A" si mode autonome
  String line1 = "T:" + String(avgTemp, 1) + "C H:" + String((int)avgHumid) + "%";
  if (autonomousMode) {
    if ((int)line1.length() <= LCD_COLS - 2)
      line1 += " A";
    else
      line1 = line1.substring(0, LCD_COLS - 2) + " A";
  }
  printLCDLine(0, line1);
  // Ligne 2 : log courant
  printLCDLine(1, getCurrentLCDLog());
}

// ============================================================
//  WIFI — CONNEXION NON-BLOQUANTE
// ============================================================

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("Connexion WiFi...");
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnecte — IP: " + WiFi.localIP().toString());
    setLCDLog("WiFi connecte");
  } else {
    Serial.println("\nEchec WiFi");
    setLCDLog("WiFi echec");
  }
}

// ============================================================
//  UTILITAIRES SERVEUR
// ============================================================

String buildServerUrl(const char* endpoint) {
  return String("http://") + serverIP + ":" + serverPort + endpoint;
}

void checkAutonomousMode() {
  if (!autonomousMode && serverFailCount >= MAX_SERVER_RETRIES) {
    autonomousMode = true;
    Serial.println("\n*** MODE AUTONOME ACTIVE ***");
    Serial.printf("  %d echecs consecutifs\n", MAX_SERVER_RETRIES);
    setLCDLog("Mode autonome");
  }
}

// ============================================================
//  ENVOI DES DONNÉES
// ============================================================

bool sendDataToServer(const String& jsonPayload) {
  if (autonomousMode || WiFi.status() != WL_CONNECTED) {
    if (!autonomousMode) { serverFailCount++; checkAutonomousMode(); }
    return false;
  }

  WiFiClient wifiClient;
  HTTPClient http;
  http.begin(wifiClient, buildServerUrl("/sensor/values"));
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", apiKey);

  int code = http.POST(jsonPayload);
  bool success = false;

  if (code > 0) {
    Serial.printf("POST /sensor/values → %d\n", code);
    // ✅ FIX : succès uniquement sur 200 ou 201 (pas sur les 4xx/5xx)
    if (code == HTTP_CODE_OK || code == HTTP_CODE_CREATED) {
      setLCDLog("Serveur OK");
      serverFailCount = 0;
      serverConnected = true;
      success = true;
    } else {
      Serial.printf("Reponse inattendue: %d\n", code);
      setLCDLog("Serveur err " + String(code));
      serverFailCount++;
      serverConnected = false;
      checkAutonomousMode();
    }
  } else {
    Serial.printf("POST echec: %s\n", http.errorToString(code).c_str());
    setLCDLog("POST echec");
    serverFailCount++;
    serverConnected = false;
    checkAutonomousMode();
  }

  http.end();
  return success;
}

// ============================================================
//  RECONNEXION PÉRIODIQUE (mode autonome)
// ============================================================

void tryReconnectToServer() {
  static unsigned long lastReconnectAttempt = 0;
  if (!autonomousMode) return;
  if (millis() - lastReconnectAttempt < RECONNECT_INTERVAL) return;

  lastReconnectAttempt = millis();
  if (WiFi.status() != WL_CONNECTED) { connectWiFi(); return; }

  Serial.println("Tentative de reconnexion au serveur...");
  WiFiClient wifiClient;
  HTTPClient http;
  http.begin(wifiClient, buildServerUrl("/sensor/automation/status"));
  int code = http.GET();
  http.end();

  if (code == HTTP_CODE_OK) {
    Serial.println("Serveur accessible — sortie du mode autonome");
    autonomousMode  = false;
    serverFailCount = 0;
    serverConnected = true;
    setLCDLog("Serveur retrouve");
  }
}

// ============================================================
//  COMMANDES AUTOMATION
// ============================================================

bool getAutomationStatus() {
  if (autonomousMode || WiFi.status() != WL_CONNECTED) return false;

  WiFiClient wifiClient;
  HTTPClient http;
  http.begin(wifiClient, buildServerUrl("/sensor/automation/status"));
  int code = http.GET();

  if (code == HTTP_CODE_OK) {
    String response = http.getString();
    JsonDocument doc;
    if (!deserializeJson(doc, response)) {
      bool fanCmd   = doc["fan"]        | false;
      bool humidCmd = doc["humidifier"] | false;
      digitalWrite(FAN_PIN,        fanCmd   ? HIGH : LOW);
      digitalWrite(HUMIDIFIER_PIN, humidCmd ? HIGH : LOW);
      fanOn        = fanCmd;
      humidifierOn = humidCmd;
      setLCDLog("Cmd automation");
      http.end();
      return true;
    }
    Serial.println("JSON status: erreur parsing");
    setLCDLog("JSON statut err");
  } else {
    Serial.printf("GET /automation/status → %d\n", code);
  }

  http.end();
  return false;
}

bool getStepperCommand() {
  if (autonomousMode || WiFi.status() != WL_CONNECTED) return false;

  WiFiClient wifiClient;
  HTTPClient http;
  http.begin(wifiClient, buildServerUrl("/sensor/automation/stepper"));
  int code = http.GET();

  if (code == HTTP_CODE_OK) {
    String response = http.getString();
    JsonDocument doc;
    if (!deserializeJson(doc, response)) {
      if (doc["stepper"] | false) {
        Serial.println("Rotation stepper activee (serveur)");
        setLCDLog("Stepper ON");
        stepper.setMaxSpeed(STEPPER_SPEED);
        enableStepper();
        stepper.moveTo(stepper.currentPosition() + STEPPER_ROTATION_STEPS);
      }
      http.end();
      return true;
    }
    Serial.println("JSON stepper: erreur parsing");
    setLCDLog("JSON stepper err");
  } else {
    Serial.printf("GET /automation/stepper → %d\n", code);
  }

  http.end();
  return false;
}

// ============================================================
//  LOGIQUE DE SECOURS (MODE AUTONOME)
// ============================================================

void applyBackupLogic(float avgTemp, float avgHumid) {
  // Ventilateur : distribue la chaleur si température trop basse
  bool fan = (avgTemp > 0.0f && avgTemp < TEMP_MIN);
  digitalWrite(FAN_PIN, fan ? HIGH : LOW);
  fanOn = fan;
  if (fan) Serial.println("[AUTO] Fan ON — temp basse");

  // Humidificateur : s'active si humidité insuffisante
  bool humid = (avgHumid > 0.0f && avgHumid < HUMIDITY_MIN);
  digitalWrite(HUMIDIFIER_PIN, humid ? HIGH : LOW);
  humidifierOn = humid;
  if (humid) Serial.println("[AUTO] Humidificateur ON — humidite basse");
}

// ============================================================
//  CAPTEURS DHT
// ============================================================

SensorData readSensor(DHT& dht, int num) {
  SensorData data;
  data.humidity    = dht.readHumidity();
  data.temperature = dht.readTemperature();
  data.valid       = !isnan(data.humidity) && !isnan(data.temperature);
  if (!data.valid) {
    Serial.printf("Capteur %d: ERREUR\n", num);
    data.temperature = 0.0f;
    data.humidity    = 0.0f;
  }
  return data;
}

void calculateAverages(SensorData sensors[], int count,
                       float& avgTemp, float& avgHumid, int& failedCount) {
  float tTotal = 0, hTotal = 0;
  int   valid  = 0;
  failedCount  = 0;

  for (int i = 0; i < count; i++) {
    if (sensors[i].valid) {
      tTotal += sensors[i].temperature;
      hTotal += sensors[i].humidity;
      valid++;
    } else {
      failedCount++;
    }
  }

  avgTemp  = valid > 0 ? tTotal / valid : 0.0f;
  avgHumid = valid > 0 ? hTotal / valid : 0.0f;
}

// ============================================================
//  LEDs DE STATUT
// ============================================================

void initLEDs() {
  const int pins[] = { LED_GREEN_PIN, LED_ORANGE_PIN, LED_RED_PIN, LED_BLUE_PIN };
  for (int p : pins) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
}

void setAllLEDsOff() {
  digitalWrite(LED_GREEN_PIN,  LOW);
  digitalWrite(LED_ORANGE_PIN, LOW);
  digitalWrite(LED_RED_PIN,    LOW);
  digitalWrite(LED_BLUE_PIN,   LOW);
}

void updateStatusLEDs(float avgTemp, float avgHumid, bool serverOk) {
  setAllLEDsOff();

  if (!serverOk || autonomousMode)  digitalWrite(LED_BLUE_PIN, HIGH);
  if (avgTemp <= 0 || avgHumid <= 0) { digitalWrite(LED_RED_PIN, HIGH); return; }

  bool tempOk  = avgTemp  >= TEMP_MIN     && avgTemp  <= TEMP_MAX;
  bool humidOk = avgHumid >= HUMIDITY_MIN && avgHumid <= HUMIDITY_MAX;

  if (tempOk && humidOk) {
    digitalWrite(LED_GREEN_PIN, HIGH);
  } else if (avgTemp > TEMP_MAX || avgHumid > HUMIDITY_MAX) {
    digitalWrite(LED_RED_PIN, HIGH);
  } else {
    digitalWrite(LED_ORANGE_PIN, HIGH);
  }
}

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

// ============================================================
//  BOUTONS
// ============================================================

void checkStepperButton() {
  const unsigned long DEBOUNCE = 200;
  if (digitalRead(BUTTON_STEPPER_PIN) == LOW && millis() - lastButtonPress > DEBOUNCE) {
    lastButtonPress = millis();
    Serial.println("Bouton stepper — rotation manuelle");
    setLCDLog("Stepper manuel");
    stepper.setMaxSpeed(STEPPER_SPEED);
    enableStepper();
    stepper.moveTo(stepper.currentPosition() + STEPPER_ROTATION_STEPS);
  }
}

void checkLCDScrollButton() {
  const unsigned long DEBOUNCE = 200;
  if (digitalRead(BUTTON_LCD_SCROLL_PIN) == LOW && millis() - lastScrollButtonPress > DEBOUNCE) {
    lastScrollButtonPress = millis();
    Serial.println("Bouton LCD — defilement manuel");
    advanceLCDLog();
  }
}

// ============================================================
//  LOGS SÉRIE
// ============================================================

void printStatus(SensorData sensors[], int count, float avgTemp, float avgHumid, int failed) {
  Serial.println("\n========== STATUS ==========");
  for (int i = 0; i < count; i++) {
    Serial.printf("  Capteur %d: %.1f°C, %.1f%% %s\n",
                  i + 1,
                  sensors[i].temperature,
                  sensors[i].humidity,
                  sensors[i].valid ? "" : "[ERREUR]");
  }
  Serial.printf("  Moyenne   : %.2f°C, %.2f%%\n", avgTemp, avgHumid);
  Serial.printf("  Seuils    : T [%.2f–%.2f]  H [%.2f–%.2f]\n",
                TEMP_MIN, TEMP_MAX, HUMIDITY_MIN, HUMIDITY_MAX);
  Serial.printf("  Fan: %s  |  Humidif: %s  |  Defauts: %d\n",
                fanOn ? "ON" : "OFF", humidifierOn ? "ON" : "OFF", failed);
  if (autonomousMode) Serial.println("  >>> MODE AUTONOME ACTIF <<<");
  Serial.println("============================\n");
}

// ============================================================
//  SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n=== ESP32 Sensor Controller v3 ===");
  Serial.printf("Driver : %s\n", DRIVER_NAME);
  Serial.printf("Vitesse: %d sps  |  Accel: %d sps²\n", STEPPER_MAX_SPEED, STEPPER_ACCELERATION);
  Serial.printf("Seuils : T [%.2f–%.2f]°C  |  H [%.2f–%.2f]%%\n\n",
                TEMP_MIN, TEMP_MAX, HUMIDITY_MIN, HUMIDITY_MAX);

  // LCD (init avant WiFi pour afficher les états)
  lcd.init();
  lcd.backlight();
  printLCDLine(0, "ESP32 Sensor v3");
  printLCDLine(1, "Init...");
  setLCDLog("Initializing...");

  // WiFi
  connectWiFi();

  // Capteurs DHT
  dht_1.begin(); dht_2.begin(); dht_3.begin(); dht_4.begin();

  // Stepper
  stepper.setMaxSpeed(STEPPER_MAX_SPEED);
  stepper.setAcceleration(STEPPER_ACCELERATION);
  pinMode(STEPPER_ENABLE_PIN, OUTPUT);
  disableStepper();

  // Actionneurs
  pinMode(FAN_PIN,        OUTPUT); digitalWrite(FAN_PIN,        LOW);
  pinMode(HUMIDIFIER_PIN, OUTPUT); digitalWrite(HUMIDIFIER_PIN, LOW);

  // LEDs
  initLEDs();
  digitalWrite(LED_BLUE_PIN, HIGH);  // Bleue allumée pendant l'init

  // Boutons avec pull-up interne
  pinMode(BUTTON_STEPPER_PIN,    INPUT_PULLUP);
  pinMode(BUTTON_LCD_SCROLL_PIN, INPUT_PULLUP);

  Serial.println("Initialisation terminee.\n");
}

// ============================================================
//  LOOP
// ============================================================

void loop() {
  static unsigned long lastSendTime = 0;
  unsigned long now = millis();

  // --- Watchdog WiFi (non-bloquant) ---
  if (WiFi.status() != WL_CONNECTED && now - lastSendTime >= SEND_INTERVAL) {
    connectWiFi();
  }

  // --- Reconnexion serveur si mode autonome (indépendant de SEND_INTERVAL) ---
  tryReconnectToServer();

  // ----------------------------------------------------------------
  //  CYCLE PRINCIPAL toutes les SEND_INTERVAL ms
  // ----------------------------------------------------------------
  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;

    // 1. Lecture des 4 capteurs
    SensorData sensors[4];
    sensors[0] = readSensor(dht_1, 1);
    sensors[1] = readSensor(dht_2, 2);
    sensors[2] = readSensor(dht_3, 3);
    sensors[3] = readSensor(dht_4, 4);

    // 2. Calcul des moyennes
    calculateAverages(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);

    // 3. Construction du payload JSON
    JsonDocument payload;
    for (int i = 0; i < 4; i++) {
      String key = "sensor_" + String(i + 1);
      payload[key]["temperature"] = sensors[i].temperature;
      payload[key]["humidity"]    = sensors[i].humidity;
      payload[key]["valid"]       = sensors[i].valid;
    }
    payload["average_temperature"] = avgTemperature;
    payload["average_humidity"]    = avgHumidity;
    payload["fan_status"]          = fanOn        ? "ON" : "OFF";
    payload["humidifier_status"]   = humidifierOn ? "ON" : "OFF";
    payload["numFailedSensors"]    = numFailedSensors;

    String jsonPayload;
    serializeJson(payload, jsonPayload);

    // 4. Envoi au serveur
    serverSuccess = false;
    if (!autonomousMode) {
      serverSuccess = sendDataToServer(jsonPayload);
    }

    // 5. Commandes automation (ou logique de secours)
    if (autonomousMode) {
      applyBackupLogic(avgTemperature, avgHumidity);
    } else if (!getAutomationStatus()) {
      applyBackupLogic(avgTemperature, avgHumidity);
    }

    // 6. Commande stepper via serveur
    if (!autonomousMode) {
      getStepperCommand();
    }

    // 7. Logs série
    printStatus(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);
  }

  // ----------------------------------------------------------------
  //  TÂCHES CONTINUES (toutes les 100 ms)
  // ----------------------------------------------------------------
  checkStepperButton();
  checkLCDScrollButton();
  updateLCDScroll(now);
  updateStatusLEDs(avgTemperature, avgHumidity, serverSuccess || serverConnected);
  displayStatusOnLCD(avgTemperature, avgHumidity);

  if (stepper.isRunning()) {
    enableStepper();
    stepper.run();
  } else {
    disableStepper();
  }

  delay(100);
}