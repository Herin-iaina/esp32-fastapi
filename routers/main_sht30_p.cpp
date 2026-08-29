#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include <PCF8574.h>  // Bibliotheque "PCF8574" (Renzo Mischianti) - via Library Manager
#include "Adafruit_SHT4x.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <esp_task_wdt.h>

// ============================================================
//  ⚠️ MODE TEST — met à 1 pour tester le stepper (bouton) sans que la
//  lecture SHT45 n'interfère ou ne pollue les logs. Remettre à 0 pour
//  l'usage réel de l'incubateur.
// ============================================================
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
#define STEPPER_PIN_DIR     12
#define STEPPER_PIN_STEP    13
#define STEPPER_ENABLE_PIN  32

// Reprend la valeur confirmée par test direct sur main.cpp : ce module
// TB6600 a un ENA actif HAUT (HIGH = bobines sous tension, LOW = driver
// coupé) — inverse de la convention ENA+/ENA- standard. Ne pas réinverser
// sans retester physiquement.
#define STEPPER_ENABLE_ACTIVE_STATE   HIGH
#define STEPPER_ENABLE_DISABLE_STATE  LOW

#define FAN_PIN             14
#define HUMIDIFIER_PIN      15

// ============================================================
//  EXPANDER I2C PCF8574 — LEDs + BOUTONS
// ============================================================
// LEDs (3V) et boutons deportes sur un PCF8574T, sur le bus principal, comme
// le LCD (PAS derrière le TCA9548A — seuls les SHT45 partagent son adresse
// fixe 0x44 et ont besoin du mux). Libere les GPIO ESP32 16,17,18,19,23,27.
#define PCF8574_ADDRESS      0x20   // Reglable 0x20-0x27 via A0-A2 si conflit

// LEDs montees en actif-BAS (LED + résistance série entre +5V et la pin) :
// pin a 0 = LED allumee (le PCF8574 "sink" le courant), pin a 1 = eteinte.
#define LED_GREEN_PIN       0    // Temp + humidité dans les seuils
#define LED_ORANGE_PIN      1    // Temp ou humidité en dessous du min
#define LED_RED_PIN         2    // Temp ou humidité au dessus du max
#define LED_BLUE_PIN        3    // Serveur inaccessible / mode autonome
#define LED_ACTIVE_STATE    LOW
#define LED_INACTIVE_STATE  HIGH

// Boutons cables entre la pin et GND, pull-up interne faible du PCF8574
#define BUTTON_STEPPER_PIN      4
#define BUTTON_LCD_SCROLL_PIN   5

// I2C (bus principal ESP32)
#define I2C_SDA         21
#define I2C_SCL         22

// LCD I2C — branché directement sur le bus principal, PAS derrière le
// multiplexeur (seuls les capteurs SHT45 passent par le TCA9548A car ils
// partagent tous la même adresse fixe 0x44).
#define LCD_ADDRESS     0x27
#define LCD_COLS        16
#define LCD_ROWS        2

// ============================================================
//  MULTIPLEXEUR I2C TCA9548A + CAPTEURS SHT45
// ============================================================
// Le SHT45 (comme tout SHT4x) n'a pas de broche d'adresse alternative :
// son adresse I2C est fixée à 0x44. Pour en mettre plusieurs sur le même
// bus, il faut donc passer par un multiplexeur — le TCA9548A expose 8
// canaux (0-7), chacun isolant électriquement un sous-bus dédié.
#define TCA9548A_ADDRESS    0x70
#define SHT45_I2C_ADDRESS   0x44

#define NUM_SENSORS 4
// Canal du multiplexeur associé à chaque capteur SHT45. Pour ajouter un
// capteur, brancher son SDA/SCL sur un canal libre du TCA9548A (0-7) et
// ajouter l'entrée correspondante ici + incrémenter NUM_SENSORS.
const uint8_t SENSOR_MUX_CHANNEL[NUM_SENSORS] = { 0, 1, 2, 3 };

// ============================================================
//  WIFI & SERVEUR
// ============================================================
const char* ssid       = "Airbox-4D56";
const char* password   = "16017581";
const char* serverIP   = "192.168.1.100";
const int   serverPort = 5000;
const char* apiKey     = "Votre_Cle_API";
const char* HOSTNAME   = "ESP32-Sensor-SHT45";

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
//  SÉCURITÉ CAPTEUR — ANTI-CONDENSATION (chauffage interne SHT45)
// ============================================================
// Valeurs par défaut — ajustables à distance sans reflasher via l'endpoint
// serveur /sensor/automation/config (voir getAutomationConfig()). Ce sont
// des variables (pas des const) précisément pour ça ; ne pas les modifier
// directement en dehors de applyServerConfig(), qui passe par le mutex.
float         humidityHeaterThreshold = 90.0f;
float         humidityResetThreshold  = 85.0f;  // Seuil bas de réarmement (hystérésis) — cf. note ci-dessous
unsigned long humidityHighSustainMs   = 5UL * 60UL * 1000UL;  // 5 minutes par défaut
unsigned long sensorCooldownMs        = 3UL * 60UL * 1000UL;  // pause avant reprise des lectures — à ajuster selon retour terrain
// Note hystérésis : sans humidityResetThreshold < humidityHeaterThreshold,
// un bruit de mesure faisant osciller RH autour de 90% (89.8% -> 90.2% ->
// 89.9%...) réinitialiserait humidityHighSince à chaque petite chute,
// alors que l'humidité est en pratique restée élevée en continu.

// Réglage du chauffage : haute puissance, impulsion courte (1s). Voir
// Adafruit_SHT4x.h pour les autres options (MED/LOW, 1S/100MS).
#define SHT45_HEATER_SETTING  SHT4X_HIGH_HEATER_1S
// Si, après ce nombre de cycles chauffage+pause consécutifs, RH est
// toujours au-dessus du seuil, ce n'est probablement plus un problème de
// condensation ponctuelle sur le capteur mais un vrai souci d'humidité
// ambiante (ventilation, étanchéité...). On arrête de rechauffer en
// boucle et on signale une alerte au lieu de continuer indéfiniment.
const int HEATER_MAX_CONSECUTIVE_TRIGGERS = 3;

// ============================================================
//  DIAGNOSTIC I2C (optionnel — désactivé par défaut)
// ============================================================
// Passe à 1 pour lancer un scan complet du bus principal + de chaque canal
// du TCA9548A au démarrage (utile une seule fois, avant le premier essai
// réel, pour confirmer le câblage sans avoir à écrire un sketch séparé).
// Remettre à 0 ensuite : le scan ajoute ~1-2s au boot et n'apporte rien en
// usage normal.
#define DEBUG_I2C_SCAN 0

// ============================================================
//  TIMING & BUFFERS
// ============================================================
const unsigned long SEND_INTERVAL             = 5000UL;   // ms entre chaque cycle capteurs
const unsigned long LCD_SCROLL_INTERVAL       = 3000UL;   // ms entre chaque défilement auto
const unsigned long RECONNECT_INTERVAL        = 60000UL;  // ms entre tentatives de reconnexion serveur
const unsigned long WIFI_TIMEOUT              = 15000UL;  // ms max pour connexion WiFi
const unsigned long AUTOMATION_POLL_INTERVAL  = 3000UL;   // ms entre chaque poll automation/stepper
const unsigned long CONFIG_POLL_INTERVAL      = 300000UL; // ms entre chaque poll de config (5 min) — ces seuils changent rarement
const unsigned long HTTP_TIMEOUT              = 1500UL;   // ms timeout par requête HTTP

const int LCD_LOG_BUFFER_SIZE = 6;
const int MAX_SERVER_RETRIES  = 10;

const uint32_t WDT_TIMEOUT_SEC = 25;   // > WIFI_TIMEOUT (15s) pour marge de sécurité

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
Adafruit_SHT4x sht45Sensors[NUM_SENSORS];
bool sensorAvailable[NUM_SENSORS] = { false, false, false, false };

AccelStepper stepper(AccelStepper::DRIVER, STEPPER_PIN_STEP, STEPPER_PIN_DIR);
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);
PCF8574 pcf8574(PCF8574_ADDRESS);

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

  // Config anti-condensation reçue du serveur (voir getAutomationConfig())
  bool  configPending             = false;
  float cfgHumidityHeaterThreshold = 90.0f;
  float cfgHumidityResetThreshold  = 85.0f;
  unsigned long cfgHumidityHighSustainMs = 5UL * 60UL * 1000UL;
  unsigned long cfgSensorCooldownMs      = 3UL * 60UL * 1000UL;
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

// FIX SECURITE : etat de presence reelle du PCF8574 sur le bus I2C.
// Tant que ce flag est false, on IGNORE toute lecture de bouton et
// tout pilotage LED via le PCF8574 : un module debranche ne doit
// jamais pouvoir simuler un appui bouton et lancer le moteur.
bool pcf8574Connected              = false;
unsigned long lastPcf8574CheckTime = 0;
const unsigned long PCF8574_CHECK_INTERVAL = 1000; // ms — sonde la presence regulierement

// Sonde legere et fiable : ACK I2C direct sur l'adresse du PCF8574.
// Independant de la logique interne de la bibliotheque, donc marche
// meme si le module a ete debranche apres le demarrage.
bool probePCF8574Presence() {
  Wire.beginTransmission(PCF8574_ADDRESS);
  return (Wire.endTransmission() == 0);
}
unsigned long stepperBtnTriggerTime = 0;
unsigned long lcdBtnTriggerTime     = 0;

// LCD log ring buffer
char lcdLogBuffer[LCD_LOG_BUFFER_SIZE][LCD_COLS + 1];
int  lcdLogCount = 0;
int  lcdLogIndex = 0;
int  lcdLogStart = 0;
unsigned long lastLogScroll = 0;

// État de sécurité capteur (anti-condensation) — Core 1 uniquement
enum SensorSafetyState { SAFETY_NORMAL, SAFETY_COOLDOWN };
SensorSafetyState safetyState        = SAFETY_NORMAL;
unsigned long     humidityHighSince  = 0;   // 0 = pas de dépassement RH>90% en cours
unsigned long     cooldownStartTime  = 0;
int               heaterConsecutiveTriggers = 0; // remis à 0 dès que RH redescend sous humidityResetThreshold
bool              heaterEscalationAlert     = false; // true = chauffage inefficace après plusieurs tentatives

// Historique des déclenchements chauffage, à des fins de diagnostic côté
// serveur (repérer un pattern récurrent lié à un cycle jour/nuit, une
// mauvaise ventilation, etc.). heaterTriggerCount ne se réinitialise
// jamais pendant l'uptime (contrairement à heaterConsecutiveTriggers) ;
// lastHeaterTriggerMillis vaut 0 tant qu'aucun déclenchement n'a eu lieu.
unsigned long     heaterTriggerCount        = 0;
unsigned long     lastHeaterTriggerMillis   = 0;

// ============================================================
//  GESTION STEPPER / POWER (Core 1)
// ============================================================

void enableStepper() {
  if (!stepperEnabled) {
    digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_STATE);
    delay(20); // Stabilisation du courant avant le premier pas
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
  } else if (safetyState == SAFETY_COOLDOWN) {
    snprintf(line0, sizeof(line0), "PAUSE capteur..");
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
  snprintf(output, size, "http://%s:%d/api%s", serverIP, serverPort, endpoint);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  WiFi.setHostname(HOSTNAME);
  Serial.println(F("Connexion WiFi..."));
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT) {
    vTaskDelay(pdMS_TO_TICKS(500));
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
      if (doc["stepper"] | false) {
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        shared.stepperRequestPending = true;
        xSemaphoreGive(stateMutex);
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

// Récupère à distance les seuils anti-condensation (voir SÉCURITÉ CAPTEUR
// plus haut). Endpoint optionnel : si le serveur ne l'implémente pas
// (404) ou renvoie un JSON incomplet, on garde simplement les valeurs
// actuelles — pas d'urgence, ce n'est pas un endpoint de sécurité vitale.
// JSON attendu, tous les champs optionnels :
// {
//   "humidity_heater_threshold": 90.0,
//   "humidity_reset_threshold":  85.0,
//   "humidity_high_sustain_min": 5,
//   "sensor_cooldown_min":       3
// }
bool getAutomationConfig() {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClient wifiClient;
  HTTPClient http;
  char url[128];
  buildServerUrl("/sensor/automation/config", url, sizeof(url));
  http.setTimeout(HTTP_TIMEOUT);
  http.begin(wifiClient, url);
  http.addHeader("x-api-key", apiKey);
  int code = http.GET();

  if (code == HTTP_CODE_OK) {
    String response = http.getString();
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, response);
    if (!error) {
      xSemaphoreTake(stateMutex, portMAX_DELAY);
      if (doc["humidity_heater_threshold"].is<float>()) {
        shared.cfgHumidityHeaterThreshold = doc["humidity_heater_threshold"].as<float>();
      }
      if (doc["humidity_reset_threshold"].is<float>()) {
        shared.cfgHumidityResetThreshold = doc["humidity_reset_threshold"].as<float>();
      }
      if (doc["humidity_high_sustain_min"].is<float>()) {
        shared.cfgHumidityHighSustainMs = (unsigned long)(doc["humidity_high_sustain_min"].as<float>() * 60000.0f);
      }
      if (doc["sensor_cooldown_min"].is<float>()) {
        shared.cfgSensorCooldownMs = (unsigned long)(doc["sensor_cooldown_min"].as<float>() * 60000.0f);
      }
      shared.configPending = true;
      xSemaphoreGive(stateMutex);

      Serial.println(F("Config anti-condensation recue du serveur"));
      http.end();
      return true;
    }
    pushLCDLog("JSON config err");
  } else if (code != HTTP_CODE_NOT_FOUND) {
    // 404 = endpoint non implémenté côté serveur, pas une vraie erreur —
    // on ne pollue pas les logs/LCD pour ça.
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
  unsigned long lastConfigPoll       = 0;

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

      if (now - lastConfigPoll >= CONFIG_POLL_INTERVAL) {
        lastConfigPoll = now;
        getAutomationConfig();
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
    digitalWrite(FAN_PIN, fanOn ? HIGH : LOW);
  }

  if (avgHumid > 0.0f) {
    if (avgHumid < (HUMIDITY_MIN - HUMIDITY_HYSTERESIS)) {
      humidifierOn = true;
    } else if (avgHumid > HUMIDITY_TARGET) {
      humidifierOn = false;
    }
    digitalWrite(HUMIDIFIER_PIN, humidifierOn ? HIGH : LOW);
  }
}

// ============================================================
//  MULTIPLEXEUR I2C (TCA9548A) & CAPTEURS SHT45 (Core 1)
// ============================================================

// Sélectionne le canal actif du TCA9548A. Toutes les transactions I2C
// suivantes sur le bus principal sont redirigées vers ce canal jusqu'au
// prochain appel. La LCD (adresse 0x27, hors mux) n'est pas affectée.
// Retourne false si le mux lui-même ne répond pas (câblage, canal grillé,
// adresse erronée) — sans ce contrôle, on lirait silencieusement le mauvais
// capteur, ou rien, en pensant avoir changé de canal.
bool tcaSelectChannel(uint8_t channel) {
  if (channel > 7) return false;
  Wire.beginTransmission(TCA9548A_ADDRESS);
  Wire.write(1 << channel);
  return Wire.endTransmission() == 0;
}

// Diagnostic optionnel (DEBUG_I2C_SCAN=1) : scanne le bus principal, puis
// chaque canal du TCA9548A, et imprime les adresses trouvées. À lancer une
// fois avant le premier essai réel pour confirmer le câblage — on doit
// voir 0x70 (mux) et 0x27 (LCD) sur le bus principal, et 0x44 (SHT45) sur
// chaque canal câblé. N'interrompt pas le boot normal, juste informatif.
void scanI2CBus() {
  Serial.println(F("\n--- Scan I2C : bus principal ---"));
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  Peripherique trouve a 0x%02X\n", addr);
      found++;
    }
  }
  if (found == 0) Serial.println(F("  Aucun peripherique trouve — verifier cablage SDA/SCL/alim"));

  Serial.println(F("--- Scan I2C : canaux du TCA9548A (0-7) ---"));
  for (uint8_t ch = 0; ch < 8; ch++) {
    if (!tcaSelectChannel(ch)) {
      Serial.printf("  Canal %d: mux injoignable, scan annule\n", ch);
      continue;
    }
    delay(5);
    bool any = false;
    for (uint8_t addr = 1; addr < 127; addr++) {
      if (addr == TCA9548A_ADDRESS) continue; // évite de re-détecter le mux lui-même
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        Serial.printf("  Canal %d -> peripherique a 0x%02X\n", ch, addr);
        any = true;
      }
    }
    if (!any) Serial.printf("  Canal %d -> rien detecte\n", ch);
  }
  Serial.println(F("--- Fin du scan I2C ---\n"));
}

bool initSHT45Sensors() {
  Wire.begin(I2C_SDA, I2C_SCL);

#if DEBUG_I2C_SCAN
  scanI2CBus();
#endif

  bool anyOk = false;
  for (int i = 0; i < NUM_SENSORS; i++) {
    if (!tcaSelectChannel(SENSOR_MUX_CHANNEL[i])) {
      sensorAvailable[i] = false;
      Serial.printf("TCA9548A: canal %d injoignable (mux non detecte ou cable) — capteur #%d ignore\n",
                    SENSOR_MUX_CHANNEL[i], i + 1);
      continue;
    }
    delay(5); // laisser le mux basculer avant d'interroger le capteur

    if (sht45Sensors[i].begin(&Wire)) {
      sht45Sensors[i].setPrecision(SHT4X_HIGH_PRECISION);
      sht45Sensors[i].setHeater(SHT4X_NO_HEATER);
      sensorAvailable[i] = true;
      anyOk = true;
      Serial.printf("SHT45 #%d (mux ch%d) detecte\n", i + 1, SENSOR_MUX_CHANNEL[i]);
    } else {
      sensorAvailable[i] = false;
      Serial.printf("SHT45 #%d (mux ch%d) non detecte\n", i + 1, SENSOR_MUX_CHANNEL[i]);
    }
  }
  return anyOk;
}

SensorData readSHT45(int idx) {
  SensorData data;

  if (!sensorAvailable[idx]) {
    data.valid = false;
    return data;
  }

  if (!tcaSelectChannel(SENSOR_MUX_CHANNEL[idx])) {
    Serial.printf("TCA9548A: canal %d injoignable au moment de la lecture (capteur #%d)\n",
                  SENSOR_MUX_CHANNEL[idx], idx + 1);
    data.valid = false;
    return data;
  }

  sensors_event_t humidityEvt, tempEvt;
  bool ok = sht45Sensors[idx].getEvent(&humidityEvt, &tempEvt);

  if (ok) {
    data.temperature = tempEvt.temperature;
    data.humidity    = humidityEvt.relative_humidity;
    data.valid       = !isnan(data.temperature) && !isnan(data.humidity);
  } else {
    data.valid = false;
  }

  if (!data.valid) {
    Serial.printf("Capteur SHT45 #%d: ERREUR de lecture\n", idx + 1);
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

// Déclenche une impulsion de chauffage interne sur chaque capteur
// disponible, l'un après l'autre. ATTENTION : l'appel getEvent() avec
// chauffage actif est bloquant côté librairie Adafruit_SHT4x pendant
// toute la durée du réglage choisi (jusqu'à ~1.1s avec SHT4X_HIGH_HEATER_1S).
// Sur 4 capteurs, ça peut donc bloquer loop() jusqu'à ~4-5s d'affilée —
// acceptable car l'événement est rare (RH>90% pendant 5 min), mais on
// nourrit le watchdog entre chaque capteur par précaution.
void triggerSensorHeaterAll() {
  for (int i = 0; i < NUM_SENSORS; i++) {
    if (!sensorAvailable[i]) continue;

    esp_task_wdt_reset();
    if (!tcaSelectChannel(SENSOR_MUX_CHANNEL[i])) {
      Serial.printf("TCA9548A: canal %d injoignable — chauffage capteur #%d ignore\n",
                    SENSOR_MUX_CHANNEL[i], i + 1);
      continue;
    }

    sensors_event_t humidityEvt, tempEvt;
    sht45Sensors[i].setHeater(SHT45_HEATER_SETTING);
    sht45Sensors[i].getEvent(&humidityEvt, &tempEvt);   // exécute l'impulsion (bloquant, courte durée)
    sht45Sensors[i].setHeater(SHT4X_NO_HEATER);         // retour en lecture normale

    Serial.printf("  Impulsion chauffage capteur #%d (mux ch%d) terminee\n", i + 1, SENSOR_MUX_CHANNEL[i]);
  }
}

// Surveillance non-bloquante de l'humidité (millis()) : si la moyenne
// dépasse 90% pendant au moins 5 minutes consécutives, on déclenche le
// chauffage anti-condensation sur tous les capteurs puis on bascule en
// pause (SAFETY_COOLDOWN) pour laisser le capteur se stabiliser avant de
// reprendre les lectures normales.
// Retourne true si les lectures sont autorisées ce cycle, false si le
// système est en pause de refroidissement.
bool updateSensorSafety(float lastAvgHumid, unsigned long now) {
  if (safetyState == SAFETY_COOLDOWN) {
    if (now - cooldownStartTime >= sensorCooldownMs) {
      safetyState = SAFETY_NORMAL;
      humidityHighSince = 0;
      Serial.println(F("Fin de pause — reprise des lectures capteurs"));
      pushLCDLog("Capteur refroidi");
    } else {
      return false; // toujours en pause, pas de nouvelle lecture ce cycle
    }
  }

  if (lastAvgHumid > humidityHeaterThreshold) {
    if (humidityHighSince == 0) {
      humidityHighSince = now;
      Serial.println(F("RH > seuil detecte — surveillance demarree"));
    } else if (now - humidityHighSince >= humidityHighSustainMs) {

      if (heaterConsecutiveTriggers >= HEATER_MAX_CONSECUTIVE_TRIGGERS) {
        // Le chauffage n'a pas suffi après plusieurs tentatives : on ne
        // rechauffe plus en boucle, on remonte une alerte à la place.
        // L'humidité ambiante reste élevée -> problème probable côté
        // ventilation/étanchéité de l'incubateur, pas côté capteur.
        if (!heaterEscalationAlert) {
          Serial.println(F("!!! ALERTE: RH>seuil persiste malgre plusieurs chauffages consecutifs !!!"));
          pushLCDLog("ALERTE humidite!");
        }
        heaterEscalationAlert = true;
        // On laisse quand même les lectures continuer normalement pour
        // remonter la valeur réelle au serveur/LED (pas de nouvelle pause).
        return true;
      }

      Serial.println(F("RH > seuil soutenue -> declenchement chauffage capteur"));
      pushLCDLog("Chauffage capteur");

      triggerSensorHeaterAll();
      heaterConsecutiveTriggers++;
      heaterTriggerCount++;
      lastHeaterTriggerMillis = now;

      safetyState       = SAFETY_COOLDOWN;
      cooldownStartTime = millis();
      humidityHighSince = 0;
      pushLCDLog("Pause refroidiss.");
      return false; // on vient de chauffer, pas de lecture ce cycle-ci
    }
  } else if (lastAvgHumid < humidityResetThreshold) {
    // Marge d'hystérésis : on ne réarme le compteur/l'alerte que
    // lorsque RH est vraiment redescendue, pas au premier petit creux
    // sous le seuil haut qui pourrait n'être que du bruit de mesure.
    humidityHighSince         = 0;
    heaterConsecutiveTriggers = 0;
    if (heaterEscalationAlert) {
      heaterEscalationAlert = false;
      Serial.println(F("RH revenue a la normale — alerte humidite levee"));
      pushLCDLog("Humidite OK");
    }
  }
  // Entre humidityResetThreshold et humidityHeaterThreshold : zone morte
  // volontaire, on ne touche ni au compteur ni à l'alerte.

  return true;
}

// ============================================================
//  LEDS DE STATUT (Core 1)
// ============================================================

void initLEDs() {
  const uint8_t pins[] = { LED_GREEN_PIN, LED_ORANGE_PIN, LED_RED_PIN, LED_BLUE_PIN };
  for (uint8_t p : pins) {
    pcf8574.pinMode(p, OUTPUT);
    pcf8574.digitalWrite(p, LED_INACTIVE_STATE);
  }
}

void setAllLEDsOff() {
  if (!pcf8574Connected) return;
  pcf8574.digitalWrite(LED_GREEN_PIN,  LED_INACTIVE_STATE);
  pcf8574.digitalWrite(LED_ORANGE_PIN, LED_INACTIVE_STATE);
  pcf8574.digitalWrite(LED_RED_PIN,    LED_INACTIVE_STATE);
  pcf8574.digitalWrite(LED_BLUE_PIN,   LED_INACTIVE_STATE);
}

void updateStatusLEDs(float avgTemp, float avgHumid, bool serverOk) {
  // SECURITE : pas de PCF8574 => pas de tentative d'ecriture I2C inutile.
  if (!pcf8574Connected) return;

  setAllLEDsOff();

  if (!serverOk || autonomousMode) {
    pcf8574.digitalWrite(LED_BLUE_PIN, LED_ACTIVE_STATE);
  }
  if (avgTemp <= 0.0f || avgHumid <= 0.0f) {
    pcf8574.digitalWrite(LED_RED_PIN, LED_ACTIVE_STATE);
    return;
  }

  if (heaterEscalationAlert) {
    // Alerte prioritaire : chauffage anti-condensation inefficace après
    // plusieurs tentatives -> probable souci de ventilation/étanchéité.
    pcf8574.digitalWrite(LED_RED_PIN, LED_ACTIVE_STATE);
    return;
  }

  bool tempOk  = avgTemp  >= TEMP_MIN     && avgTemp  <= TEMP_MAX;
  bool humidOk = avgHumid >= HUMIDITY_MIN && avgHumid <= HUMIDITY_MAX;

  if (tempOk && humidOk) {
    pcf8574.digitalWrite(LED_GREEN_PIN, LED_ACTIVE_STATE);
  } else if (avgTemp > TEMP_MAX || avgHumid > HUMIDITY_MAX) {
    pcf8574.digitalWrite(LED_RED_PIN, LED_ACTIVE_STATE);
  } else {
    pcf8574.digitalWrite(LED_ORANGE_PIN, LED_ACTIVE_STATE);
  }
}

// ============================================================
//  BOUTONS (debounce non-bloquant, Core 1)
// ============================================================

void checkStepperButton() {
  // SECURITE : PCF8574 absent/debranche => on n'ecoute pas ce "bouton
  // fantome". Sans ce garde, une lecture I2C echouee peut etre
  // interpretee comme un appui permanent et declencher le moteur seul.
  if (!pcf8574Connected) return;

  const unsigned long DEBOUNCE = 200;
  const unsigned long CONFIRM_TIME = 20;
  unsigned long now = millis();

  if (!stepperBtnPendingCheck) {
    if (pcf8574.digitalRead(BUTTON_STEPPER_PIN) == LOW && (now - lastButtonPress > DEBOUNCE)) {
      stepperBtnPendingCheck = true;
      stepperBtnTriggerTime = now;
    }
  } else {
    if (now - stepperBtnTriggerTime >= CONFIRM_TIME) {
      stepperBtnPendingCheck = false;
      if (pcf8574.digitalRead(BUTTON_STEPPER_PIN) == LOW) {
        lastButtonPress = now;
        pushLCDLog("Stepper manuel");
        startStepperRotation("bouton");
      }
    }
  }
}

void checkLCDScrollButton() {
  // Meme securite que checkStepperButton() : pas de PCF8574, pas de lecture.
  if (!pcf8574Connected) return;

  const unsigned long DEBOUNCE = 200;
  const unsigned long CONFIRM_TIME = 20;
  unsigned long now = millis();

  if (!lcdBtnPendingCheck) {
    if (pcf8574.digitalRead(BUTTON_LCD_SCROLL_PIN) == LOW && (now - lastScrollButtonPress > DEBOUNCE)) {
      lcdBtnPendingCheck = true;
      lcdBtnTriggerTime = now;
    }
  } else {
    if (now - lcdBtnTriggerTime >= CONFIRM_TIME) {
      lcdBtnPendingCheck = false;
      if (pcf8574.digitalRead(BUTTON_LCD_SCROLL_PIN) == LOW) {
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
  bool configPending = false;
  float cfgHeaterThresh = 0, cfgResetThresh = 0;
  unsigned long cfgSustainMs = 0, cfgCooldownMs = 0;

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
  configPending = shared.configPending;
  if (configPending) {
    cfgHeaterThresh = shared.cfgHumidityHeaterThreshold;
    cfgResetThresh  = shared.cfgHumidityResetThreshold;
    cfgSustainMs    = shared.cfgHumidityHighSustainMs;
    cfgCooldownMs   = shared.cfgSensorCooldownMs;
    shared.configPending = false;
  }
  xSemaphoreGive(stateMutex);

  autonomousMode  = localAutonomous;
  serverConnected = localServerConnected;
  wifiConnected   = localWifiConnected;

  if (!autonomousMode && automationPending) {
    digitalWrite(FAN_PIN,        fanCmd   ? HIGH : LOW);
    digitalWrite(HUMIDIFIER_PIN, humidCmd ? HIGH : LOW);
    fanOn        = fanCmd;
    humidifierOn = humidCmd;
  }

  if (stepperPending) {
    startStepperRotation("serveur");
  }

  if (configPending) {
    humidityHeaterThreshold = cfgHeaterThresh;
    humidityResetThreshold  = cfgResetThresh;
    humidityHighSustainMs   = cfgSustainMs;
    sensorCooldownMs        = cfgCooldownMs;
    Serial.printf("Nouveaux seuils anti-condensation: seuil=%.1f%% reset=%.1f%% sustain=%lums cooldown=%lums\n",
                  humidityHeaterThreshold, humidityResetThreshold, humidityHighSustainMs, sensorCooldownMs);
    pushLCDLog("Config maj (srv)");
  }
}

void printStatus(SensorData sensors[], int count, float avgTemp, float avgHumid, int failed) {
  Serial.println(F("\n========== STATUS (SHT45) =========="));
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
  if (safetyState == SAFETY_COOLDOWN) {
    Serial.println(F("  >>> PAUSE ANTI-CONDENSATION (chauffage effectue) <<<"));
  }
  Serial.println(F("=====================================\n"));
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println(F("\n=== ESP32 Incubator Controller SHT45 + TCA9548A ==="));

  // Les mutex doivent être créés en tout premier — voir main.cpp pour le
  // détail : pushLCDLog()/sendDataToServer() en dépendent dès l'init.
  stateMutex  = xSemaphoreCreateMutex();
  lcdLogMutex = xSemaphoreCreateMutex();

  // Rétrocompatibilité multi-versions ESP32 Arduino Core (v2.x vs v3.x)
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

  // Bus I2C partage (LCD + PCF8574 + TCA9548A/SHT45). Initialise ici,
  // independamment de TEST_MODE_SKIP_SENSORS — LEDs/boutons doivent
  // fonctionner meme si les capteurs sont desactives pour un test.
  // Rappel sans effet : initSHT45Sensors() rappelle Wire.begin() plus bas,
  // ce qui est sans risque sur l'ESP32.
  Wire.begin(I2C_SDA, I2C_SCL);
  if (!pcf8574.begin()) {
    Serial.println(F("ATTENTION: PCF8574 (LEDs/boutons) non detecte!"));
  }
  pcf8574Connected = probePCF8574Presence();
  if (!pcf8574Connected) {
    Serial.println(F("ATTENTION: PCF8574 absent du bus I2C — boutons/LEDs desactives par securite."));
  }

  lcd.init();
  lcd.backlight();
  printLCDLine(0, "ESP32 SHT45");
  printLCDLine(1, "Init...");
  pushLCDLog("Initializing...");

#if !TEST_MODE_SKIP_SENSORS
  if (!initSHT45Sensors()) {
    Serial.println(F("ATTENTION: Aucun capteur SHT45 detecte!"));
    pushLCDLog("Aucun capteur!");
  }
#endif

  stepper.setMaxSpeed(STEPPER_MAX_SPEED);
  stepper.setAcceleration(STEPPER_ACCELERATION);

  pinMode(FAN_PIN,        OUTPUT);
  digitalWrite(FAN_PIN,        LOW);
  pinMode(HUMIDIFIER_PIN, OUTPUT);
  digitalWrite(HUMIDIFIER_PIN, LOW);

  if (pcf8574Connected) {
    initLEDs();
    pcf8574.digitalWrite(LED_BLUE_PIN, LED_ACTIVE_STATE);

    // Boutons sur PCF8574 : mode INPUT active la pull-up faible interne
    // (quasi-bidirectionnel), pas besoin de pull-up externe dans la plupart
    // des cas.
    pcf8574.pinMode(BUTTON_STEPPER_PIN,    INPUT);
    pcf8574.pinMode(BUTTON_LCD_SCROLL_PIN, INPUT);
  }

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
    Serial.println(F("[TEST_MODE_SKIP_SENSORS] capteurs desactives — test stepper en cours"));
#else
    // La décision de lire ou non se base sur la MOYENNE PRÉCÉDENTE
    // (avgHumidity du cycle d'avant) : c'est cette valeur qui alimente la
    // surveillance non-bloquante par millis(). Si le système est en pause
    // de refroidissement, on saute la lecture ce cycle-ci.
    bool readsAllowed = updateSensorSafety(avgHumidity, now);

    if (readsAllowed) {
      SensorData sensors[NUM_SENSORS];
      for (int i = 0; i < NUM_SENSORS; i++) {
        sensors[i] = readSHT45(i);
      }

      calculateAverages(sensors, NUM_SENSORS, avgTemperature, avgHumidity, numFailedSensors);

      JsonDocument payload;
      for (int i = 0; i < NUM_SENSORS; i++) {
        char key[10];
        snprintf(key, sizeof(key), "sensor_%d", i + 1);
        payload[key]["temperature"] = sensors[i].temperature;
        payload[key]["humidity"]    = sensors[i].humidity;
        payload[key]["valid"]       = sensors[i].valid;
        payload[key]["type"]        = "SHT45";
      }
      payload["average_temperature"] = avgTemperature;
      payload["average_humidity"]    = avgHumidity;
      payload["fan_status"]          = fanOn;
      payload["humidifier_status"]   = humidifierOn;
      payload["numFailedSensors"]    = numFailedSensors;
      payload["sensor_paused"]       = false;
      payload["heater_escalation"]   = heaterEscalationAlert;
      payload["heater_trigger_count"] = heaterTriggerCount;
      payload["ms_since_last_heater_trigger"] =
          (lastHeaterTriggerMillis == 0) ? -1 : (long)(now - lastHeaterTriggerMillis);

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

      printStatus(sensors, NUM_SENSORS, avgTemperature, avgHumidity, numFailedSensors);
    } else {
      // En pause de refroidissement : on garde les dernières valeurs
      // connues (avgTemperature/avgHumidity inchangées) et on informe le
      // serveur/LCD que les lectures sont temporairement suspendues.
      Serial.println(F("[PAUSE] lecture capteurs suspendue (refroidissement anti-condensation)"));

      JsonDocument payload;
      payload["average_temperature"] = avgTemperature;
      payload["average_humidity"]    = avgHumidity;
      payload["fan_status"]          = fanOn;
      payload["humidifier_status"]   = humidifierOn;
      payload["sensor_paused"]       = true;
      payload["heater_escalation"]   = heaterEscalationAlert;
      payload["heater_trigger_count"] = heaterTriggerCount;
      payload["ms_since_last_heater_trigger"] =
          (lastHeaterTriggerMillis == 0) ? -1 : (long)(now - lastHeaterTriggerMillis);

      String jsonPayload;
      serializeJson(payload, jsonPayload);

      if (!autonomousMode) {
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        shared.pendingPayload   = jsonPayload;
        shared.sensorDataReady  = true;
        xSemaphoreGive(stateMutex);
      }
    }
#endif
  }

  // Tâches secondaires d'affichage et boutons
  if (now - lastSlowTaskTime >= 50) {
    lastSlowTaskTime = now;

    // SECURITE : re-sonde la presence du PCF8574 regulierement. Si le
    // module est debranche en cours de route, pcf8574Connected repasse a
    // false et coupe immediatement la lecture des boutons/LEDs — un fil
    // arrache ne doit jamais pouvoir faire tourner le moteur tout seul.
    if (now - lastPcf8574CheckTime >= PCF8574_CHECK_INTERVAL) {
      lastPcf8574CheckTime = now;
      bool wasConnected = pcf8574Connected;
      pcf8574Connected = probePCF8574Presence();
      if (wasConnected && !pcf8574Connected) {
        Serial.println(F("ATTENTION: PCF8574 deconnecte du bus I2C — boutons/LEDs desactives."));
      } else if (!wasConnected && pcf8574Connected) {
        Serial.println(F("PCF8574 reconnecte — reinitialisation LEDs/boutons."));
        initLEDs();
        pcf8574.pinMode(BUTTON_STEPPER_PIN,    INPUT);
        pcf8574.pinMode(BUTTON_LCD_SCROLL_PIN, INPUT);
      }
    }

    checkStepperButton();
    checkLCDScrollButton();
    updateLCDScroll(now);
    updateStatusLEDs(avgTemperature, avgHumidity, serverConnected);
    displayStatusOnLCD(avgTemperature, avgHumidity);
  }

  delay(1);
}