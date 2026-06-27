# Methode B – enteliWEB REST-API

Schreibt SMARD-Strompreise (und optional Open-Meteo-Wetter) über die
**enteliWEB Web-API** (HTTP) in BACnet-Objekte. Kein direktes BACnet/IP nötig.

**Voraussetzung:** enteliWEB-Server mit **lizenzierter Web-API**.

---

## 1. Einrichten

1. Abhängigkeiten (vom Repo-Wurzelordner):
   ```cmd
   python -m pip install -r ..\requirements.txt
   ```
   Im Firmennetz mit TLS-Proxy zusätzlich:
   ```cmd
   python -m pip install pip-system-certs
   ```
2. `config/einstellungen.ini` öffnen und ausfüllen:
   - **`[enteliweb]`** – `host`, `benutzer`, `passwort`, `site`, `device`
   - **`[strompreis_objekte]`** – Ziel-Objekt(e), z. B. `av_aktuell = analog-value,1000`
   - **`[smard_api]`** – `aufloesung = quarterhour` (15-Min-Preise) oder `hour`
   - **`[wetter_api]` / `[wetter_objekte]`** – nur falls Wetter gewünscht

> `dry_run = ja` (Standard) schreibt **nichts**, sondern loggt nur. Zum echten
> Schreiben `dry_run = nein` setzen **oder** das Skript mit `--live` starten.

## 2. Verbindung & Ziel-Objekte prüfen (schreibt nichts)

```cmd
python src\gateway_rest.py --check
```
Prüft enteliWEB-Erreichbarkeit, Auth/Lizenz und ob alle Ziel-Objekte lesbar
sind. Ergebnis z. B. „3/3 Objekte ok" + Exit-Code 0.

## 3. Ausführen

```cmd
python src\gateway_rest.py            (alle aktiven Quellen, Dry-Run)
python src\gateway_rest.py --live     (wirklich schreiben)
python src\gateway_rest.py --modus preis    (nur Strompreis)
python src\gateway_rest.py --modus wetter    (nur Wetter)
```

Logs landen in `logs/gateway_rest.log` (rotierend).

## 4. Automatisieren (Windows-Aufgabenplanung)

Beispiel: alle 15 Minuten, läuft auch ohne Anmeldung (stabil für Server/VM):

```cmd
schtasks /Create /TN "SMARD Strompreis" ^
  /TR "cmd /c <PFAD-ZU-PYTHON> <PFAD>\methode-rest-api\src\gateway_rest.py --modus preis --live >> <PFAD>\methode-rest-api\logs\task_debug.log 2>&1" ^
  /SC MINUTE /MO 15 /ST 00:02 /RU <konto> /RP * /RL HIGHEST /F
```

Hinweise:
- **`/RU <konto> /RP *`** = „unabhängig von der Anmeldung". Der Modus
  **„Nur interaktiv" startet auf manchen Systemen gar nichts** – diese Variante
  ist zuverlässiger.
- Pfade **ohne** Leerzeichen brauchen keine inneren Anführungszeichen.
- `cmd /c … >> task_debug.log 2>&1` fängt auch Abstürze **vor** dem Logging ab.
- Bei `aufloesung = quarterhour` den Task alle **15 Min** laufen lassen.

## Dateien

| Datei | Zweck |
|---|---|
| `src/gateway_rest.py` | Hauptprogramm (Quellen → enteliWEB REST) |
| `src/enteliweb.py` | HTTP-Client für die enteliWEB-API |
| `src/sources/smard.py` | SMARD-Strompreise (Stunde/Viertelstunde, mit Retry) |
| `src/sources/openmeteo.py` | Open-Meteo-Wetterprognose |
| `config/einstellungen.ini` | Konfiguration (Vorlage) |
