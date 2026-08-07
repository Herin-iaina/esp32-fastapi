#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>
#include "DHT.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <esp_task_wdt.h>
#include "soc/rtc_cntl_reg.h"
#include "soc/soc.h"

// ============================================================
//  ⚠️ DIAGNOSTIC UNIQUEMENT — À RETIRER APRÈS TEST ⚠️
// ============================================================
// Désactive le détecteur de brownout matériel. Ça ne corrige RIEN — ça
// masque juste le symptôme (le reset), pour vérifier si le blocage vient
// bien d'un sous-voltage transitoire. Si avec ça le boot va au bout et que
// tu observes à la place des comportements bizarres (WiFi qui échoue,
// capteurs qui donnent n'importe quoi, redémarrages aléatoires ailleurs),
// ça confirme un vrai problème d'alimentation à régler avant d'aller plus
// loin. Ne JAMAIS garder ça sur un système en usage réel : sans BOD, un
// sous-voltage peut corrompre la flash/l'exécution au lieu de proprement
// redémarrer.
#define DEBUG_DISABLE_BOD 0

// ⚠️ MODE TEST — met à 1 pour tester le stepper (bouton) sans que la lecture
// DHT (init + lectures répétées) n'interfère ou ne pollue les logs. Le WiFi,
// le LCD et les LEDs restent actifs normalement. Remettre à 0 pour l'usage
// réel de l'incubateur.
#define TEST_MODE_SKIP_SENSORS 0

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
// GPIO 34/35/36 sont des broches ENTRÉE SEULE sur l'ESP32 (pas de driver de
// sortie physique) : le protocole DHT a besoin d'envoyer un signal de
// démarrage (ligne tirée au bas) avant de lire la réponse, donc ces
// broches ne peuvent PAS fonctionner avec un DHT, pull-up externe ou pas.
// Rebranche physiquement les capteurs 2/3/4 sur ces broches à la place :
#define DHT_2_PIN_DATA      25
#define DHT_3_PIN_DATA      26
#define DHT_4_PIN_DATA      4

#define STEPPER_PIN_DIR     12
#define STEPPER_PIN_STEP    13
#define STEPPER_ENABLE_PIN  32

// Confirmé par test direct (sketch minimal PUL/DIR/ENA) : ce module TB6600
// a un ENA actif HAUT (HIGH = bobines sous tension, LOW = driver coupé) —
// inverse de la convention ENA+/ENA- standard. Ne pas réinverser sans
// retester physiquement.
#define STEPPER_ENABLE_ACTIVE_STATE   HIGH
#define STEPPER_ENABLE_DISABLE_STATE  LOW

#define FAN_PIN             14
#define HUMIDIFIER_PIN      15

// Le relais est activé par un niveau bas : GPIO LOW signifie relais enclenché.
#define RELAY_ACTIVE_STATE   LOW
#define RELAY_INACTIVE_STATE HIGH

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
const char* serverIP   = "192.168.1.155";
const int   serverPort = 8000;
const char* apiKey     = "Votre_Cle_API";
const char* HOSTNAME   = "ESP32-Sensor";

// ============================================================
//  SEUILS TEMPÉRATURE / HUMIDITÉ & HYSTÉRÉSIS
// ============================================================
const float TEMP_TARGET       = 37.7f;
const float HUMIDITY_TARGET   = 45.0f;
const float TOLERANCE_PERCENT = 1.5f;

const float TEMP_MIN     = TEMP_TARGET     * (1.0f - TOLERANCE_PERCENT / 100.0f);
const float TEMP_MAX     = TEMP_TARGET     * (1.0f + TOLERANCE_PERCENT / 100.0f);
const float HUMIDITY_MIN = HUMIDITY_TARGET * (1.0f - TOLERANCE_PERCENT / 100.0f);
const float HUMIDITY_MAX = HUMIDITY_TARGET * (1.0f + TOLERANCE_PERCENT / 100.0f);

// Plages d'hystérésis pour la sécurité des relais (mode autonome)
const float TEMP_HYSTERESIS     = 0.3f;
const float HUMIDITY_HYSTERESIS = 0.5f;

// ============================================================
//  TIMING & BUFFERS
// ============================================================
const unsigned long SEND_INTERVAL             = 5000UL;   // ms entre chaque cycle capteurs
const unsigned long LCD_SCROLL_INTERVAL       = 3000UL;   // ms entre chaque défilement auto
const unsigned long RECONNECT_INTERVAL        = 60000UL;  // ms entre tentatives de reconnexion serveur
const unsigned long WIFI_TIMEOUT              = 15000UL;  // ms max pour connexion WiFi
const unsigned long AUTOMATION_POLL_INTERVAL  = 3000UL;   // ms entre chaque poll automation/stepper
const unsigned long HTTP_TIMEOUT              = 1500UL;   // ms timeout par requête HTTP

const int LCD_LOG_BUFFER_SIZE = 6;
const int MAX_SERVER_RETRIES  = 10;

// FIX 1 : WDT à 25s (> WIFI_TIMEOUT de 15s) pour marge de sécurité
const uint32_t WDT_TIMEOUT_SEC = 25;                       

// ============================================================
//  CONFIGURATION STEPPER
// ============================================================
#if STEPPER_DRIVER_TYPE == STEPPER_DRIVER_TYPE_TB6600
  #define STEPPER_MAX_SPEED          1000
  #define STEPPER_ACCELERATION       1000
  #define STEPPER_STEPS_PER_ROTATION  800
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

struct SharedState {
  // Écrit par core 1, lu par core 0
  bool     sensorDataReady = false;
  String   pendingPayload;

  // Écrit par core 0, lu par core 1
  bool wifiConnected     = false;
  bool serverConnected   = false;
  bool autonomousMode    = false;
  int  serverFailCount   = 0;

  bool fanCmdFromServer      = false;
  bool humidCmdFromServer    = false;
  bool automationCmdPending  = false;

  bool stepperRequestPending = false;
};

SharedState shared;
SemaphoreHandle_t stateMutex;
SemaphoreHandle_t lcdLogMutex;
TaskHandle_t networkTaskHandle;

bool  fanOn           = false;
bool  humidifierOn    = false;
bool  autonomousMode  = false;   // Copie locale Core 1
bool  serverConnected = false;   // Copie locale Core 1
bool  wifiConnected   = false;   // Copie locale Core 1

float avgTemperature  = 0.0f;
float avgHumidity     = 0.0f;
int   numFailedSensors = 0;
bool  stepperEnabled   = false;

// Anti-rebond non-bloquant
unsigned long lastButtonPress       = 0;
unsigned long lastScrollButtonPress = 0;
bool stepperBtnPendingCheck         = false;
bool lcdBtnPendingCheck             = false;
unsigned long stepperBtnTriggerTime = 0;
unsigned long lcdBtnTriggerTime     = 0;

// LCD log ring buffer
char lcdLogBuffer[LCD_LOG_BUFFER_SIZE][LCD_COLS + 1];
int  lcdLogCount = 0;
int  lcdLogIndex = 0;
int  lcdLogStart = 0;
unsigned long lastLogScroll = 0;

// Mémorise le dernier index de cycle serveur ayant déclenché une rotation
// stepper (Core 0 uniquement — networkTaskFunction/getStepperCommand). Voir
// getStepperCommand() : sert à éviter de redéclencher une rotation à
// chaque poll (~3s) tant que le serveur renvoie stepper=true pour la même
// fenêtre de 2 minutes.
long lastStepperCycleTriggered = -1;

// ============================================================
//  GESTION STEPPER / POWER (Core 1)
// ============================================================

void enableStepper() {
  if (!stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_STATE);
    delay(20); // Stabilisation du courant avant le premier pas (aligné sur le test validé)
    stepperEnabled = true;
  }
}

void disableStepper() {
  if (stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_DISABLE_STATE);
    stepperEnabled = false;
  }
}

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
//  UTILITAIRES LCD LOG & DISPLAY (Core 1)
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

  xSemaphoreTake(lcdLogMutex, portMAX_DELAY);

  int lastIndex = (lcdLogStart + lcdLogCount - 1 + LCD_LOG_BUFFER_SIZE) % LCD_LOG_BUFFER_SIZE;
  if (lcdLogCount > 0 && strcmp(text, lcdLogBuffer[lastIndex]) == 0) {
    xSemaphoreGive(lcdLogMutex);
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

  xSemaphoreGive(lcdLogMutex);
}

void getCurrentLCDLog(char* out, size_t outSize) {
  xSemaphoreTake(lcdLogMutex, portMAX_DELAY);
  if (lcdLogCount == 0) {
    out[0] = '\0';
  } else {
    if (lcdLogIndex >= lcdLogCount) {
      lcdLogIndex = 0;
    }
    int idx = (lcdLogStart + lcdLogIndex) % LCD_LOG_BUFFER_SIZE;
    snprintf(out, outSize, "%s", lcdLogBuffer[idx]);
  }
  xSemaphoreGive(lcdLogMutex);
}

void advanceLCDLog() {
  xSemaphoreTake(lcdLogMutex, portMAX_DELAY);
  if (lcdLogCount > 1) {
    lcdLogIndex = (lcdLogIndex + 1) % lcdLogCount;
  }
  xSemaphoreGive(lcdLogMutex);
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
  const char* wifiState = wifiConnected ? "OK" : "--";

  if (autonomousMode) {
    snprintf(line0, sizeof(line0), "AUTO W:%s S:%s", wifiState, stepperMoving ? "ON" : "OFF");
  } else {
    snprintf(line0, sizeof(line0), "T:%.0f H:%d W:%s", avgTemp, (int)avgHumid, wifiState);
  }
  printLCDLine(0, line0);

  char line1[LCD_COLS + 1];
  getCurrentLCDLog(line1, sizeof(line1));
  printLCDLine(1, line1);
}

// ============================================================
//  WIFI & SERVEUR (Core 0 - NetworkTask)
// ============================================================

void buildServerUrl(const char* endpoint, char* output, size_t size) {
  // Le backend FastAPI est exposé avec le préfixe /api
  snprintf(output, size, "http://%s:%d/api%s", serverIP, serverPort, endpoint);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.mode(WIFI_STA);
  // Réduit la puissance d'émission WiFi pour limiter les pics de courant
  // (jusqu'à ~400-500mA en pleine puissance) qui peuvent faire chuter le
  // rail 3.3V sous le seuil du détecteur de brownout sur une alimentation
  // USB faible/longue. Ce n'est qu'une mitigation logicielle : le vrai fix
  // reste une alimentation capable de fournir les pics de courant (voir
  // note plus bas) + un condensateur de découplage proche de l'ESP32.
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  WiFi.setHostname(HOSTNAME);
  Serial.println(F("Connexion WiFi..."));
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT) {
    vTaskDelay(pdMS_TO_TICKS(500)); 
    // FIX 2 : Feed du WDT dans la boucle d'attente WiFi pour éviter le reset intempestif
    esp_task_wdt_reset(); 
    Serial.print(".");
  }

  bool isConnected = (WiFi.status() == WL_CONNECTED);
  xSemaphoreTake(stateMutex, portMAX_DELAY);
  shared.wifiConnected = isConnected;
  xSemaphoreGive(stateMutex);

  if (isConnected) {
    Serial.println("\nConnecte — IP: " + WiFi.localIP().toString());
    pushLCDLog("WiFi connecte");
  } else {
    Serial.printf("\nEchec WiFi (statut=%d)\n", WiFi.status());
    pushLCDLog("WiFi echec");
  }
}

void checkAutonomousMode_locked() {
  if (!shared.autonomousMode && shared.serverFailCount >= MAX_SERVER_RETRIES) {
    shared.autonomousMode = true;
    Serial.println(F("\n*** MODE AUTONOME ACTIVE ***"));
    Serial.printf("  %d echecs consecutifs\n", MAX_SERVER_RETRIES);
    pushLCDLog("Mode autonome");
  }
}

bool sendDataToServer(const String& jsonPayload) {
  if (WiFi.status() != WL_CONNECTED) {
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.wifiConnected = false;
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

  xSemaphoreTake(stateMutex, portMAX_DELAY);
  bool success = false;
  if (code > 0) {
    Serial.printf("POST /sensor/values -> %d\n", code);
    if (code == HTTP_CODE_OK || code == HTTP_CODE_CREATED) {
      pushLCDLog("Serveur OK");
      shared.serverFailCount = 0;
      shared.serverConnected = true;
      shared.autonomousMode = false;
      success = true;
    } else {
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

  Serial.println(F("Tentative de reconnexion au serveur..."));
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
    Serial.println(F("Serveur accessible — sortie du mode autonome"));
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.autonomousMode  = false;
    shared.serverFailCount = 0;
    shared.serverConnected = true;
    xSemaphoreGive(stateMutex);
    pushLCDLog("Serveur retrouve");
    pushLCDLog("Mode normal");
  } else {
    Serial.printf("Reconnect serveur echec -> %d\n", code);
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.serverConnected = false;
    xSemaphoreGive(stateMutex);
    pushLCDLog("Server NOK");
  }
}

bool getAutomationStatus() {
  if (WiFi.status() != WL_CONNECTED) return false;

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
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, response);
    if (!error) {
      bool fanCmd   = doc["fan"]        | false;
      bool humidCmd = doc["humidifier"] | false;

      xSemaphoreTake(stateMutex, portMAX_DELAY);
      shared.fanCmdFromServer     = fanCmd;
      shared.humidCmdFromServer   = humidCmd;
      shared.automationCmdPending = true;
      xSemaphoreGive(stateMutex);

      pushLCDLog("Server OK");
      pushLCDLog("Cmd automation");
      http.end();
      return true;
    }
    pushLCDLog("JSON statut err");
  } else {
    pushLCDLog("Server NOK");
  }

  http.end();
  return false;
}

bool getStepperCommand() {
  if (WiFi.status() != WL_CONNECTED) return false;

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
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, response);
    if (!error) {
      bool stepperCmd    = doc["stepper"] | false;
      bool hasCycleField = doc["cycle"].is<long>();
      long cycleIndex    = hasCycleField ? doc["cycle"].as<long>() : -2;

      // Le serveur renvoie stepper=true pendant toute une fenêtre de 2
      // minutes (voir get_automation_stepper côté backend). Une rotation
      // ne prenant que quelques secondes, sans ce garde-fou l'ESP32
      // redéclencherait une nouvelle rotation à CHAQUE poll (~3s) tant que
      // la fenêtre reste active — soit une dizaine de rotations au lieu
      // d'une seule. "cycle" identifie la fenêtre : on ne déclenche que si
      // elle diffère de la dernière déjà exécutée.
      // Repli : si le backend n'envoie pas encore "cycle" (ancienne
      // version non mise à jour), on retombe sur l'ancien comportement
      // (déclenche à chaque poll) plutôt que de bloquer silencieusement
      // le stepper.
      bool shouldTrigger = stepperCmd && (!hasCycleField || cycleIndex != lastStepperCycleTriggered);

      if (shouldTrigger) {
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        shared.stepperRequestPending = true;
        xSemaphoreGive(stateMutex);
        if (hasCycleField) {
          lastStepperCycleTriggered = cycleIndex;
        }
        pushLCDLog("Stepper ON (srv)");
      }
      http.end();
      return true;
    }
    pushLCDLog("JSON stepper err");
  } else {
    pushLCDLog("Server NOK");
  }

  http.end();
  return false;
}

// ============================================================
//  TÂCHE RÉSEAU (Core 0)
// ============================================================
void networkTaskFunction(void* pvParameters) {
  esp_task_wdt_add(NULL);

  unsigned long lastAutomationPoll   = 0;
  unsigned long lastReconnectAttempt = 0;

  connectWiFi();

  for (;;) {
    esp_task_wdt_reset();
    unsigned long now = millis();

    bool isConnected = (WiFi.status() == WL_CONNECTED);
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    shared.wifiConnected = isConnected;
    bool localAutonomous = shared.autonomousMode;
    xSemaphoreGive(stateMutex);

    if (!isConnected) {
      connectWiFi();
    }

    if (localAutonomous) {
      if (now - lastReconnectAttempt >= RECONNECT_INTERVAL) {
        lastReconnectAttempt = now;
        tryReconnectToServer();
      }
    } else {
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

      if (now - lastAutomationPoll >= AUTOMATION_POLL_INTERVAL) {
        lastAutomationPoll = now;
        getAutomationStatus();
        getStepperCommand();
      }
    }

    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

// ============================================================
//  LOGIQUE DE SECOURS AVEC HYSTÉRÉSIS (Core 1)
// ============================================================

void applyBackupLogic(float avgTemp, float avgHumid) {
  if (avgTemp > 0.0f) {
    if (avgTemp < (TEMP_MIN - TEMP_HYSTERESIS)) {
      fanOn = true;
    } else if (avgTemp > TEMP_TARGET) {
      fanOn = false;
    }
    digitalWrite(FAN_PIN, fanOn ? RELAY_ACTIVE_STATE : RELAY_INACTIVE_STATE);
  }

  if (avgHumid > 0.0f) {
    if (avgHumid < (HUMIDITY_MIN - HUMIDITY_HYSTERESIS)) {
      humidifierOn = true;
    } else if (avgHumid > HUMIDITY_TARGET) {
      humidifierOn = false;
    }
    digitalWrite(HUMIDIFIER_PIN, humidifierOn ? RELAY_ACTIVE_STATE : RELAY_INACTIVE_STATE);
  }
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
  return data;
}

void calculateAverages(SensorData sensors[], int count, float& avgTemp, float& avgHumid, int& failedCount) {
  float tTotal = 0.0f, hTotal = 0.0f;
  int valid = 0;
  failedCount = 0;

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

// FIX 3 : Debounce 100% NON-BLOQUANT pour éliminer les micro-saccades moteur
void checkStepperButton() {
  const unsigned long DEBOUNCE = 200;
  const unsigned long CONFIRM_TIME = 20;
  unsigned long now = millis();

  if (!stepperBtnPendingCheck) {
    if (digitalRead(BUTTON_STEPPER_PIN) == LOW && (now - lastButtonPress > DEBOUNCE)) {
      stepperBtnPendingCheck = true;
      stepperBtnTriggerTime = now;
    }
  } else {
    if (now - stepperBtnTriggerTime >= CONFIRM_TIME) {
      stepperBtnPendingCheck = false;
      if (digitalRead(BUTTON_STEPPER_PIN) == LOW) {
        lastButtonPress = now;
        pushLCDLog("Stepper manuel");
        startStepperRotation("bouton");
      }
    }
  }
}

void checkLCDScrollButton() {
  const unsigned long DEBOUNCE = 200;
  const unsigned long CONFIRM_TIME = 20;
  unsigned long now = millis();

  if (!lcdBtnPendingCheck) {
    if (digitalRead(BUTTON_LCD_SCROLL_PIN) == LOW && (now - lastScrollButtonPress > DEBOUNCE)) {
      lcdBtnPendingCheck = true;
      lcdBtnTriggerTime = now;
    }
  } else {
    if (now - lcdBtnTriggerTime >= CONFIRM_TIME) {
      lcdBtnPendingCheck = false;
      if (digitalRead(BUTTON_LCD_SCROLL_PIN) == LOW) {
        lastScrollButtonPress = now;
        advanceLCDLog();
      }
    }
  }
}

void applyNetworkOutputs() {
  bool localAutonomous, localServerConnected, localWifiConnected;
  bool automationPending, fanCmd = false, humidCmd = false;
  bool stepperPending;

  xSemaphoreTake(stateMutex, portMAX_DELAY);
  localAutonomous      = shared.autonomousMode;
  localServerConnected = shared.serverConnected;
  localWifiConnected   = shared.wifiConnected;
  automationPending    = shared.automationCmdPending;
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
  wifiConnected   = localWifiConnected;

  if (!autonomousMode && automationPending) {
    digitalWrite(FAN_PIN,        fanCmd   ? RELAY_ACTIVE_STATE : RELAY_INACTIVE_STATE);
    digitalWrite(HUMIDIFIER_PIN, humidCmd ? RELAY_ACTIVE_STATE : RELAY_INACTIVE_STATE);
    fanOn        = fanCmd;
    humidifierOn = humidCmd;
  }

  if (stepperPending) {
    startStepperRotation("serveur");
  }
}

void printStatus(SensorData sensors[], int count, float avgTemp, float avgHumid, int failed) {
  Serial.println(F("\n========== STATUS =========="));
  for (int i = 0; i < count; i++) {
    Serial.printf("  Capteur %d: %.1f°C, %.1f%% %s\n",
                  i + 1, sensors[i].temperature, sensors[i].humidity,
                  sensors[i].valid ? "" : "[ERREUR]");
  }
  Serial.printf("  Moyenne   : %.2f°C, %.2f%%\n", avgTemp, avgHumid);
  Serial.printf("  Fan: %s  |  Humidif: %s  |  Defauts: %d\n",
                fanOn ? "ON" : "OFF", humidifierOn ? "ON" : "OFF", failed);
  Serial.printf("  Stepper: %s (%ld)\n",
                stepper.distanceToGo() != 0 ? "MOVING" : "IDLE", stepper.distanceToGo());
  Serial.printf("  Server: %s  WiFi: %s\n",
                serverConnected ? "OK" : "NOK", wifiConnected ? "OK" : "NOK");
  if (autonomousMode) {
    Serial.println(F("  >>> MODE AUTONOME ACTIF <<<"));
  }
  Serial.println(F("============================\n"));
}

void setup() {
#if DEBUG_DISABLE_BOD
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // ⚠️ diagnostic seulement, voir note plus haut
#endif

  Serial.begin(115200);
  delay(1000);

  Serial.println(F("\n=== ESP32 Incubator Controller v4.2 ==="));

  // Les mutex doivent être créés en tout premier : pushLCDLog() (appelée dès
  // le premier lcd.init()/printLCDLine ci-dessous) prend lcdLogMutex, et
  // sendDataToServer()/checkAutonomousMode_locked() prennent stateMutex. Tant
  // que ces handles valent NULL (valeur par défaut avant création), tout
  // xSemaphoreTake() dessus déclenche l'assertion FreeRTOS
  // "xQueueSemaphoreTake ... (( pxQueue ))" et fait rebooter la carte.
  stateMutex  = xSemaphoreCreateMutex();
  lcdLogMutex = xSemaphoreCreateMutex();

  // FIX 4 : Rétrocompatibilité multi-versions ESP32 Arduino Core (v2.x vs v3.x)
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  esp_task_wdt_config_t twdt_config = {
      .timeout_ms = WDT_TIMEOUT_SEC * 1000,
      .idle_core_mask = (1 << 0) | (1 << 1),
      .trigger_panic = true
  };
  esp_task_wdt_reconfigure(&twdt_config);
  esp_task_wdt_add(NULL);
#else
  esp_task_wdt_init(WDT_TIMEOUT_SEC, true);
  esp_task_wdt_add(NULL);
#endif

  pinMode(STEPPER_ENABLE_PIN, OUTPUT);
  disableStepper();

  lcd.init();
  lcd.backlight();
  printLCDLine(0, "ESP32 Sensor v4");
  printLCDLine(1, "Init...");
  pushLCDLog("Initializing...");

#if !TEST_MODE_SKIP_SENSORS
  dht_1.begin();
  dht_2.begin();
  dht_3.begin();
  dht_4.begin();
#endif

  stepper.setMaxSpeed(STEPPER_MAX_SPEED);
  stepper.setAcceleration(STEPPER_ACCELERATION);

  pinMode(FAN_PIN,        OUTPUT);
  digitalWrite(FAN_PIN,        RELAY_INACTIVE_STATE);
  pinMode(HUMIDIFIER_PIN, OUTPUT);
  digitalWrite(HUMIDIFIER_PIN, RELAY_INACTIVE_STATE);

  initLEDs();
  digitalWrite(LED_BLUE_PIN, HIGH);

  pinMode(BUTTON_STEPPER_PIN,    INPUT_PULLUP);
  pinMode(BUTTON_LCD_SCROLL_PIN, INPUT_PULLUP);

  xTaskCreatePinnedToCore(
    networkTaskFunction,
    "NetworkTask",
    8192,
    NULL,
    1,
    &networkTaskHandle,
    0
  );

  Serial.println(F("Initialisation terminee. NetworkTask sur Core 0.\n"));
}

void loop() {
  esp_task_wdt_reset(); 

  static unsigned long lastSendTime     = 0;
  static unsigned long lastSlowTaskTime = 0;
  unsigned long now = millis();

  applyNetworkOutputs();

  // Pilotage non-bloquant du Stepper
  if (stepper.distanceToGo() != 0) {
    enableStepper();
    stepper.run();
  } else {
    disableStepper();
  }

  // Lecture et traitement des capteurs
  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;

#if TEST_MODE_SKIP_SENSORS
    // Pas de lecture DHT — juste un heartbeat pour confirmer que loop()
    // tourne normalement pendant le test du stepper.
    Serial.println(F("[TEST_MODE_SKIP_SENSORS] capteurs desactives — test stepper en cours"));
#else
    SensorData sensors[4];
    sensors[0] = readSensor(dht_1, 1);
    sensors[1] = readSensor(dht_2, 2);
    sensors[2] = readSensor(dht_3, 3);
    sensors[3] = readSensor(dht_4, 4);

    calculateAverages(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);

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
    payload["fan_status"]          = fanOn;
    payload["humidifier_status"]   = humidifierOn;
    payload["numFailedSensors"]    = numFailedSensors;

    String jsonPayload;
    serializeJson(payload, jsonPayload);

    if (!autonomousMode) {
      xSemaphoreTake(stateMutex, portMAX_DELAY);
      shared.pendingPayload   = jsonPayload;
      shared.sensorDataReady  = true;
      xSemaphoreGive(stateMutex);
    }

    if (autonomousMode || !serverConnected) {
      applyBackupLogic(avgTemperature, avgHumidity);
    }

    printStatus(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);
#endif
  }

  // Tâches secondaires d'affichage et boutons
  if (now - lastSlowTaskTime >= 50) {
    lastSlowTaskTime = now;
    checkStepperButton();
    checkLCDScrollButton();
    updateLCDScroll(now);
    updateStatusLEDs(avgTemperature, avgHumidity, serverConnected);
    displayStatusOnLCD(avgTemperature, avgHumidity);
  }

  delay(1);
}