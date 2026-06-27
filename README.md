# SMARD-BACnet Gateway

**Strompreise (und Wetter) aus dem Internet in die Gebäudeautomation bringen.**

Dieses Projekt holt automatisch **Day-Ahead-Strompreise** von der öffentlichen
API der Bundesnetzagentur (**SMARD**) – optional auch Wetterdaten von
**Open-Meteo** – und schreibt die Werte in **BACnet-Objekte** eines
Gebäudeautomations-Controllers.

Es gibt **zwei Methoden**, das ins BACnet zu schreiben. Wähle **eine** davon
aus – jede liegt in einem eigenen Ordner mit eigener Konfiguration:

| Methode | Ordner | Wann nutzen? |
|---|---|---|
| **A – BACnet/IP direkt** | [`methode-bacnet-direkt/`](methode-bacnet-direkt/) | Du sprichst den Controller **direkt** per BACnet/IP (UDP, Port 47808) an. Kein enteliWEB nötig. |
| **B – enteliWEB REST-API** | [`methode-rest-api/`](methode-rest-api/) | Du schreibst über die **enteliWEB Web-API** (HTTP). Kein direktes BACnet/IP nötig, dafür enteliWEB mit lizenzierter API. Unterstützt zusätzlich Wetter. |

> **Kurz:** Hast du enteliWEB mit Web-API? → **Methode B**.
> Willst/must du direkt aufs BACnet/IP-Netz? → **Methode A**.

Beide Methoden sind **unabhängig** voneinander – du brauchst nur den Ordner der
gewählten Methode. Jede hat ihre eigene `README.md` mit Schritt-für-Schritt-Anleitung.

---

## Schnellstart

1. **Python 3.10+** installieren.
2. Abhängigkeiten installieren:
   ```cmd
   python -m pip install -r requirements.txt
   ```
   (Im Firmennetz mit TLS-Proxy zusätzlich: `python -m pip install pip-system-certs`)
3. Methode wählen, in deren Ordner wechseln und die dortige **`README.md`** befolgen:
   - `methode-bacnet-direkt/` → BACnet/IP direkt
   - `methode-rest-api/` → enteliWEB REST-API

---

## Projektstruktur

```
smard-bacnet-gateway/
├─ methode-bacnet-direkt/     Methode A: BACnet/IP direkt (UDP)
│  ├─ config/einstellungen.ini
│  └─ src/  (strompreis_bacnet.py, verbindungstest.py)
│
├─ methode-rest-api/          Methode B: enteliWEB REST-API
│  ├─ config/einstellungen.ini
│  └─ src/  (gateway_rest.py, enteliweb.py, sources/)
│
├─ extras/                    Optionale CSV-Exporter (kein BACnet)
│  ├─ strompreis-csv/
│  └─ wetter-csv/
│
├─ docs/                      Ausführliche Doku & Setup-Guide
└─ requirements.txt           Gemeinsame Python-Abhängigkeiten
```

---

## Wichtige Hinweise

- **Konfiguration:** Jede `config/einstellungen.ini` ist eine **Vorlage mit
  Platzhaltern**. Trage deine echten Werte ein – aber **committe keine echten
  Zugangsdaten/IP-Adressen** (steht so in der `.gitignore`-Notiz).
- **Automatisierung** (alle 15 Min / stündlich) per Windows-Aufgabenplanung:
  siehe [`docs/setup_guide/05_AUTOMATISIERUNG.md`](docs/setup_guide/05_AUTOMATISIERUNG.md)
  und die README der jeweiligen Methode.

## Lizenz

Siehe [LICENSE](LICENSE).
