# Schritt 1: Vorbereitung

## Was du brauchst

### Hardware
- [x] Windows PC mit Netzwerkzugang zum BACnet-Controller
- [x] BACnet-fähiger Controller (z.B. Delta Controls EBcon)
- [x] Beide Geräte im selben Netzwerk-Subnetz

### IPC-Minimum
- [x] Windows-Rechner oder IPC mit Administratorrechten
- [x] Feste oder reservierte IP-Adresse im selben Subnetz wie der Controller
- [x] Freier lokaler UDP-Port für BACnet, standardmäßig `47809`
- [x] Freigegebene Windows-Firewall für den gewählten UDP-Port
- [x] Eine freie AV- und BV-Instanznummer im Controller

### Software auf dem PC
- [x] Python 3.10 oder neuer
  - Download: https://www.python.org/downloads/
  - Bei der Installation: **"Add Python to PATH"** anhaken!
- [x] Internetzugang (für die SMARD-API)

### Schnelltest: Habe ich Python?

Öffne die **Eingabeaufforderung** (CMD) und tippe die Befehle **genau so** ein:

```cmd
python --version
```

Erwartung:
- Gut: `Python 3.10.x`, `Python 3.11.x` oder neuer
- Schlecht: `python is not recognized` oder eine sehr alte Version

Wenn das nicht klappt, probiere:

```cmd
py --version
where python
where py
```

So kannst du schnell erkennen:
- `py --version` zeigt, ob der Python-Launcher installiert ist
- `where python` zeigt, ob Windows Python im Suchpfad findet
- `where py` zeigt, ob der Launcher verfügbar ist

Wenn du `python` oder `py` gar nicht findest, installiere Python neu von
https://www.python.org/downloads/ und aktiviere dabei **"Add Python to PATH"**.

### Schnelltest: Welche Python-Version habe ich?

Wenn Python gefunden wird, prüfe die genaue Version:

```cmd
python --version
```

oder alternativ:

```cmd
py --version
```

Für dieses Projekt brauchst du **Python 3.10 oder neuer**.
Wenn dort `Python 3.9.x` oder älter steht, bitte erst aktualisieren.

### Informationen die du brauchst
Notiere folgende Daten – du wirst sie bei der Einrichtung brauchen:

| Was                    | Wo findest du es           | Beispiel          |
|------------------------|----------------------------|--------------------|
| IP des Controllers     | enteliWEB / Netzwerk-Admin | 192.168.244.30     |
| IP dieses PCs          | `ipconfig` in CMD          | 192.168.244.10     |
| BACnet Port Controller | Meist Standard             | 47808              |
| Freier Port auf dem PC | 47809 wenn enteliWEB läuft | 47809              |

### Python-Version prüfen

Öffne die **Eingabeaufforderung** (CMD) und tippe:

```
python --version
```

Es sollte `Python 3.10.x` oder höher angezeigt werden.

Falls nicht: Python installieren (Link oben).

## Weiter mit → [Schritt 2: Installation](02_INSTALLATION.md)
