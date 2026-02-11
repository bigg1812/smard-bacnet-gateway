# SMARD-BACnet Gateway – GitHub Repository

Dieses Repository enthält eine **vollständige, GitHub-ready Vorlage** für das SMARD-BACnet Gateway Projekt.

## 📁 Struktur

```
smard-bacnet-gateway/
├── README.md                   ← Hauptdokumentation
├── KONFIGURATION.md            ← ⭐ WICHTIG: Anleitung zum Anpassen der Platzhalter
├── LICENSE                     ← MIT Lizenz
├── .gitignore                  ← Git-Ausschlüsse
├── requirements.txt            ← Python-Abhängigkeiten
├── config/
│   └── einstellungen.ini       ← Konfiguration (enthält Platzhalter!)
├── src/
│   ├── strompreis_bacnet.py    ← Hauptskript
│   └── verbindungstest.py      ← Verbindungstest
├── setup_guide/
│   ├── 01_VORBEREITUNG.md
│   ├── 02_INSTALLATION.md
│   ├── 03_CONTROLLER_EINRICHTEN.md
│   ├── 04_ERSTER_TEST.md
│   ├── 05_AUTOMATISIERUNG.md
│   └── bilder/                 ← Für Screenshots
└── logs/
    └── .gitkeep                ← Platzhalter für Git
```

## ⚠️ Vor der Verwendung

**WICHTIG:** Dieses Repository enthält **Platzhalter-Werte**, die du durch deine echten Projektdaten ersetzen musst!

### 1. Lies zuerst: [KONFIGURATION.md](KONFIGURATION.md)

Diese Datei erklärt **Schritt für Schritt**:
- ✅ Welche Platzhalter wo zu finden sind
- ✅ Wie du deine echten IP-Adressen und AV-Nummern findest
- ✅ Welche Werte du anpassen musst
- ✅ Häufige Fehler und deren Lösungen

### 2. Passe die Konfiguration an

Die wichtigste Datei: **`config/einstellungen.ini`**

Ersetze:
- `192.168.1.100` → Deine Controller-IP
- `192.168.1.50` → Deine PC-IP
- `1000`, `1001`, etc. → Deine AV-Nummern

### 3. Folge der Setup-Anleitung

Starte mit: [setup_guide/01_VORBEREITUNG.md](setup_guide/01_VORBEREITUNG.md)

## 🚀 Schnellstart

```powershell
# 1. Repository klonen
git clone https://github.com/DEIN-NAME/smard-bacnet-gateway.git
cd smard-bacnet-gateway

# 2. KONFIGURATION.md lesen und Werte anpassen!
notepad KONFIGURATION.md
notepad config\einstellungen.ini

# 3. Python-Umgebung einrichten
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 4. Verbindung testen
python src/verbindungstest.py

# 5. Strompreise abrufen
python src/strompreis_bacnet.py
```

## 📖 Dokumentation

| Datei | Beschreibung |
|-------|--------------|
| [README.md](README.md) | Hauptdokumentation des Projekts |
| [KONFIGURATION.md](KONFIGURATION.md) | **⭐ Anleitung zum Anpassen der Platzhalter** |
| [setup_guide/](setup_guide/) | Schritt-für-Schritt Installationsanleitung |

## 🔧 Für GitHub vorbereiten

Falls du dieses Repository auf GitHub veröffentlichen möchtest:

1. ✅ **Prüfe**, dass `config/einstellungen.ini` nur Platzhalter enthält (keine echten IPs!)
2. ✅ **Prüfe**, dass `.gitignore` korrekt ist
3. ✅ **Erstelle** ein neues Repository auf GitHub
4. ✅ **Pushe** den Code:

```bash
git init
git add .
git commit -m "Initial commit: SMARD-BACnet Gateway"
git branch -M main
git remote add origin https://github.com/DEIN-NAME/smard-bacnet-gateway.git
git push -u origin main
```

## 📝 Lizenz

MIT License – siehe [LICENSE](LICENSE)

## 🔗 Weitere Informationen

- **SMARD-Datenquelle:** https://www.smard.de
- **BACnet-Protokoll:** http://www.bacnet.org
- **Python:** https://www.python.org

---

**Hinweis:** Diese Vorlage wurde erstellt, um das Projekt einfach mit anderen zu teilen, ohne projektspezifische Informationen preiszugeben.
