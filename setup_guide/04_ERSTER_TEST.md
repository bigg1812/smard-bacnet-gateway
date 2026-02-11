# Schritt 4: Erster Test

## 1. Verbindungstest

Prüft ob der Controller erreichbar ist und BACnet funktioniert.

```
cd C:\smard-bacnet-gateway
venv\Scripts\activate
python src/verbindungstest.py
```

**Erwartete Ausgabe:**
```
=======================================================
  SMARD-BACnet Gateway – Verbindungstest
=======================================================
  Controller:  192.168.244.30:47808
  Lokaler PC:  192.168.244.10:47809
  Test-Objekt: AV:1000

[1/4] Ping... OK
[2/4] UDP-Socket oeffnen (Port 47809)... OK
[3/4] Lese AV:1000... OK (Wert: 11.67)
[4/4] Schreibe 88.88 auf AV:1000... OK (SimpleACK)

-------------------------------------------------------
  ERFOLG! AV:1000 = 88.88
  Die Verbindung funktioniert einwandfrei.
-------------------------------------------------------
```

### Fehlerbehebung

**"TIMEOUT – Keine Antwort":**

Die Windows Firewall blockiert vermutlich eingehende UDP-Pakete.
Öffne CMD **als Administrator** und führe aus:

```
netsh advfirewall firewall add rule name="BACnet Gateway UDP" dir=in action=allow protocol=UDP localport=47809
```

Danach den Test wiederholen.

**"Port belegt":**

Ein anderes Programm (oder eine vorherige Instanz des Skripts)
nutzt den Port. Entweder:
- Das andere Programm beenden
- Oder in `config/einstellungen.ini` den `local_port` ändern
  (z.B. auf 47810)

## 2. Strompreis-Test (nur aktueller Preis)

```
python src/strompreis_bacnet.py --modus aktuell
```

**Erwartete Ausgabe:**
```
Aktueller Preis: 116.70 EUR/MWh = 11.67 ct/kWh (11.02.2025 14:00)
AV:1000 = 11.67 ct/kWh
```

Prüfe in enteliWEB: AV:1000 sollte jetzt 11.67 anzeigen.

## 3. Morgen-Preise testen

```
python src/strompreis_bacnet.py --modus morgen
```

**Hinweis:** Morgen-Preise sind erst ab ca. 13:00 Uhr verfügbar!
Vorher kommt die Meldung "KEINE Preise fuer morgen".

## 4. Alles zusammen

```
python src/strompreis_bacnet.py
```

## Weiter mit → [Schritt 5: Automatisierung](05_AUTOMATISIERUNG.md)
