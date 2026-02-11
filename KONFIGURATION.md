# Konfiguration für dein Projekt anpassen

Diese Datei erklärt **Schritt für Schritt**, welche Platzhalter-Werte du durch deine echten Projektdaten ersetzen musst.

---

## Übersicht: Was muss angepasst werden?

| Datei | Was anpassen | Warum |
|-------|--------------|-------|
| `config/einstellungen.ini` | IP-Adressen, AV-Nummern | Damit das Skript deinen Controller findet |
| `setup_guide/*.md` | Pfade (optional) | Falls du einen anderen Installationsort wählst |

---

## 1. Hauptkonfiguration: `config/einstellungen.ini`

Diese Datei enthält **alle wichtigen Einstellungen**. Öffne sie mit einem Texteditor (z.B. Notepad).

### 📍 Netzwerk-Einstellungen

**Wo:** Zeile 25-28 im Abschnitt `[netzwerk]`

```ini
controller_ip   = 192.168.1.100    ← PLATZHALTER
controller_port = 47808
local_ip        = 192.168.1.50     ← PLATZHALTER
local_port      = 47809
```

**Was du brauchst:**

| Platzhalter | Ersetzen durch | Wie finde ich das? |
|-------------|----------------|-------------------|
| `192.168.1.100` | IP deines BACnet-Controllers | In enteliWEB oder bei deinem Netzwerk-Admin |
| `192.168.1.50` | IP des PCs mit diesem Skript | CMD öffnen → `ipconfig` eingeben → "IPv4-Adresse" |

**Beispiel:**
```ini
# Vorher (Platzhalter):
controller_ip   = 192.168.1.100
local_ip        = 192.168.1.50

# Nachher (deine echten Werte):
controller_ip   = 10.20.30.40
local_ip        = 10.20.30.99
```

---

### 🔢 BACnet-Objekt-Nummern

**Wo:** Zeile 43-48 im Abschnitt `[bacnet_objekte]`

```ini
av_aktuell      = 1000    ← PLATZHALTER
av_morgen_start = 1001    ← PLATZHALTER
av_morgen_ende  = 1024    ← PLATZHALTER
av_status       = 1025    ← PLATZHALTER
priority        = 14
fehlwert        = -1.0
```

**Was du brauchst:**

Du musst **26 freie Analog Values** im Controller anlegen (siehe [03_CONTROLLER_EINRICHTEN.md](setup_guide/03_CONTROLLER_EINRICHTEN.md)).

| Platzhalter | Ersetzen durch | Beschreibung |
|-------------|----------------|--------------|
| `1000` | Deine AV-Instanznummer | Für den aktuellen Strompreis |
| `1001` | Deine AV-Instanznummer | Erste Stunde morgen (00:00) |
| `1024` | Deine AV-Instanznummer | Letzte Stunde morgen (23:00) |
| `1025` | Deine AV-Instanznummer | Status/Watchdog |

**Wichtig:** Die Nummern müssen **aufeinanderfolgend** sein!
- Wenn `av_morgen_start = 2000`, dann muss `av_morgen_ende = 2023` sein (24 Stunden)

**Beispiel:**
```ini
# Vorher (Platzhalter):
av_aktuell      = 1000
av_morgen_start = 1001
av_morgen_ende  = 1024
av_status       = 1025

# Nachher (deine echten AV-Nummern):
av_aktuell      = 5000
av_morgen_start = 5001
av_morgen_ende  = 5024
av_status       = 5025
```

---

### ⚙️ Weitere Einstellungen (optional)

Diese Werte funktionieren normalerweise ohne Änderung:

| Einstellung | Standard | Wann ändern? |
|-------------|----------|--------------|
| `controller_port` | 47808 | Nur wenn dein Controller einen anderen Port nutzt |
| `local_port` | 47809 | Wenn Port 47809 bereits belegt ist |
| `priority` | 14 | Wenn du eine andere BACnet-Priority brauchst (1-16) |
| `faktor` | 0.1 | Wenn du EUR/MWh statt ct/kWh willst (dann 1.0) |
| `region` | DE-LU | Für Österreich: AT, für Deutschland vor 2018: DE-AT-LU |

---

## 2. Setup-Anleitungen anpassen (optional)

Falls du **nicht** nach `C:\smard-bacnet-gateway\` installierst, musst du die Pfade in den Anleitungen anpassen.

### Dateien mit Pfaden:

1. **`setup_guide/02_INSTALLATION.md`**
   - Zeile 7, 13, 19: `C:\smard-bacnet-gateway\`
   
2. **`setup_guide/04_ERSTER_TEST.md`**
   - Zeile 7: `cd C:\smard-bacnet-gateway`
   
3. **`setup_guide/05_AUTOMATISIERUNG.md`**
   - Zeile 26: `C:\smard-bacnet-gateway\venv\Scripts\python.exe`
   - Zeile 28: `C:\smard-bacnet-gateway`
   - Zeile 50: (gleiches für stündlichen Task)

**Beispiel:**
```markdown
# Vorher (Platzhalter):
cd C:\smard-bacnet-gateway

# Nachher (dein Pfad):
cd D:\Projekte\Strompreis-Gateway
```

---

## 3. Checkliste vor dem ersten Start

- [ ] `config/einstellungen.ini` geöffnet
- [ ] `controller_ip` durch echte Controller-IP ersetzt
- [ ] `local_ip` durch echte PC-IP ersetzt
- [ ] 26 Analog Values im Controller angelegt
- [ ] `av_aktuell`, `av_morgen_start`, `av_morgen_ende`, `av_status` angepasst
- [ ] Datei gespeichert
- [ ] Verbindungstest ausgeführt: `python src/verbindungstest.py`

---

## 4. Häufige Fehler

### ❌ "Konfigurationsdatei nicht gefunden"
**Problem:** Das Skript findet `config/einstellungen.ini` nicht.  
**Lösung:** Stelle sicher, dass du im richtigen Verzeichnis bist (`cd C:\smard-bacnet-gateway`)

### ❌ "Port belegt"
**Problem:** `local_port` ist bereits in Benutzung.  
**Lösung:** Ändere `local_port` auf 47810 oder 47811

### ❌ "Controller antwortet nicht"
**Problem:** Falsche `controller_ip` oder Firewall blockiert.  
**Lösung:** 
1. Prüfe IP mit `ping 192.168.x.x`
2. Firewall-Regel anlegen (siehe [04_ERSTER_TEST.md](setup_guide/04_ERSTER_TEST.md))

### ❌ "AV:1000 existiert nicht"
**Problem:** Die AV-Nummern stimmen nicht mit dem Controller überein.  
**Lösung:** Prüfe in enteliWEB, welche AV-Nummern du wirklich angelegt hast

---

## 5. Schnellreferenz: Wo finde ich was?

### IP-Adresse des Controllers
- **enteliWEB:** System → Network → IP Address
- **CopperCube:** Device Properties → Network
- **Netzwerk-Admin fragen**

### IP-Adresse des PCs
```cmd
ipconfig
```
Suche nach "IPv4-Adresse" bei deinem aktiven Netzwerkadapter.

### Freie AV-Nummern im Controller
- **enteliWEB:** Objects → Analog Values → Liste durchsehen
- **Tipp:** Wähle einen Nummernbereich, der noch nicht verwendet wird (z.B. 5000-5025)

### BACnet-Port des Controllers
- Standard: **47808**
- Falls unsicher: In den Controller-Einstellungen nachsehen

---

## Fertig!

Wenn du alle Platzhalter ersetzt hast, kannst du mit dem [Verbindungstest](setup_guide/04_ERSTER_TEST.md) fortfahren.
