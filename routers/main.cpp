#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>
#include "DHT.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

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
#define DHT_1_PIN_DATA      33
#define DHT_2_PIN_DATA      34
#define DHT_3_PIN_DATA      35
#define DHT_4_PIN_DATA      36

#define STEPPER_PIN_DIR     12
#define STEPPER_PIN_STEP    13
#define STEPPER_ENABLE_PIN  32    // Enable pin pour couper le courant

// ⚠️ Ajuste ces deux états selon la réponse de ton TB6600 :
// Si le moteur bloque au repos et devient libre en mouvement, inverse LOW et HIGH.
#define STEPPER_ENABLE_ACTIVE_STATE   LOW
#define STEPPER_ENABLE_DISABLE_STATE  HIGH

#define FAN_PIN             14
#define HUMIDIFIER_PIN      15

#define LED_GREEN_PIN       16    // Temp + humidité dans les seuils
#define LED_ORANGE_PIN      17    // Temp ou humidité en dessous du min
#define LED_RED_PIN         18    // Temp ou humidité au dessus du max
#define LED_BLUE_PIN        19    // Serveur inaccessible / mode autonome

#define BUTTON_STEPPER_PIN      23
#define BUTTON_LCD_SCROLL_PIN   27

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
const char* HOSTNAME   = "ESP32-Sensor";

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
const unsigned long SEND_INTERVAL             = 5000UL;   // ms entre chaque cycle capteurs
const unsigned long LCD_SCROLL_INTERVAL       = 3000UL;   // ms entre chaque défilement auto
const unsigned long RECONNECT_INTERVAL        = 60000UL;  // ms entre tentatives de reconnexion serveur
const unsigned long WIFI_TIMEOUT              = 15000UL;  // ms max pour connexion WiFi
const unsigned long AUTOMATION_POLL_INTERVAL  = 3000UL;   // ms entre chaque poll automation/stepper
const unsigned long HTTP_TIMEOUT              = 3000UL;   // ms timeout par requête HTTP

const int LCD_LOG_BUFFER_SIZE = 6;
const int MAX_SERVER_RETRIES  = 10;

// ============================================================
//  CONFIGURATION STEPPER
// ============================================================
#if STEPPER_DRIVER_TYPE == STEPPER_DRIVER_TYPE_TB6600
  #define STEPPER_MAX_SPEED          1000
  #define STEPPER_ACCELERATION       1000
  #define STEPPER_STEPS_PER_ROTATION  800  // Remarque : 800 si DIP switchs TB6600 réglés en 1/4 step
  #define STEPPER_SPEED               500
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

// AccelStepper::DRIVER → (STEP, DIR)
// IMPORTANT : cet objet n'est piloté QUE depuis le core 1 (setup/loop).
// AccelStepper n'est pas thread-safe, il ne doit jamais être touché
// depuis la tâche réseau (core 0).
AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_STEP, STEPPER_PIN_DIR);
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// ============================================================
//  STRUCTURES DE DONNÉES & VARIABLES GLOBALES
// ============================================================
struct SensorData {
  float temperature = 0.0f;
  float humidity    = 0.0f;
  bool  valid       = false;
};

// ------------------------------------------------------------
//  ÉTAT PARTAGÉ ENTRE LES DEUX TÂCHES (core 0 = réseau, core 1 = loop)
//  Toute lecture/écriture doit être protégée par stateMutex.
// ------------------------------------------------------------
struct SharedState {
  // --- Écrit par le core 1 (loop), lu par le core 0 (réseau) ---
  bool     sensorDataReady = false;   // nouvelle trame capteurs prête à être postée
  String   pendingPayload;            // JSON à envoyer

  // --- Écrit par le core 0 (réseau), lu par le core 1 (loop) ---
  bool serverConnected   = false;
  bool autonomousMode    = false;
  int  serverFailCount   = 0;

  bool fanCmdFromServer      = false; // dernier ordre reçu du serveur
  bool humidCmdFromServer    = false;
  bool automationCmdPending  = false; // un ordre fan/humid vient d'arriver

  bool stepperRequestPending = false; // le serveur demande une rotation
};

SharedState shared;
SemaphoreHandle_t stateMutex;
TaskHandle_t networkTaskHandle;

bool  fanOn           = false;
bool  humidifierOn    = false;
bool  autonomousMode  = false;   // copie locale (core 1) de shared.autonomousMode
bool  serverConnected = false;   // copie locale (core 1) de shared.serverConnected

float avgTemperature  = 0.0f;
float avgHumidity     = 0.0f;
int   numFailedSensors = 0;
bool  stepperEnabled   = false;

// Boutons
unsigned long lastButtonPress       = 0;
unsigned long lastScrollButtonPress = 0;

// LCD log ring buffer
char lcdLogBuffer[LCD_LOG_BUFFER_SIZE][LCD_COLS + 1];
int  lcdLogCount = 0;
int  lcdLogIndex = 0;
int  lcdLogStart = 0;
unsigned long lastLogScroll = 0;

// ============================================================
//  FONCTIONS GESTION STEPPER / POWER  (core 1 uniquement)
// ============================================================

void enableStepper() {
  if (!stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_STATE);
    delayMicroseconds(100);
    stepperEnabled = true;
  }
}

void disableStepper() {
  if (stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_DISABLE_STATE);
    stepperEnabled = false;
  }
}

// Lance une rotation si le moteur est actuellement à l'arrêt.
// Centralise la règle "pas de nouvelle rotation par-dessus une en cours"
// pour le bouton ET pour la commande serveur.
void startStepperRotation(const char* origin) {
  if (stepper.distanceToGo() != 0) {
    Serial.printf("Rotation ignoree (%s) — moteur deja en mouvement\n", origin);
    return;
  }
  Serial.printf("Rotation stepper activee (%s)\n", origin);
  stepper.setMaxSpeed(STEPPER_SPEED);
  enableStepper();
  stepper.move(STEPPER_ROTATION_STEPS);
}

// ============================================================
//  UTILITAIRES LCD LOG & DISPLAY  (core 1 uniquement)
// ============================================================

void printLCDLine(int row, const char* line) {
  lcd.setCursor(0, row);
  lcd.print(line);
  for (int i = strlen(line); i < LCD_COLS; i++) {
    lcd.print(' ');
  }
}

void pushLCDLog(const char* msg) {
  char text[LCD_COLS + 1];
  snprintf(text, sizeof(text), "%s", msg);

  int lastIndex = (lcdLogStart + lcdLogCount - 1 + LCD_LOG_BUFFER_SIZE) % LCD_LOG_BUFFER_SIZE;
  if (lcdLogCount > 0 && strcmp(text, lcdLogBuffer[lastIndex]) == 0) {
    return;
  }

  if (lcdLogCount < LCD_LOG_BUFFER_SIZE) {
    int idx = (lcdLogStart + lcdLogCount) % LCD_LOG_BUFFER_SIZE;
    strcpy(lcdLogBuffer[idx], text);
    lcdLogCount++;
  } else {
    lcdLogStart = (lcdLogStart + 1) % LCD_LOG_BUFFER_SIZE;
    int idx = (lcdLogStart + lcdLogCount - 1) % LCD_LOG_BUFFER_SIZE;
    strcpy(lcdLogBuffer[idx], text);
  }
}

const char* getCurrentLCDLog() {
  if (lcdLogCount == 0) {
    return "";
  }
  if (lcdLogIndex >= lcdLogCount) {
    lcdLogIndex = 0;
  }
  int idx = (lcdLogStart + lcdLogIndex) % LCD_LOG_BUFFER_SIZE;
  return lcdLogBuffer[idx];
}

void advanceLCDLog() {
  if (lcdLogCount > 1) {
    lcdLogIndex = (lcdLogIndex + 1) % lcdLogCount;
  }
}

void updateLCDScroll(unsigned long now) {
  if (now - lastLogScroll >= LCD_SCROLL_INTERVAL) {
    lastLogScroll = now;
    advanceLCDLog();
  }
}

void displayStatusOnLCD(float avgTemp, float avgHumid) {
  char line0[LCD_COLS + 1];
  bool stepperMoving = stepper.distanceToGo() != 0;
  const char* wifiState = WiFi.status() == WL_CONNECTED ? "OK" : "--";
  if (autonomousMode) {
    snprintf(line0, sizeof(line0), "AUTO W:%s S:%s",
             wifiState, stepperMoving ? "ON" : "OFF");
  } else {
    snprintf(line0, sizeof(line0), "T:%.0f H:%d W:%s",
             avgTemp, (int)avgHumid, wifiState);
  }
  printLCDLine(0, line0);
  printLCDLine(1, getCurrentLCDLog());
}

// Note : pushLCDLog() n'est PAS protégé par mutex. Il est appelé depuis les
// deux tâches (loop ET networkTask). Comme le ring buffer LCD n'est utile
// qu'à l'affichage (pas de conséquence fonctionnelle en cas de log perdu/
// dupliqué lors d'une rare collision), on accepte ce compromis plutôt que
// d'alourdir chaque appel réseau avec un lock dédié. Si tu veux une garantie
// stricte, entoure le corps de pushLCDLog() avec stateMutex comme pour
// SharedState.

// ============================================================
//  WIFI & SERVEUR  — tout ce bloc tourne désormais sur networkTask (core 0)
// ============================================================

void buildServerUrl(const char* endpoint, char* output, size_t size) {
  snprintf(output, size, "http://%s:%d%s", serverIP, serverPort, endpoint);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  Serial.println("Connexion WiFi...");
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnecte — IP: " + WiFi.localIP().toString());
    pushLCDLog("WiFi connecte");
  } else {
    Serial.printf("\nEchec WiFi (statut=%d)\n", WiFi.status());
    pushLCDLog("WiFi echec");
  }
}

// Doit être appelée avec stateMutex déjà pris par l'appelant.
void checkAutonomousMode_locked() {
  if (!shared.autonomousMode && shared.serverFailCount >= MAX_SERVER_RETRIES) {
    shared.autonomousMode = true;
    Serial.println("\n*** MODE AUTONOME ACTIVE ***");
    Serial.printf("  %d echecs consecutifs\n", MAX_SERVER_RETRIES);
    pushLCDLog("Mode autonome");
  }
}

bool sendDataToServer(const String& jsonPayload) {
  if (WiFi.status() != WL_CONNECTED) {
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.serverFailCount++;
    checkAutonomousMode_locked();
    xSemaphoreGive(stateMutex);
    return false;
  }

  WiFiClient wifiClient;
  HTTPClient http;
  char url[128];
  buildServerUrl("/sensor/values", url, sizeof(url));
  http.setTimeout(HTTP_TIMEOUT);
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", apiKey);

  int code = http.POST(jsonPayload);
  bool success = false;

  xSemaphoreTake(stateMutex, portMAX_DELAY);
  if (code > 0) {
    Serial.printf("POST /sensor/values -> %d\n", code);
    if (code == HTTP_CODE_OK || code == HTTP_CODE_CREATED) {
      pushLCDLog("Serveur OK");
      shared.serverFailCount = 0;
      shared.serverConnected = true;
      success = true;
    } else {
      Serial.printf("Reponse inattendue: %d\n", code);
      char msg[LCD_COLS + 1];
      snprintf(msg, sizeof(msg), "Serveur err %d", code);
      pushLCDLog(msg);
      shared.serverFailCount++;
      shared.serverConnected = false;
      checkAutonomousMode_locked();
    }
  } else {
    Serial.printf("POST echec: %s\n", http.errorToString(code).c_str());
    pushLCDLog("POST echec");
    shared.serverFailCount++;
    shared.serverConnected = false;
    checkAutonomousMode_locked();
  }
  xSemaphoreGive(stateMutex);

  http.end();
  return success;
}

void tryReconnectToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }

  Serial.println("Tentative de reconnexion au serveur...");
  WiFiClient wifiClient;
  HTTPClient http;
  char url[128];
  buildServerUrl("/sensor/automation/status", url, sizeof(url));
  http.setTimeout(HTTP_TIMEOUT);
  http.begin(wifiClient, url);
  http.addHeader("x-api-key", apiKey);
  int code = http.GET();
  http.end();

  if (code == HTTP_CODE_OK) {
    Serial.println("Serveur accessible — sortie du mode autonome");
    Serial.println("MODE NORMAL");
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.autonomousMode  = false;
    shared.serverFailCount = 0;
    shared.serverConnected = true;
    xSemaphoreGive(stateMutex);
    pushLCDLog("Serveur retrouve");
    pushLCDLog("Mode normal");
  }
}

bool getAutomationStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  WiFiClient wifiClient;
  HTTPClient http;
  char url[128];
  buildServerUrl("/sensor/automation/status", url, sizeof(url));
  http.setTimeout(HTTP_TIMEOUT);
  http.begin(wifiClient, url);
  http.addHeader("x-api-key", apiKey);
  int code = http.GET();

  if (code == HTTP_CODE_OK) {
    String response = http.getString();
    JsonDocument doc; // ArduinoJson v7
    DeserializationError error = deserializeJson(doc, response);
    if (!error) {
      bool fanCmd   = doc["fan"]        | false;
      bool humidCmd = doc["humidifier"] | false;

      xSemaphoreTake(stateMutex, portMAX_DELAY);
      shared.fanCmdFromServer     = fanCmd;
      shared.humidCmdFromServer   = humidCmd;
      shared.automationCmdPending = true;
      shared.serverConnected      = true;
      xSemaphoreGive(stateMutex);

      Serial.println("Server OK");
      pushLCDLog("Server OK");
      pushLCDLog("Cmd automation");
      http.end();
      return true;
    }
    Serial.print("JSON statut erreur: ");
    Serial.println(error.c_str());
    pushLCDLog("JSON statut err");
  } else {
    Serial.printf("GET /automation/status -> %d\n", code);
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.serverConnected = false;
    xSemaphoreGive(stateMutex);
    pushLCDLog("Server NOK");
  }

  http.end();
  return false;
}

bool getStepperCommand() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  WiFiClient wifiClient;
  HTTPClient http;
  char url[128];
  buildServerUrl("/sensor/automation/stepper", url, sizeof(url));
  http.setTimeout(HTTP_TIMEOUT);
  http.begin(wifiClient, url);
  http.addHeader("x-api-key", apiKey);
  int code = http.GET();

  if (code == HTTP_CODE_OK) {
    String response = http.getString();
    JsonDocument doc; // ArduinoJson v7
    DeserializationError error = deserializeJson(doc, response);
    if (!error) {
      if (doc["stepper"] | false) {
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        shared.stepperRequestPending = true;
        xSemaphoreGive(stateMutex);
        pushLCDLog("Stepper ON (srv)");
      }
      http.end();
      return true;
    }
    Serial.print("JSON stepper erreur: ");
    Serial.println(error.c_str());
    pushLCDLog("JSON stepper err");
  } else {
    Serial.printf("GET /automation/stepper -> %d\n", code);
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.serverConnected = false;
    xSemaphoreGive(stateMutex);
    pushLCDLog("Server NOK");
  }

  http.end();
  return false;
}

// ============================================================
//  TÂCHE RÉSEAU — tourne sur le core 0, en boucle indépendante du loop()
// ============================================================
void networkTaskFunction(void* pvParameters) {
  unsigned long lastAutomationPoll   = 0;
  unsigned long lastReconnectAttempt = 0;

  connectWiFi();

  for (;;) {
    unsigned long now = millis();

    if (WiFi.status() != WL_CONNECTED) {
      connectWiFi();
    }

    bool localAutonomous;
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    localAutonomous = shared.autonomousMode;
    xSemaphoreGive(stateMutex);

    if (localAutonomous) {
      // En mode autonome : on ne tente qu'une reconnexion périodique,
      // on n'envoie plus rien au serveur.
      if (now - lastReconnectAttempt >= RECONNECT_INTERVAL) {
        lastReconnectAttempt = now;
        tryReconnectToServer();
      }
    } else {
      // 1) Poste les données capteurs si une nouvelle trame est prête
      bool   hasData = false;
      String payloadCopy;
      xSemaphoreTake(stateMutex, portMAX_DELAY);
      if (shared.sensorDataReady) {
        payloadCopy = shared.pendingPayload;
        shared.sensorDataReady = false;
        hasData = true;
      }
      xSemaphoreGive(stateMutex);

      if (hasData) {
        sendDataToServer(payloadCopy);
      }

      // 2) Interroge périodiquement l'automation (fan/humid) et le stepper
      if (now - lastAutomationPoll >= AUTOMATION_POLL_INTERVAL) {
        lastAutomationPoll = now;
        getAutomationStatus();
        getStepperCommand();
      }
    }

    // Cède la main — évite de saturer le CPU / le watchdog du core 0
    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

// ============================================================
//  LOGIQUE DE SECOURS (core 1)
// ============================================================

void applyBackupLogic(float avgTemp, float avgHumid) {
  bool fan = (avgTemp > 0.0f && avgTemp < TEMP_MIN);
  digitalWrite(FAN_PIN, fan ? HIGH : LOW);
  fanOn = fan;
  if (fan) Serial.println("[AUTO] Fan ON — temp basse");

  bool humid = (avgHumid > 0.0f && avgHumid < HUMIDITY_MIN);
  digitalWrite(HUMIDIFIER_PIN, humid ? HIGH : LOW);
  humidifierOn = humid;
  if (humid) Serial.println("[AUTO] Humidificateur ON — humidite basse");
}

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
  Serial.printf("Capteur %d: T=%.1f°C H=%.1f%% valid=%d\n",
                num,
                data.temperature,
                data.humidity,
                data.valid ? 1 : 0);
  return data;
}

void calculateAverages(SensorData sensors[], int count,
                       float& avgTemp, float& avgHumid, int& failedCount) {
  float tTotal = 0.0f;
  float hTotal = 0.0f;
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

void initLEDs() {
  const int pins[] = { LED_GREEN_PIN, LED_ORANGE_PIN, LED_RED_PIN, LED_BLUE_PIN };
  for (int p : pins) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
  }
}

void setAllLEDsOff() {
  digitalWrite(LED_GREEN_PIN,  LOW);
  digitalWrite(LED_ORANGE_PIN, LOW);
  digitalWrite(LED_RED_PIN,    LOW);
  digitalWrite(LED_BLUE_PIN,   LOW);
}

void updateStatusLEDs(float avgTemp, float avgHumid, bool serverOk) {
  setAllLEDsOff();

  if (!serverOk || autonomousMode) {
    digitalWrite(LED_BLUE_PIN, HIGH);
  }
  if (avgTemp <= 0.0f || avgHumid <= 0.0f) {
    digitalWrite(LED_RED_PIN, HIGH);
    return;
  }

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

void checkStepperButton() {
  const unsigned long DEBOUNCE = 200;
  if (digitalRead(BUTTON_STEPPER_PIN) == LOW && millis() - lastButtonPress > DEBOUNCE) {
    lastButtonPress = millis();
    pushLCDLog("Stepper manuel");
    startStepperRotation("bouton");
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

// Récupère les infos écrites par networkTask et les applique côté core 1
// (digitalWrite fan/humid, déclenchement stepper). Ainsi, AccelStepper et
// les actionneurs restent pilotés depuis un seul et même core.
void applyNetworkOutputs() {
  bool localAutonomous;
  bool localServerConnected;
  bool automationPending;
  bool fanCmd = false, humidCmd = false;
  bool stepperPending;

  xSemaphoreTake(stateMutex, portMAX_DELAY);
  localAutonomous      = shared.autonomousMode;
  localServerConnected = shared.serverConnected;
  automationPending     = shared.automationCmdPending;
  if (automationPending) {
    fanCmd   = shared.fanCmdFromServer;
    humidCmd = shared.humidCmdFromServer;
    shared.automationCmdPending = false;
  }
  stepperPending = shared.stepperRequestPending;
  if (stepperPending) {
    shared.stepperRequestPending = false;
  }
  xSemaphoreGive(stateMutex);

  autonomousMode  = localAutonomous;
  serverConnected = localServerConnected;

  if (!autonomousMode && automationPending) {
    digitalWrite(FAN_PIN,        fanCmd   ? HIGH : LOW);
    digitalWrite(HUMIDIFIER_PIN, humidCmd ? HIGH : LOW);
    fanOn        = fanCmd;
    humidifierOn = humidCmd;
  }

  if (stepperPending) {
    startStepperRotation("serveur");
  }
}

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
  Serial.printf("  Seuils    : T [%.2f-%.2f]  H [%.2f-%.2f]\n",
                TEMP_MIN, TEMP_MAX, HUMIDITY_MIN, HUMIDITY_MAX);
  Serial.printf("  Fan: %s  |  Humidif: %s  |  Defauts: %d\n",
                fanOn ? "ON" : "OFF", humidifierOn ? "ON" : "OFF", failed);
  Serial.printf("  Stepper: %s (%ld)\n",
                stepper.distanceToGo() != 0 ? "MOVING" : "IDLE",
                stepper.distanceToGo());
  Serial.printf("  Server: %s  WiFi: %s\n",
                serverConnected ? "OK" : "NOK",
                WiFi.status() == WL_CONNECTED ? "OK" : "NOK");
  if (autonomousMode) {
    Serial.println("  >>> MODE AUTONOME ACTIF <<<");
  }
  Serial.println("============================\n");
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n=== ESP32 Sensor Controller v4 (stepper non-bloquant) ===");
  Serial.printf("Driver : %s\n", DRIVER_NAME);
  Serial.printf("Vitesse: %d sps  |  Accel: %d sps^2\n", STEPPER_MAX_SPEED, STEPPER_ACCELERATION);

  pinMode(STEPPER_ENABLE_PIN, OUTPUT);
  disableStepper();

  lcd.init();
  lcd.backlight();
  printLCDLine(0, "ESP32 Sensor v4");
  printLCDLine(1, "Init...");
  pushLCDLog("Initializing...");

  dht_1.begin();
  dht_2.begin();
  dht_3.begin();
  dht_4.begin();

  stepper.setMaxSpeed(STEPPER_MAX_SPEED);
  stepper.setAcceleration(STEPPER_ACCELERATION);

  pinMode(FAN_PIN,        OUTPUT);
  digitalWrite(FAN_PIN,        LOW);
  pinMode(HUMIDIFIER_PIN, OUTPUT);
  digitalWrite(HUMIDIFIER_PIN, LOW);

  initLEDs();
  digitalWrite(LED_BLUE_PIN, HIGH);

  pinMode(BUTTON_STEPPER_PIN,    INPUT_PULLUP);
  pinMode(BUTTON_LCD_SCROLL_PIN, INPUT_PULLUP);

  // --- Mutex + tâche réseau sur le core 0 ---
  stateMutex = xSemaphoreCreateMutex();

  xTaskCreatePinnedToCore(
    networkTaskFunction,   // fonction de la tâche
    "NetworkTask",         // nom (debug)
    8192,                  // taille de pile (les buffers HTTP/JSON sont gourmands)
    NULL,                  // paramètre
    1,                     // priorité
    &networkTaskHandle,    // handle
    0                       // épinglée sur le core 0 (Arduino loop tourne sur le core 1)
  );

  Serial.println("Initialisation terminee. Tache reseau demarree sur le core 0.\n");
}

void loop() {
  static unsigned long lastSendTime     = 0;
  static unsigned long lastSlowTaskTime = 0;
  unsigned long now = millis();

  // Récupère et applique ce que la tâche réseau a produit depuis le dernier tour
  applyNetworkOutputs();

  // Le stepper est géré à CHAQUE itération de loop(), jamais bloqué par le réseau
  if (stepper.distanceToGo() != 0) {
    enableStepper();
    stepper.run();
  } else {
    disableStepper();
  }

  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;
    Serial.println("Lecture des capteurs...");

    SensorData sensors[4];
    sensors[0] = readSensor(dht_1, 1);
    sensors[1] = readSensor(dht_2, 2);
    sensors[2] = readSensor(dht_3, 3);
    sensors[3] = readSensor(dht_4, 4);

    calculateAverages(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);

    // Dynamic JsonDocument (ArduinoJson v7)
    JsonDocument payload;
    for (int i = 0; i < 4; i++) {
      char key[10];
      snprintf(key, sizeof(key), "sensor_%d", i + 1);
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

    // On ne fait plus l'appel HTTP ici : on dépose juste la trame pour
    // que networkTask (core 0) la poste dès qu'elle est disponible.
    if (!autonomousMode) {
      xSemaphoreTake(stateMutex, portMAX_DELAY);
      shared.pendingPayload   = jsonPayload;
      shared.sensorDataReady  = true;
      xSemaphoreGive(stateMutex);
    }

    // Logique de secours : active si on est autonome, ou si la dernière
    // commande automation connue n'a pas pu être obtenue du serveur.
    if (autonomousMode || !serverConnected) {
      applyBackupLogic(avgTemperature, avgHumidity);
    }

    printStatus(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);
  }

  if (now - lastSlowTaskTime >= 100) {
    lastSlowTaskTime = now;
    checkStepperButton();
    checkLCDScrollButton();
    updateLCDScroll(now);
    updateStatusLEDs(avgTemperature, avgHumidity, serverConnected);
    displayStatusOnLCD(avgTemperature, avgHumidity);
  }

  // Petite respiration pour laisser le scheduler FreeRTOS souffler
  // (utile même si loop() ne bloque plus sur le réseau)
  delay(1);
}