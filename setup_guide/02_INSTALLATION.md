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
av_aktuell      = 1000             ← Ersetze durch deine AV-Nummern
av_morgen_start = 1001
av_morgen_ende  = 1024
av_status       = 1025
```

**Wie finde ich die Werte?**
- **Controller-IP:** In enteliWEB oder beim Netzwerk-Admin
- **PC-IP:** CMD öffnen → `ipconfig` eingeben
- **AV-Nummern:** Freie Analog Values im Controller (26 Stück benötigt)

**Tipp:** Die restlichen Einstellungen können erstmal so bleiben.

## Weiter mit → [Schritt 3: Controller einrichten](03_CONTROLLER_EINRICHTEN.md)
