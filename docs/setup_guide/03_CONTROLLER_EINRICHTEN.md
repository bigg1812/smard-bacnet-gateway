# Schritt 3: Controller einrichten

## BACnet-Objekte anlegen

Im Controller (via enteliWEB oder CopperCube) müssen **1 Analog Value (AV)** und **1 Binary Value (BV)** angelegt werden:

| Objekt-Instanz | Name (Vorschlag)    | Beschreibung                                               |
|----------------|---------------------|------------------------------------------------------------|
| AV:1000        | Strompreis_Aktuell  | Preis der aktuellen Stunde (Analog Value)                  |
| BV:1025        | Strompreis_Status   | Watchdog/Status (Binary Value, 1 = Ok/Aktiv, 0 = Fehler)   |

### Einstellungen pro Objekt:

- **AV:1000 (Analog Value):**
  - **Object Type:** Analog Value
  - **Units:** No Units (oder custom "ct/kWh")
  - **Relinquish Default:** 0.0
  - **Out of Service:** False
  - **Wichtig:** Kein Override auf Priority 1-13!

- **BV:1025 (Binary Value):**
  - **Object Type:** Binary Value
  - **Relinquish Default:** 0 (Inactive)
  - **Out of Service:** False
  - **Wichtig:** Kein Override auf Priority 1-13!

### Was bedeutet der Fehlwert -1.0?

Wenn für den aktuellen Preis kein Wert verfügbar ist (z.B. bei API-Problemen), wird **-1.0** auf das AV geschrieben. Deine Steuerungsprogramme können darauf prüfen:

```
WENN Strompreis_Aktuell < 0 DANN
  → Kein gültiger Preis, Standard-Fahrplan nutzen
```

## Weiter mit → [Schritt 4: Erster Test](04_ERSTER_TEST.md)
