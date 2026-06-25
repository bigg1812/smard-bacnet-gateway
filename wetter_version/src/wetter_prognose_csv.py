#!/usr/bin/env python3
"""
wetter_prognose_csv.py – Wetterprognose Außentemperatur CSV-Exporter
==================================================================
Holt stündliche Außentemperatur-Vorhersagen von der Open-Meteo API
und schreibt sie in eine CSV-Datei für die Gebäudeautomation.

Ausführung:
  python src/wetter_prognose_csv.py
"""

import sys
import logging
from pathlib import Path
import configparser

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("")
    print("  FEHLER: Das Paket 'requests' ist nicht installiert.")
    print("  Lösung: Führe 'pip install requests' aus.")
    print("")
    sys.exit(1)

from datetime import datetime
from logging.handlers import RotatingFileHandler

# ════════════════════════════════════════════════════════════════
#  KONFIGURATION LADEN
# ════════════════════════════════════════════════════════════════

def load_config():
    """
    Liest die Konfiguration aus config/einstellungen.ini.
    """
    script_dir = Path(__file__).parent.parent  # wetter_version/
    config_file = script_dir / "config" / "einstellungen.ini"

    if not config_file.exists():
        print(f"")
        print(f"  FEHLER: Konfigurationsdatei nicht gefunden!")
        print(f"  Erwartet: {config_file}")
        print(f"")
        sys.exit(1)

    cp = configparser.ConfigParser(interpolation=None)
    cp.read(config_file, encoding="utf-8")

    cfg = {
        # Wetter API
        "latitude":        cp.getfloat("wetter_api", "latitude", fallback=52.52),
        "longitude":       cp.getfloat("wetter_api", "longitude", fallback=13.41),
        "timeout":         cp.getint("wetter_api", "timeout", fallback=30),
        # CSV
        "csv_filepath":    cp.get("csv", "dateipfad", fallback="config/wetterprognose.csv"),
        "csv_separator":   cp.get("csv", "trennzeichen", fallback=";"),
        "csv_decimal":     cp.get("csv", "dezimaltrennzeichen", fallback=","),
        "csv_date_format": cp.get("csv", "datumsformat", fallback="%d.%m.%Y"),
        # Pfade
        "base_dir":        script_dir,
    }
    return cfg


CFG = load_config()

# Logging-Pfade
LOG_DIR  = CFG["base_dir"] / "logs"
LOG_FILE = LOG_DIR / "wetterprognose.log"


# ════════════════════════════════════════════════════════════════
#  LOGGING EINRICHTEN
# ════════════════════════════════════════════════════════════════

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("wetter_prognose")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=2*1024*1024,
        backupCount=2, encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ════════════════════════════════════════════════════════════════
#  HAUPTPROGRAMM
# ════════════════════════════════════════════════════════════════

def main():
    log = setup_logging()
    log.info("=" * 55)
    log.info("Wetterprognose CSV-Exporter gestartet")
    log.info(f"Koordinaten: Lat={CFG['latitude']}, Lon={CFG['longitude']}")
    
    exit_code = 0
    try:
        # 1. Open-Meteo API aufrufen (Prognose für heute und morgen in Europe/Berlin)
        # forecast_days=2 lädt heute und morgen.
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={CFG['latitude']}"
            f"&longitude={CFG['longitude']}"
            f"&hourly=temperature_2m"
            f"&timezone=Europe%2FBerlin"
            f"&forecast_days=2"
        )
        
        log.debug(f"API-Abfrage: {url}")
        resp = requests.get(url, timeout=CFG["timeout"], verify=False)
        resp.raise_for_status()
        
        data = resp.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        
        if not times or not temps:
            raise ValueError("Keine stündlichen Temperaturdaten in der API-Antwort gefunden.")
            
        log.info(f"{len(times)} Wetter-Prognosewerte erfolgreich empfangen.")
        
        # 2. CSV schreiben
        csv_file = Path(CFG["csv_filepath"])
        if not csv_file.is_absolute():
            csv_file = CFG["base_dir"] / csv_file
            
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        
        sep = CFG["csv_separator"]
        dec = CFG["csv_decimal"]
        date_fmt = CFG["csv_date_format"]
        
        log.info(f"Schreibe CSV in: {csv_file}")
        
        with open(csv_file, "w", encoding="utf-8") as f:
            # Header
            f.write(f"Datum{sep}Uhrzeit{sep}Temperatur_C\n")
            
            for t_str, temp in zip(times, temps):
                # Open-Meteo Datumsformat ist ISO 8601: "YYYY-MM-DDTHH:MM"
                if "T" in t_str:
                    d_part, t_part = t_str.split("T")
                    # Datum in das gewünschte Format konvertieren
                    dt_obj = datetime.strptime(d_part, "%Y-%m-%d")
                    date_formatted = dt_obj.strftime(date_fmt)
                else:
                    date_formatted = t_str
                    t_part = ""
                
                # Temperatur formatieren
                if temp is not None:
                    temp_formatted = f"{temp:.1f}".replace(".", dec)
                else:
                    temp_formatted = ""
                    
                f.write(f"{date_formatted}{sep}{t_part}{sep}{temp_formatted}\n")
                
        log.info("CSV-Datei erfolgreich geschrieben!")
        
    except requests.RequestException as e:
        log.error(f"Netzwerkfehler bei Open-Meteo-API: {e}")
        exit_code = 2
    except Exception as e:
        log.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        exit_code = 99
        
    log.info(f"Beendet (Exit-Code {exit_code})")
    log.info("=" * 55)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
