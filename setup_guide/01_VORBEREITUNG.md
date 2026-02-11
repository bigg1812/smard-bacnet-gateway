# Schritt 1: Vorbereitung

## Was du brauchst

### Hardware
- [x] Windows PC mit Netzwerkzugang zum BACnet-Controller
- [x] BACnet-fähiger Controller (z.B. Delta Controls EBcon)
- [x] Beide Geräte im selben Netzwerk-Subnetz

### Software auf dem PC
- [x] Python 3.10 oder neuer
  - Download: https://www.python.org/downloads/
  - Bei der Installation: **"Add Python to PATH"** anhaken!
- [x] Internetzugang (für die SMARD-API)

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
