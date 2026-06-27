# Methode A – BACnet/IP (direkt)

Schreibt SMARD-Strompreise **direkt per BACnet/IP** (UDP, Port 47808) in einen
Controller. Kein enteliWEB nötig – das Skript spricht das BACnet-Netz selbst an.

---

## 1. Einrichten

1. Abhängigkeiten (vom Repo-Wurzelordner):
   ```cmd
   python -m pip install -r ..\requirements.txt
   ```
2. `config/einstellungen.ini` öffnen und ausfüllen:
   - **`[netzwerk]`** – `controller_ip`, `local_ip`, Ports
     (`local_port` **nicht** 47808, falls auf dem PC schon BACnet-Software läuft)
   - **`[bacnet_objekte]`** – `av_aktuell` (Instanz für den Preis), `bv_status`, `priority`
   - **`[smard_api]` / `[einheiten]`** – Datenquelle und Umrechnung

## 2. Verbindung testen (nur Lesen/Schreiben-Test, keine SMARD-Daten)

```cmd
python src\verbindungstest.py
```
Prüft, ob der Controller über BACnet/IP erreichbar ist.

## 3. Ausführen

```cmd
python src\strompreis_bacnet.py                 (alles)
python src\strompreis_bacnet.py --modus aktuell (nur aktueller Preis)
python src\strompreis_bacnet.py --modus morgen  (nur 24h Morgen-Preise)
```

Logs landen in `logs/` (rotierend).

## 4. Automatisieren (Windows-Aufgabenplanung)

Beispiel: stündlich, läuft auch ohne Anmeldung:

```cmd
schtasks /Create /TN "SMARD BACnet" ^
  /TR "cmd /c <PFAD-ZU-PYTHON> <PFAD>\methode-bacnet-direkt\src\strompreis_bacnet.py --modus aktuell >> <PFAD>\methode-bacnet-direkt\logs\task_debug.log 2>&1" ^
  /SC HOURLY /RU <konto> /RP * /RL HIGHEST /F
```

> Tipp: Modus **„unabhängig von der Anmeldung"** (`/RU /RP`) nutzen – der Modus
> „Nur interaktiv" startet auf manchen Systemen gar nichts.

## Dateien

| Datei | Zweck |
|---|---|
| `src/strompreis_bacnet.py` | Hauptprogramm (SMARD → BACnet/IP direkt) |
| `src/verbindungstest.py` | BACnet-Verbindungstest |
| `config/einstellungen.ini` | Konfiguration (Vorlage) |
