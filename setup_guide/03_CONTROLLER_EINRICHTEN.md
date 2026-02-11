# Schritt 3: Controller einrichten

## Analog Values anlegen

Im Controller (via enteliWEB oder CopperCube) müssen **26 Analog
Values** angelegt werden:

| AV-Instanz | Name (Vorschlag)    | Beschreibung                   |
|------------|---------------------|---------------------------------|
| AV:1000    | Strompreis_Aktuell  | Preis der aktuellen Stunde      |
| AV:1001    | Preis_Morgen_00     | Morgen 00:00-01:00 Uhr          |
| AV:1002    | Preis_Morgen_01     | Morgen 01:00-02:00 Uhr          |
| AV:1003    | Preis_Morgen_02     | Morgen 02:00-03:00 Uhr          |
| ...        | ...                 | ...                             |
| AV:1023    | Preis_Morgen_22     | Morgen 22:00-23:00 Uhr          |
| AV:1024    | Preis_Morgen_23     | Morgen 23:00-00:00 Uhr          |
| AV:1025    | Preis_Status        | Watchdog (Anzahl Preise: 0-24)  |

### Einstellungen pro AV:

- **Object Type:** Analog Value
- **Units:** No Units (oder custom "ct/kWh")
- **Relinquish Default:** 0.0
- **Out of Service:** False
- **Wichtig:** Kein Override auf Priority 1-13!

### Was bedeutet der Fehlwert -1.0?

Wenn für eine Stunde kein Preis verfügbar ist (z.B. Feiertag oder
API-Problem), wird **-1.0** geschrieben. Deine Steuerungsprogramme
können darauf prüfen:

```
WENN Preis_Morgen_00 < 0 DANN
  → Kein gültiger Preis, Standard-Fahrplan nutzen
```

## Weiter mit → [Schritt 4: Erster Test](04_ERSTER_TEST.md)
