# Schritt 5: Automatisierung (Windows Task Scheduler)

Wenn alle Tests erfolgreich waren, richten wir jetzt die
automatische Ausführung ein.

## Aufgabenplanung öffnen

1. **Windows-Taste** drücken
2. **"Aufgabenplanung"** eintippen und öffnen
   (oder: `taskschd.msc` in CMD)

## Task erstellen: Tägliches Update (13:30 Uhr)

### Allgemein
- Name: `SMARD BACnet Strompreis Update`
- Beschreibung: `Holt Strompreise von SMARD und schreibt sie in den BACnet Controller`
- ☑ "Unabhängig von der Benutzeranmeldung ausführen"
- ☑ "Mit höchsten Privilegien ausführen"

### Trigger
- **Neu...**
- Täglich, Startzeit: **13:30:00**
- Wiederholung: Keine (einmal pro Tag reicht)
- ☑ Aktiviert

### Aktionen
- **Neu...**
- Aktion: Programm starten
- Programm: `C:\smard-bacnet-gateway\venv\Scripts\python.exe`
- Argumente: `src/strompreis_bacnet.py --modus alle`
- Starten in: `C:\smard-bacnet-gateway`

### Bedingungen
- ☐ "Aufgabe nur starten, falls Computer im Netzbetrieb" → **DEAKTIVIEREN**
- ☐ "Aufgabe nur starten, falls Netzwerkverbindung" → **DEAKTIVIEREN**

### Einstellungen
- ☑ "Aufgabe so bald wie möglich nach einem verpassten Start ausführen"
- "Aufgabe beenden, falls Ausführung länger als:" → **5 Minuten**

## Optional: Stündliches Update (aktueller Preis)

Falls du den aktuellen Preis jede Stunde aktualisieren möchtest:

### Trigger
- Täglich, Startzeit: **00:05:00**
- ☑ Aufgabe wiederholen: Alle **1 Stunde**
- Dauer: **Unbegrenzt**

### Aktionen
- Programm: `C:\smard-bacnet-gateway\venv\Scripts\python.exe`
- Argumente: `src/strompreis_bacnet.py --modus aktuell`
- Starten in: `C:\smard-bacnet-gateway`

## Testen

1. In der Aufgabenplanung: Rechtsklick auf den Task → **"Ausführen"**
2. Log prüfen: `C:\smard-bacnet-gateway\logs\strompreis.log`
3. In enteliWEB prüfen: AV:1000 sollte aktuellen Preis zeigen

## Fertig!

Das System läuft jetzt automatisch. Bei Problemen:
- Log-Datei prüfen: `logs/strompreis.log`
- Verbindungstest: `python src/verbindungstest.py`
- Exit-Codes im Log geben Hinweise auf die Fehlerursache

| Exit-Code | Bedeutung                  | Was tun                          |
|-----------|----------------------------|----------------------------------|
| 0         | Alles OK                   | Nichts                           |
| 1         | Controller nicht erreichbar| Netzwerk/Firewall prüfen         |
| 2         | SMARD-API nicht erreichbar | Internet/Proxy prüfen            |
| 3         | Keine Preisdaten           | Zu früh? Feiertag? SMARD-Wartung?|
| 99        | Unerwarteter Fehler        | Log-Datei genau lesen            |
