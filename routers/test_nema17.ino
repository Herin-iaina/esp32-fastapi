/*
  Test NEMA17 minimal pour ESP32 + driver step/dir (A4988, DRV8825...)

  Connexions suggérées (ESP32 GPIO):
    STEP  -> 26
    DIR   -> 27
    ENABLE-> 14  (optionnel, LOW = enabled pour la plupart des drivers)

  Usage:
    - Ajuster les constantes ci-dessous si nécessaire.
    - Téléverser le sketch avec l'Arduino IDE ou PlatformIO.
    - Ouvrir le Moniteur Série à 115200 bauds pour suivre les étapes.
*/

const int STEP_PIN = 26;
const int DIR_PIN = 27;
const int ENABLE_PIN = 14;

// Paramètres moteur/driver
const int STEPS_PER_REV = 200; // pas plein par révolution pour NEMA17 standard
const int MICROSTEP = 1;       // 1 = full step, 2 = half, 16 = 1/16, etc.
const int RPM = 60;            // vitesse cible en tours/min

unsigned long computeStepDelayMicros() {
  float stepsPerMin = (float)STEPS_PER_REV * (float)MICROSTEP * (float)RPM;
  float stepsPerSec = stepsPerMin / 60.0;
  if (stepsPerSec <= 0.0) return 1000;
  float delayMicros = 1000000.0 / stepsPerSec;
  return (unsigned long)delayMicros;
}

void stepPulse(unsigned long halfPeriodMicros) {
  digitalWrite(STEP_PIN, HIGH);
  delayMicroseconds(halfPeriodMicros);
  digitalWrite(STEP_PIN, LOW);
  delayMicroseconds(halfPeriodMicros);
}

void moveSteps(long steps, unsigned long fullPeriodMicros) {
  if (steps == 0) return;
  digitalWrite(DIR_PIN, steps > 0 ? HIGH : LOW);
  unsigned long half = fullPeriodMicros / 2;
  unsigned long n = (unsigned long)abs(steps);
  for (unsigned long i = 0; i < n; ++i) {
    stepPulse(half);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  // Activer le driver (LOW est généralement enable pour A4988/DRV8825)
  digitalWrite(ENABLE_PIN, LOW);
  digitalWrite(STEP_PIN, LOW);
  digitalWrite(DIR_PIN, LOW);
  Serial.println("Test NEMA17 démarré");
}

void loop() {
  unsigned long period = computeStepDelayMicros();
  long stepsPerRev = (long)STEPS_PER_REV * (long)MICROSTEP;

  Serial.println("Avance: 1 tour");
  moveSteps(stepsPerRev, period);
  delay(500);

  Serial.println("Recule: 1 tour");
  moveSteps(-stepsPerRev, period);
  delay(1000);
}
