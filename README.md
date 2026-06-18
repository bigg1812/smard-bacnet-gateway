# SMARD-BACnet Gateway

**Strompreise aus dem Internet direkt in die Gebäudeautomation bringen.**

Dieses Tool holt automatisch **Day-Ahead Strompreise** von der
öffentlichen API der Bundesnetzagentur (SMARD) und schreibt sie
via **BACnet/IP** in einen Gebäudeautomations-Controller.

```
                                          ┌─────────────────┐
 ┌────────────┐   Internet    ┌────────┐  │  BACnet         │
 │  SMARD API │ ─────────────►│ Python │──│  Controller     │
 │  (Bundes-  │  Strompreise  │ Skript │  │  (z.B. EBcon)   │
 │  netzagen- │  EUR/MWh      │        │  │                 │
 │  tur)      │               │  PC    │  │  AV:1000 = 11.67│
 └────────────┘               └────────┘  │  BV:1025 = 1    │
                                          └─────────────────┘
```

## Was macht das Tool?

1. **Ruft Strompreise ab** von der SMARD-Plattform der Bundesnetzagentur
2. **Schreibt den aktuellen Preis** in ein konfigurierbares Analog Value (z.B. `AV:1000`)
3. **Schreibt den Status für morgen** (ob Preise für morgen vorliegen und das System ok ist) in ein Binary Value (z.B. `BV:1025`)

Die Preise stehen dann im Controller für Steuerungsprogramme zur
Verfügung – z.B. um ein BHKW, Wärmepumpen oder Batteriespeicher zu optimieren.

## Schnellstart

> **Detaillierte Anleitung mit Screenshots:**
> Siehe [`setup_guide/`](setup_guide/01_VORBEREITUNG.md)

```powershell
# 1. Repository herunterladen
git clone https://github.com/DEIN-NAME/smard-bacnet-gateway.git
cd smard-bacnet-gateway

# 2. Python-Umgebung einrichten
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Konfiguration anpassen (IP-Adressen und AV-Nummern!)
notepad config\einstellungen.ini

# 4. Verbindung testen
python src/verbindungstest.py

# 5. Strompreise abrufen
python src/strompreis_bacnet.py
```

## Voraussetzungen

| Was                    | Mindestanforderung              |
|------------------------|---------------------------------|
| Betriebssystem         | Windows 10/11 oder Windows Server |
| Python                 | 3.10 oder neuer                 |
| Controller             | Jeder BACnet/IP Controller      |
| Netzwerk               | PC und Controller im selben Subnetz |
| Internet               | Für SMARD-API (HTTPS)           |

## Projektstruktur

```
smard-bacnet-gateway/
├── README.md                   ← Diese Datei
├── LICENSE                     ← MIT Lizenz
├── requirements.txt            ← Python-Abhängigkeiten
├── config/
│   └── einstellungen.ini       ← Alle Einstellungen (MUSS angepasst werden!)
├── src/
│   ├── strompreis_bacnet.py    ← Hauptskript
│   └── verbindungstest.py      ← Verbindungstest
├── setup_guide/
│   ├── 01_VORBEREITUNG.md      ← Was du brauchst
│   ├── 02_INSTALLATION.md      ← Schritt-für-Schritt Installation
│   ├── 03_CONTROLLER_EINRICHTEN.md ← AVs im Controller anlegen
│   ├── 04_ERSTER_TEST.md       ← Testen ob alles funktioniert
│   └── 05_AUTOMATISIERUNG.md   ← Windows Task einrichten
└── logs/
    └── strompreis.log          ← Wird automatisch erstellt
```

## Konfiguration

> **⚠️ WICHTIG:** Vor der ersten Nutzung **MUSS** die Datei [`config/einstellungen.ini`](config/einstellungen.ini) angepasst werden!
> 
> **📖 Detaillierte Schritt-für-Schritt-Anleitung:** [KONFIGURATION.md](KONFIGURATION.md)

Die Konfigurationsdatei enthält Platzhalter, die du durch deine echten Werte ersetzen musst:

```ini
[netzwerk]
controller_ip = 192.168.1.100   ← Ersetze durch IP deines Controllers
local_ip      = 192.168.1.50    ← Ersetze durch IP deines PCs

[bacnet_objekte]
av_aktuell      = 1000          ← Ersetze durch deine AV-Instanznummer
bv_status       = 1025          ← Ersetze durch deine BV-Instanznummer

[einheiten]
faktor = 0.1                    ← 0.1 = ct/kWh, 1.0 = EUR/MWh
```

**Du benötigst:**
- ✅ Die IP-Adresse deines BACnet-Controllers
- ✅ Die IP-Adresse des PCs auf dem das Skript läuft
- ✅ 1 freie AV-Instanznummer und 1 freie BV-Instanznummer im Controller

**Wo finde ich diese Informationen?** → Siehe [KONFIGURATION.md](KONFIGURATION.md)

## SMARD-Datenquelle

Die Daten stammen von [SMARD](https://www.smard.de) – der
Strommarkt-Plattform der Bundesnetzagentur. Die API ist
**öffentlich zugänglich**, kostenlos und benötigt **keinen API-Key**.

### Verfügbare Daten (Auszug)

| Typ              | Filter-ID | Beschreibung              |
|------------------|-----------|---------------------------|
| **Strompreise**  |           |                           |
|                  | 4169      | Day-Ahead Großhandelspreis|
|                  | 5078      | Intraday Durchschnitt     |
| **Erzeugung**    |           |                           |
|                  | 4068      | Photovoltaik              |
|                  | 4067      | Wind Onshore              |
|                  | 1225      | Wind Offshore             |
|                  | 4071      | Erdgas                    |
| **Verbrauch**    |           |                           |
|                  | 410       | Netzlast (Gesamt)         |
|                  | 4359      | Residuallast              |

Die vollständige Liste steht in der `einstellungen.ini`.

## Fehlerbehebung

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| Verbindungstest: Timeout | Firewall | [Schritt 4](setup_guide/04_ERSTER_TEST.md) |
| "Keine Preise für morgen" | Vor 13:00 ausgeführt | Um 13:30 nochmal starten |
| Port belegt | Vorherige Instanz läuft | Prozess beenden oder Port ändern |
| AV ändert sich nicht | Höhere Priority aktiv | Priority Array im Controller prüfen |
| Preis = -1.0 im Controller | Kein SMARD-Preis für diese Stunde | Normal an manchen Feiertagen |

## Lizenz

MIT License – siehe [LICENSE](LICENSE)

## Datenquelle

[SMARD – Strommarktdaten](https://www.smard.de)  
Bundesnetzagentur, öffentlich zugänglich.

## Anpassungen für dein Projekt

Bevor du das Repository verwendest, passe folgende Dateien an:

1. **`config/einstellungen.ini`** – Alle IP-Adressen und AV-Nummern
2. **`setup_guide/02_INSTALLATION.md`** – Pfade falls du einen anderen Installationsort wählst
3. **`setup_guide/05_AUTOMATISIERUNG.md`** – Task Scheduler Pfade anpassen
