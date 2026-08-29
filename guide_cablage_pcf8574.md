# Guide de câblage — PCF8574 (LEDs + boutons)

Applicable aux deux boîtiers (main.cpp / main_sht30.cpp) — même expander, même logique, adresses I2C à vérifier selon le bus.

---

## 1. Brochage du PCF8574T

| Pin PCF8574 | Fonction firmware | Broche # (code) |
|---|---|---|
| P0 | LED verte | `LED_GREEN_PIN` = 0 |
| P1 | LED orange | `LED_ORANGE_PIN` = 1 |
| P2 | LED rouge | `LED_RED_PIN` = 2 |
| P3 | LED bleue | `LED_BLUE_PIN` = 3 |
| P4 | Bouton stepper (manuel) | `BUTTON_STEPPER_PIN` = 4 |
| P5 | Bouton scroll LCD | `BUTTON_LCD_SCROLL_PIN` = 5 |
| P6 | Libre | — |
| P7 | Libre | — |

| Alimentation PCF8574 | Connexion |
|---|---|
| VCC | 5V (rail logique) |
| GND | Masse commune (star ground) |
| SDA | Bus I2C — GPIO21 (ESP32) |
| SCL | Bus I2C — GPIO22 (ESP32) |
| A0, A1, A2 | GND (→ adresse 0x20 par défaut) — voir section 4 si conflit |
| INT | Non câblé (optionnel, non utilisé par le firmware actuel) |

---

## 2. Câblage des 4 LEDs (montage actif-bas, LED 3V)

Chaque LED s'allume quand le firmware écrit **0** sur sa pin (le PCF8574 "sink" le courant vers GND).

```
+5V ──── Résistance série ──── Anode LED
                                   │
                                Cathode LED
                                   │
                              Pin PCF8574 (P0-P3)
```

**Calcul résistance** (Vf LED ≈ 3V, courant cible 10-15mA) :

```
R = (5V − 3V) / 0.012A ≈ 167Ω → utiliser 150Ω ou 220Ω (valeurs standard)
```

| LED | Pin | Résistance |
|---|---|---|
| Verte | P0 | 150-220Ω |
| Orange | P1 | 150-220Ω |
| Rouge | P2 | 150-220Ω |
| Bleue | P3 | 150-220Ω (si LED bleue Vf ≈ 3.2-3.4V, vérifier marge — 220Ω recommandé) |

**Attention** : courant max absolu par pin du PCF8574 ≈ 25mA — ne jamais descendre sous ~130Ω même en dépannage rapide.

---

## 3. Câblage des 2 boutons poussoirs

```
Pin PCF8574 (P4 ou P5) ──── Bouton poussoir ──── GND
```

- Pull-up interne faible du PCF8574 activée par `pinMode(pin, INPUT)` dans le firmware — suffisant dans la majorité des cas.
- Si rebond ou lecture instable observée (câble long, bruit électrique) : ajouter une résistance pull-up externe 10kΩ entre la pin et le +5V, en complément.
- Pas de condensateur anti-rebond nécessaire — le debounce est géré en logiciel (200ms + confirmation 20ms).

| Bouton | Pin |
|---|---|
| Stepper manuel | P4 |
| Scroll LCD | P5 |

---

## 4. Partage du bus I2C avec le LCD (et le TCA9548A côté boîtier 2)

Le PCF8574 partage le même bus SDA/SCL que le LCD (et le TCA9548A + SHT45 sur le boîtier 2). Chaque device doit avoir une adresse distincte.

| Device | Adresse par défaut | Boîtier |
|---|---|---|
| LCD I2C | 0x27 (ou 0x3F selon module) | 1 et 2 |
| PCF8574T | 0x20 (A0=A1=A2=GND) | 1 et 2 |
| TCA9548A | 0x70 | 2 uniquement |

Adresse 0x20 du PCF8574 ne rentre pas en conflit avec 0x27/0x3F (LCD) ni 0x70 (TCA9548A) — câblage A0/A1/A2 à GND suffit, pas de jumper à modifier.

**Si tu ajoutes un 2e PCF8574 plus tard** (ex: pour le potentiomètre ou d'autres GPIO) : décale son adresse via A0-A2 (0x21 à 0x27 disponibles).

---

## 5. Vérification avant mise sous tension

- [ ] VCC du PCF8574 sur 5V (pas 3.3V — le module standard T fonctionne en logique 5V)
- [ ] A0, A1, A2 reliés à GND (adresse 0x20 confirmée)
- [ ] Chaque LED câblée en actif-bas avec résistance série correcte
- [ ] Chaque bouton câblé entre sa pin et GND (pas de résistance en série côté bouton)
- [ ] SDA/SCL du PCF8574 sur le même bus que le LCD, adresses non conflictuelles
- [ ] Masse du PCF8574 reliée au point de star ground commun

## 6. Test rapide au premier boot

Au démarrage, le firmware log `"ATTENTION: PCF8574 (LEDs/boutons) non detecte!"` sur le port série si l'expander ne répond pas à l'adresse 0x20 — signe d'un défaut de câblage SDA/SCL/VCC/GND ou d'une adresse mal configurée. Si ce message apparaît, vérifier au multimètre la continuité SDA/SCL avant de réessayer.
