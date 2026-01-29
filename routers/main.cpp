
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
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

// WiFi credentials
const char* ssid = "Airbox-4D56";
const char* password = "16017581";

// Server configuration
const char* serverIP = "192.168.1.100";  // Remplacer par l'IP du serveur
const int serverPort = 5000;
const char* apiKey = "Votre_Cle_API";

// Thresholds for backup mode
const float TEMP_THRESHOLD = 37.7;
const float HUMIDITY_THRESHOLD = 45.0;

// Timing
const unsigned long SEND_INTERVAL = 5000;  // 5 secondes

// ============== OBJETS GLOBAUX ==============

DHT dht_1(DHT_1_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_2(DHT_2_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_3(DHT_3_PIN_DATA, DHT_SENSOR_TYPE);
DHT dht_4(DHT_4_PIN_DATA, DHT_SENSOR_TYPE);

AccelStepper stepper(AccelStepper::FULL4WIRE, STEPPER_PIN_1, STEPPER_PIN_2);

// ============== VARIABLES D'ÉTAT ==============

bool fanOn = false;
bool humidifierOn = false;

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

bool sendDataToServer(const String& jsonPayload) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi non connecte");
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
    }
  } else {
    Serial.printf("Erreur POST: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
  return httpCode > 0;
}

bool getCommandsFromServer() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  String url = buildServerUrl("/sensor/values") + "?api_key=" + String(apiKey);
  http.begin(url);

  int httpCode = http.GET();

  if (httpCode == 200 || httpCode == 202) {
    String response = http.getString();
    Serial.println("Commandes recues: " + response);

    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);

    if (!error) {
      // Motor control
      const char* motorStatus = doc["Motor"] | "OFF";
      if (strcmp(motorStatus, "ON") == 0) {
        stepper.moveTo(200);
        stepper.setSpeed(100);
        stepper.runToPosition();
      } else {
        stepper.setSpeed(0);
        stepper.setCurrentPosition(0);
      }

      // Fan control
      const char* fanStatus = doc["FAN"] | "OFF";
      if (strcmp(fanStatus, "ON") == 0) {
        digitalWrite(FAN_PIN, HIGH);
        fanOn = true;
      } else {
        digitalWrite(FAN_PIN, LOW);
        fanOn = false;
      }

      // Humidifier control
      const char* humidStatus = doc["Humidity"] | "OFF";
      if (strcmp(humidStatus, "ON") == 0) {
        digitalWrite(HUMIDIFIER_PIN, HIGH);
        humidifierOn = true;
      } else {
        digitalWrite(HUMIDIFIER_PIN, LOW);
        humidifierOn = false;
      }

      http.end();
      return true;
    } else {
      Serial.println("Erreur parsing JSON");
    }
  } else {
    Serial.printf("GET /getdata - Erreur: %d\n", httpCode);
  }

  http.end();
  return false;
}

void applyBackupLogic(float avgTemp, float avgHumid) {
  Serial.println("Mode autonome - Logique de secours");

  // Fan control based on temperature
  if (avgTemp > 0 && avgTemp > TEMP_THRESHOLD) {
    digitalWrite(FAN_PIN, HIGH);
    fanOn = true;
  } else {
    digitalWrite(FAN_PIN, LOW);
    fanOn = false;
  }

  // Humidifier control based on humidity
  if (avgHumid > 0 && avgHumid < HUMIDITY_THRESHOLD) {
    digitalWrite(HUMIDIFIER_PIN, HIGH);
    humidifierOn = true;
  } else {
    digitalWrite(HUMIDIFIER_PIN, LOW);
    humidifierOn = false;
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

  // Send data to server
  sendDataToServer(jsonPayload);

  // Get commands from server or use backup logic
  if (!getCommandsFromServer()) {
    applyBackupLogic(avgTemperature, avgHumidity);
  }

  // Print status
  printStatus(sensors, 4, avgTemperature, avgHumidity, numFailedSensors);

  // Run stepper if needed
  while (stepper.isRunning()) {
    stepper.run();
  }

  // Wait before next iteration
  delay(SEND_INTERVAL);
}
