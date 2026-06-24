# Schritt 2: Installation

## Repository herunterladen

### Option A: Mit Git (empfohlen)
```
cd C:\
git clone https://github.com/DEIN-NAME/smard-bacnet-gateway.git
cd smard-bacnet-gateway
```

### Option B: Als ZIP
1. Auf GitHub → grüner Button **"Code"** → **"Download ZIP"**
2. ZIP entpacken nach `C:\smard-bacnet-gateway\`
3. CMD öffnen:
```
cd C:\smard-bacnet-gateway
```

## Virtuelle Umgebung erstellen

Eine virtuelle Umgebung hält die Python-Pakete getrennt vom
System. Das verhindert Konflikte.

### Vorher prüfen: Funktioniert Python wirklich?

Bevor du die virtuelle Umgebung erstellst, prüfe in CMD noch einmal:

```cmd
python --version
```

Falls das nicht funktioniert:

```cmd
py --version
where python
where py
```

Erwartung:
- Mindestens `Python 3.10`
- `where python` oder `where py` zeigt einen gültigen Pfad

Wenn `python` nicht gefunden wird, ist meistens eines davon die Ursache:
- Python ist noch nicht installiert
- Beim Installieren wurde **"Add Python to PATH"** nicht aktiviert
- Du musst die Eingabeaufforderung nach der Installation neu öffnen

```
python -m venv venv
```

## Virtuelle Umgebung aktivieren

```
venv\Scripts\activate
```

Du siehst jetzt `(venv)` vor der Eingabezeile. **Das muss immer
aktiv sein wenn du das Skript ausführst.**

## Abhängigkeiten installieren

```
pip install -r requirements.txt
```

Wenn hier ein Fehler wegen `python` oder `pip` kommt, dann ist Python
noch nicht korrekt eingerichtet. In diesem Fall erst die Prüfschritte oben
noch einmal durchgehen.

Erwartete Ausgabe:
```
Successfully installed requests-2.31.0 tzdata-2024.1 ...
```

## Konfiguration anpassen

> **⚠️ WICHTIG:** Die Konfigurationsdatei enthält Platzhalter-Werte!  
> **Detaillierte Anleitung:** Siehe [KONFIGURATION.md](../KONFIGURATION.md)

Öffne die Datei `config/einstellungen.ini` mit einem Texteditor
(z.B. Notepad) und passe **mindestens** folgende Werte an:

```ini
[netzwerk]
controller_ip   = 192.168.1.100    ← Ersetze durch IP deines Controllers
controller_port = 47808
local_ip        = 192.168.1.50     ← Ersetze durch IP dieses PCs
local_port      = 47809

[bacnet_objekte]
av_aktuell      = 1000             ← Ersetze durch deine AV-Nummer
bv_status       = 1025             ← Ersetze durch deine BV-Nummer
```

**Wie finde ich die Werte?**
- **Controller-IP:** In enteliWEB oder beim Netzwerk-Admin
- **PC-IP:** CMD öffnen → `ipconfig` eingeben
- **Objekt-Nummern:** 1 freies Analog Value (AV) und 1 freies Binary Value (BV) im Controller

**Tipp:** Die restlichen Einstellungen können erstmal so bleiben.

## Weiter mit → [Schritt 3: Controller einrichten](03_CONTROLLER_EINRICHTEN.md)
