#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>      // v7+ : JsonDocument (remplace StaticJsonDocument/DynamicJsonDocument)
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
#define BUTTON_LCD_SCROLL_PIN 25  // Bouton pour defiler manuellement les logs LCD

// LCD I2C (adresse 0x27 par défaut, ajuster si nécessaire)
#define LCD_ADDRESS     0x27
#define LCD_COLS        16
#define LCD_ROWS        2

// WiFi credentials
const char* ssid = "Airbox-AB84";
const char* password = "7ddd6jVJPUR-deEJbxc";

// Server configuration
const char* serverIP = "192.168.1.100";  // Remplacer par l'IP du serveur
const int serverPort = 5000;
const char* apiKey = "Votre_Cle_API";

// Thresholds
const float TEMP_TARGET      = 37.7;
const float HUMIDITY_TARGET  = 45.0;
const float TOLERANCE_PERCENT = 1.5;

// Seuils calculés
const float TEMP_MIN     = TEMP_TARGET     * (1.0 - TOLERANCE_PERCENT / 100.0);  // 37.13°C
const float TEMP_MAX     = TEMP_TARGET     * (1.0 + TOLERANCE_PERCENT / 100.0);  // 38.27°C
const float HUMIDITY_MIN = HUMIDITY_TARGET * (1.0 - TOLERANCE_PERCENT / 100.0);  // 44.33%
const float HUMIDITY_MAX = HUMIDITY_TARGET * (1.0 + TOLERANCE_PERCENT / 100.0);  // 45.68%

// Timing
const unsigned long SEND_INTERVAL = 5000;  // 5 secondes
const unsigned long LCD_SCROLL_INTERVAL = 3000;  // 3 secondes pour defiler les logs
const int LCD_LOG_BUFFER_SIZE = 6;

// Mode autonome
const int MAX_SERVER_RETRIES = 10;

// ============== OBJETS GLOBAUX ==============

DHT dht_1(DHT_1_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_2(DHT_2_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_3(DHT_3_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_4(DHT_4_PIN_DATA, DHT_SENSOR_TYPE);

AccelStepper stepper(AccelStepper::FULL4WIRE, STEPPER_PIN_1, STEPPER_PIN_2);

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// ============== VARIABLES D'ÉTAT ==============

bool fanOn          = false;
bool humidifierOn   = false;
bool autonomousMode = false;
int  serverFailCount = 0;
bool serverConnected = false;
bool buttonPressed   = false;
unsigned long lastButtonPress = 0;

String lcdLogBuffer[LCD_LOG_BUFFER_SIZE];
int lcdLogCount = 0;
int lcdLogIndex = 0;
unsigned long lastLogScroll = 0;
unsigned long lastScrollButtonPress = 0;

float avgTemperature = 0;
float avgHumidity = 0;
int numFailedSensors = 0;
bool serverSuccess = false;

struct SensorData {
  float temperature;
  float humidity;
  bool  valid;
};

void printLCDLine(int row, const String& line) {
  lcd.setCursor(0, row);
  lcd.print(line);
  for (int i = line.length(); i < LCD_COLS; i++) {
    lcd.print(' ');
  }
}

void pushLCDLog(const String& msg) {
  String text = msg;
  if (text.length() > LCD_COLS) {
    text = text.substring(0, LCD_COLS);
  }
  if (lcdLogCount > 0 && lcdLogBuffer[lcdLogCount - 1] == text) {
    return;
  }
  if (lcdLogCount < LCD_LOG_BUFFER_SIZE) {
    lcdLogBuffer[lcdLogCount++] = text;
  } else {
    for (int i = 0; i < LCD_LOG_BUFFER_SIZE - 1; i++) {
      lcdLogBuffer[i] = lcdLogBuffer[i + 1];
    }
    lcdLogBuffer[LCD_LOG_BUFFER_SIZE - 1] = text;
    if (lcdLogIndex > 0) {
      lcdLogIndex--;
    }
  }
}

String getCurrentLCDLog() {
  if (lcdLogCount == 0) {
    return "";
  }
  if (lcdLogIndex >= lcdLogCount) {
    lcdLogIndex = 0;
  }
  return lcdLogBuffer[lcdLogIndex];
}

void setLCDLog(const String& msg) {
  pushLCDLog(msg);
}

void advanceLCDLog() {
  if (lcdLogCount <= 1) {
    return;
  }
  lcdLogIndex = (lcdLogIndex + 1) % lcdLogCount;
}

void updateLCDScroll(unsigned long now) {
  if (now - lastLogScroll >= LCD_SCROLL_INTERVAL) {
    lastLogScroll = now;
    advanceLCDLog();
  }
}

void checkLCDScrollButton() {
  const unsigned long DEBOUNCE_DELAY = 200;
  if (digitalRead(BUTTON_LCD_SCROLL_PIN) == LOW) {
    if (millis() - lastScrollButtonPress > DEBOUNCE_DELAY) {
      lastScrollButtonPress = millis();
      Serial.println("Bouton LCD presse - defilement manuel");
      advanceLCDLog();
    }
  }
}

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
    setLCDLog("WiFi connecte");
  } else {
    Serial.println("\nEchec connexion WiFi - Mode autonome");
    setLCDLog("WiFi echec");
  }
}

SensorData readSensor(DHT& dht, int sensorNum) {
  SensorData data;
  data.humidity    = dht.readHumidity();
  data.temperature = dht.readTemperature();
  data.valid       = !isnan(data.humidity) && !isnan(data.temperature);

  if (!data.valid) {
    Serial.printf("Capteur %d: ERREUR de lecture\n", sensorNum);
    data.temperature = 0;
    data.humidity    = 0;
  }

  return data;
}

void calculateAverages(SensorData sensors[], int count,
                       float& avgTemp, float& avgHumid, int& failedCount) {
  float totalTemp  = 0;
  float totalHumid = 0;
  int   validCount = 0;
  failedCount = 0;

  for (int i = 0; i < count; i++) {
    if (sensors[i].valid) {
      totalTemp  += sensors[i].temperature;
      totalHumid += sensors[i].humidity;
      validCount++;
    } else {
      failedCount++;
    }
  }

  if (validCount > 0) {
    avgTemp  = totalTemp  / validCount;
    avgHumid = totalHumid / validCount;
  } else {
    avgTemp  = 0;
    avgHumid = 0;
  }
}

String buildServerUrl(const char* endpoint) {
  return String("http://") + serverIP + ":" + String(serverPort) + endpoint;
}

// ============== FONCTIONS LED STATUS ==============

void initLEDs() {
  pinMode(LED_GREEN_PIN,  OUTPUT);
  pinMode(LED_ORANGE_PIN, OUTPUT);
  pinMode(LED_RED_PIN,    OUTPUT);
  pinMode(LED_BLUE_PIN,   OUTPUT);

  digitalWrite(LED_GREEN_PIN,  LOW);
  digitalWrite(LED_ORANGE_PIN, LOW);
  digitalWrite(LED_RED_PIN,    LOW);
  digitalWrite(LED_BLUE_PIN,   LOW);
}

void setAllLEDsOff() {
  digitalWrite(LED_GREEN_PIN,  LOW);
  digitalWrite(LED_ORANGE_PIN, LOW);
  digitalWrite(LED_RED_PIN,    LOW);
  digitalWrite(LED_BLUE_PIN,   LOW);
}

void updateStatusLEDs(float avgTemp, float avgHumid, bool serverOk) {
  setAllLEDsOff();

  // LED Bleue : connexion serveur NOK
  if (!serverOk || autonomousMode) {
    digitalWrite(LED_BLUE_PIN, HIGH);
  }

  // Pas de données valides → LED rouge
  if (avgTemp <= 0 || avgHumid <= 0) {
    digitalWrite(LED_RED_PIN, HIGH);
    return;
  }

  bool tempOk   = (avgTemp  >= TEMP_MIN     && avgTemp  <= TEMP_MAX);
  bool humidOk  = (avgHumid >= HUMIDITY_MIN && avgHumid <= HUMIDITY_MAX);
  bool tempHigh = (avgTemp  > TEMP_MAX);
  bool humidHigh= (avgHumid > HUMIDITY_MAX);
  bool tempLow  = (avgTemp  < TEMP_MIN);
  bool humidLow = (avgHumid < HUMIDITY_MIN);

  if (tempOk && humidOk) {
    digitalWrite(LED_GREEN_PIN, HIGH);
  } else if (tempHigh || humidHigh) {
    digitalWrite(LED_RED_PIN, HIGH);
  } else if (tempLow || humidLow) {
    digitalWrite(LED_ORANGE_PIN, HIGH);
  }
}

// ============== ENVOI DONNÉES SERVEUR ==============

void checkAutonomousMode() {
  if (serverFailCount >= MAX_SERVER_RETRIES && !autonomousMode) {
    autonomousMode = true;
    Serial.println("\n**************************************************");
    Serial.println("* ATTENTION: Mode autonome active!               *");
    Serial.printf( "* %d tentatives de connexion echouees            *\n", MAX_SERVER_RETRIES);
    Serial.println("* Le systeme fonctionne en mode secours          *");
    Serial.println("**************************************************\n");
    setLCDLog("Mode autonome");
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

  // ✅ v2 : WiFiClient explicite (requis par le core ESP32 récent)
  WiFiClient client;
  HTTPClient http;
  http.begin(client, buildServerUrl("/sensor/values"));
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", apiKey);

  int httpCode = http.POST(jsonPayload);

  if (httpCode > 0) {
    Serial.printf("POST /data - Code: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_CREATED) {
      Serial.println("Donnees envoyees avec succes");
      setLCDLog("Serveur OK");
      serverFailCount = 0;
      serverConnected = true;
    }
  } else {
    String errorMsg = "POST echec";
    Serial.printf("Erreur POST: %s\n", http.errorToString(httpCode).c_str());
    setLCDLog(errorMsg);
    serverFailCount++;
    serverConnected = false;
    checkAutonomousMode();
  }

  http.end();
  return httpCode > 0;
}

// ============== RECONNEXION PÉRIODIQUE ==============

void tryReconnectToServer() {
  static unsigned long lastReconnectAttempt = 0;
  const unsigned long RECONNECT_INTERVAL = 60000;  // 1 minute

  if (autonomousMode && (millis() - lastReconnectAttempt > RECONNECT_INTERVAL)) {
    lastReconnectAttempt = millis();
    Serial.println("Tentative de reconnexion au serveur...");

    if (WiFi.status() == WL_CONNECTED) {
      // ✅ v2 : WiFiClient explicite
      WiFiClient client;
      HTTPClient http;
      http.begin(client, buildServerUrl("/sensor/automation/status"));
      int httpCode = http.GET();

      if (httpCode == 200) {
        Serial.println("Serveur accessible! Sortie du mode autonome.");
        autonomousMode  = false;
        serverFailCount = 0;
        serverConnected = true;
      }
      http.end();
    }
  }
}

// ============== COMMANDES AUTOMATION ==============

bool getAutomationStatus() {
  if (WiFi.status() != WL_CONNECTED) return false;

  // ✅ v2 : WiFiClient explicite
  WiFiClient client;
  HTTPClient http;
  http.begin(client, buildServerUrl("/sensor/automation/status"));
  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("Status recu: " + response);

    // ✅ v7 : JsonDocument (plus de taille à spécifier)
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, response);

    if (!error) {
      bool fanStatus   = doc["fan"]        | false;
      bool humidStatus = doc["humidifier"] | false;

      digitalWrite(FAN_PIN,        fanStatus   ? HIGH : LOW);
      digitalWrite(HUMIDIFIER_PIN, humidStatus ? HIGH : LOW);
      fanOn        = fanStatus;
      humidifierOn = humidStatus;

      setLCDLog("Cmd automation");
      http.end();
      return true;
    } else {
      Serial.println("Erreur parsing JSON status");
      setLCDLog("JSON statut err");
    }
  } else {
    Serial.printf("GET /automation/status - Erreur: %d\n", httpCode);
  }

  http.end();
  return false;
}

bool getStepperCommand() {
  if (WiFi.status() != WL_CONNECTED) return false;

  // ✅ v2 : WiFiClient explicite
  WiFiClient client;
  HTTPClient http;
  http.begin(client, buildServerUrl("/sensor/automation/stepper"));
  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("Stepper recu: " + response);

    // ✅ v7 : JsonDocument
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, response);

    if (!error) {
      bool stepperStatus = doc["stepper"] | false;
      if (stepperStatus) {
        Serial.println("Rotation stepper activee");
        setLCDLog("Stepper ON");
        stepper.moveTo(stepper.currentPosition() + 200);
        stepper.setSpeed(100);
      }
      http.end();
      return true;
    } else {
      Serial.println("Erreur parsing JSON stepper");
      setLCDLog("JSON stepper err");
    }
  } else {
    Serial.printf("GET /automation/stepper - Erreur: %d\n", httpCode);
  }

  http.end();
  return false;
}

// ============== LOGIQUE DE SECOURS (MODE AUTONOME) ==============

void applyBackupLogic(float avgTemp, float avgHumid) {
  Serial.println("Mode autonome - Logique de secours");

  // Fan : s'active si température trop basse (distribue la chaleur)
  if (avgTemp > 0 && avgTemp < TEMP_MIN) {
    digitalWrite(FAN_PIN, HIGH);
    fanOn = true;
    Serial.println("Fan ON - Temperature basse, distribution chaleur");
  } else {
    digitalWrite(FAN_PIN, LOW);
    fanOn = false;
  }

  // Humidificateur : s'active si humidité trop basse
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
      buttonPressed   = true;

      Serial.println("Bouton presse - Lancement rotation stepper");
      setLCDLog("Stepper manuel");
      stepper.moveTo(stepper.currentPosition() + 200);
      stepper.setSpeed(100);
    }
  }
}

// ============== AFFICHAGE ==============

void printStatus(SensorData sensors[], int count,
                 float avgTemp, float avgHumid, int failedCount) {
  Serial.println("\n========== STATUS ==========");
  for (int i = 0; i < count; i++) {
    Serial.printf("Capteur %d: %.1f°C, %.1f%% %s\n",
                  i + 1,
                  sensors[i].temperature,
                  sensors[i].humidity,
                  sensors[i].valid ? "" : "[ERREUR]");
  }
  Serial.printf("Moyenne: %.1f°C, %.1f%%\n", avgTemp, avgHumid);
  Serial.printf("Ventilateur: %s\n",     fanOn        ? "ON" : "OFF");
  Serial.printf("Humidificateur: %s\n",  humidifierOn ? "ON" : "OFF");
  Serial.printf("Capteurs defaillants: %d\n", failedCount);
  Serial.println("============================\n");
}

void displayStatusOnLCD(float avgTemp, float avgHumid) {
  lcd.clear();

  // Ligne 1 : T:37.5C H:45%  (+ "A" si mode autonome)
  String line1 = "T:" + String(avgTemp, 1) + "C H:" + String((int)avgHumid) + "%";
  if (autonomousMode) {
    if (line1.length() < LCD_COLS - 2) {
      line1 += " A";
    } else {
      line1 = line1.substring(0, LCD_COLS - 2) + " A";
    }
  }
  printLCDLine(0, line1);

  // Ligne 2 : message de log courant
  printLCDLine(1, getCurrentLCDLog());
}

// ============== SETUP ==============

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n=== ESP32 Sensor Controller v2 ===\n");

  connectWiFi();

  dht_1.begin();
  dht_2.begin();
  dht_3.begin();
  dht_4.begin();

  stepper.setMaxSpeed(300);
  stepper.setAcceleration(1000);

  pinMode(FAN_PIN,        OUTPUT);
  pinMode(HUMIDIFIER_PIN, OUTPUT);
  digitalWrite(FAN_PIN,        LOW);
  digitalWrite(HUMIDIFIER_PIN, LOW);

  initLEDs();
  digitalWrite(LED_BLUE_PIN, HIGH);  // LED bleue pendant l'init

  pinMode(BUTTON_STEPPER_PIN, INPUT_PULLUP);
  pinMode(BUTTON_LCD_SCROLL_PIN, INPUT_PULLUP);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("ESP32 Sensor v2");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  setLCDLog("Initializing...");

  Serial.println("Initialisation terminee\n");
}

// ============== LOOP ==============

void loop() {
  static unsigned long lastSendTime = 0;
  unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED && now - lastSendTime >= SEND_INTERVAL) {
    connectWiFi();
  }

  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;

    // Lecture des 4 capteurs
    SensorData sensors[4];
    sensors[0] = readSensor(dht_1, 1);
    sensors[1] = readSensor(dht_2, 2);
    sensors[2] = readSensor(dht_3, 3);
    sensors[3] = readSensor(dht_4, 4);

  // Calcul des moyennes
  calculateAverages(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);

  // Construction du payload JSON
  // ✅ v7 : JsonDocument (auto-alloué depuis le heap, pas de taille fixe)
  JsonDocument payload;

  for (int i = 0; i < 4; i++) {
    String sensorKey = "sensor_" + String(i + 1);
    payload[sensorKey]["temperature"] = sensors[i].temperature;
    payload[sensorKey]["humidity"]    = sensors[i].humidity;
    payload[sensorKey]["valid"]       = sensors[i].valid;
  }

  payload["average_temperature"] = avgTemperature;
  payload["average_humidity"]    = avgHumidity;
  payload["fan_status"]          = fanOn        ? "ON" : "OFF";
  payload["humidifier_status"]   = humidifierOn ? "ON" : "OFF";
  payload["numFailedSensors"]    = numFailedSensors;

  String jsonPayload;
  serializeJson(payload, jsonPayload);

  // Envoi au serveur
  serverSuccess = false;
  if (!autonomousMode) {
    serverSuccess = sendDataToServer(jsonPayload);
  }

  // Commandes d'automation
  if (autonomousMode) {
    applyBackupLogic(avgTemperature, avgHumidity);
    tryReconnectToServer();
  } else if (!getAutomationStatus()) {
    applyBackupLogic(avgTemperature, avgHumidity);
  }

  // Commande stepper serveur (seulement si connecté)
  if (!autonomousMode) {
    getStepperCommand();
  }

  // Logs Serial
  printStatus(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);
  if (autonomousMode) {
    Serial.println(">>> MODE AUTONOME ACTIF <<<");
  }
  }

  // Bouton stepper manuel
  checkStepperButton();
  // Bouton de defilement manuel des logs LCD
  checkLCDScrollButton();

  // Defilement auto des logs toutes les 3 secondes
  updateLCDScroll(now);

  // LEDs de statut
  updateStatusLEDs(avgTemperature, avgHumidity, serverSuccess || serverConnected);

  // Affichage LCD
  displayStatusOnLCD(avgTemperature, avgHumidity);

  // Stepper
  if (stepper.isRunning()) {
    stepper.run();
  }

  delay(100);
}