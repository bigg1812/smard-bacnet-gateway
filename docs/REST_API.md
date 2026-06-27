# REST-API Weg (enteliWEB)

Neben dem klassischen Weg über rohe BACnet/IP-Pakete
([`src/strompreis_bacnet.py`](src/strompreis_bacnet.py)) gibt es jetzt einen
zweiten Weg, der Werte über die **enteliWEB REST-API** schreibt –
ohne dass der PC selbst BACnet sprechen muss.

```
 ┌────────────┐   ┌─────────────┐   ┌──────────┐        ┌─────────────────┐
 │  SMARD API │   │ Open-Meteo  │   │  Python  │ HTTP   │   enteliWEB     │ BACnet
 │ Strompreis │──▶│   Wetter    │──▶│ gateway_ │───────▶│   Web-API       │──────▶ Controller
 │            │   │             │   │ rest.py  │ PUT    │  (lizenziert)   │        AV/BV
 └────────────┘   └─────────────┘   └──────────┘        └─────────────────┘
```

## Wann diesen Weg nutzen?

| | Raw BACnet (`src/strompreis_bacnet.py`) | REST-API (`src/rest_api/`) |
|---|---|---|
| Transport | UDP-Pakete selbst bauen | HTTP PUT |
| Netzwerk | PC muss im BACnet-Subnetz sein | nur HTTP zum enteliWEB-Server |
| Voraussetzung | nichts extra | **enteliWEB mit lizenzierter Web-API** |
| Datenquellen | nur Strompreis | Strompreis **und** Wetter |

> **Der gesamte REST-Weg liegt im Ordner [`src/rest_api/`](src/rest_api/).**
> Der klassische BACnet-Weg (`src/strompreis_bacnet.py`) bleibt davon unberührt.

## Architektur

```
src/
  strompreis_bacnet.py    ← klassischer Weg: rohes BACnet/IP (unverändert)
  verbindungstest.py      ← BACnet-Verbindungstest (unverändert)
  rest_api/               ← NEU: der komplette REST-API-Weg
    gateway_rest.py       Orchestrator: Config → Quellen → Werte → schreiben
    enteliweb.py          REST-Writer: HTTP PUT/GET an die enteliWEB-API
    sources/
      smard.py            Strompreise (SMARD, kostenlos)
      openmeteo.py        Wetterprognose (Open-Meteo, kostenlos, kein Key)
```

Prinzip: **Jede Quelle liefert nur Zahlen.** Der Writer macht daraus HTTP-Requests.
Eine neue Quelle dazubauen = neues Modul in `src/rest_api/sources/` + Config-Abschnitt,
ohne den REST-Code anzufassen.

## Konfiguration

Alle Einstellungen in [`config/einstellungen.ini`](config/einstellungen.ini),
Abschnitte `[enteliweb]`, `[quellen]`, `[strompreis_objekte]`,
`[wetter_api]`, `[wetter_objekte]`.

```ini
[enteliweb]
host    = DEIN_ENTELIWEB_SERVER
benutzer = DEIN_BENUTZER
passwort = DEIN_PASSWORT
site    = DEINE_SITE
device  = 1234
dry_run = ja          ; ja = nur loggen (sicher), nein = wirklich schreiben

[quellen]
strompreis = an
wetter     = an

[wetter_objekte]
temperature_2m      = analog-value,1010
shortwave_radiation = analog-value,1011
```

## Ausführen

```bash
# Verbindung prüfen (read-only) – steht die HTTP-Strecke? Existieren die Objekte?
# Ideal als ERSTER Schritt, besonders wenn IPC und Controller in getrennten Netzen sind:
python src/rest_api/gateway_rest.py --check

# Sicher testen – sendet NICHTS, loggt nur die geplanten Requests:
python src/rest_api/gateway_rest.py

# Nur eine Quelle:
python src/rest_api/gateway_rest.py --modus preis
python src/rest_api/gateway_rest.py --modus wetter

# Wirklich schreiben (überschreibt dry_run):
python src/rest_api/gateway_rest.py --live
```

## Sicherheit

1. **Immer zuerst im Dry-Run** prüfen, welche Objekte beschrieben würden.
2. Erst gegen **ungenutzte Test-Objekte** schreiben, nie gegen produktive Anlagen.
3. **Priority bewusst** wählen (14 lässt manuelle Übersteuerung im Controller zu).
4. Schreiben auf eine echte Anlage braucht **Betreiberfreigabe** und idealerweise HTTPS.
