#!/usr/bin/env python3
"""
strompreis_csv.py – SMARD Strompreis CSV-Exporter
==================================================
Holt Day-Ahead Strompreise von der SMARD-API (Bundesnetzagentur)
und schreibt die Werte für gestern und heute stündlich in eine CSV-Datei.

Ausführung:
  python src/strompreis_csv.py
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
import configparser

# --- Zeitzone ---
try:
    from zoneinfo import ZoneInfo
    TZ_BERLIN = ZoneInfo("Europe/Berlin")
except Exception:
    TZ_BERLIN = None

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


# ════════════════════════════════════════════════════════════════
#  KONFIGURATION LADEN
# ════════════════════════════════════════════════════════════════

def load_config():
    """
    Liest die Konfiguration aus config/einstellungen.ini.
    """
    script_dir = Path(__file__).parent.parent  # csv_version/
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
        # SMARD API
        "smard_filter":    cp.getint("smard_api", "filter_id", fallback=4169),
        "smard_region":    cp.get("smard_api", "region", fallback="DE-LU"),
        "smard_timeout":   cp.getint("smard_api", "timeout", fallback=30),
        # Einheiten
        "price_factor":    cp.getfloat("einheiten", "faktor", fallback=0.1),
        "price_unit":      cp.get("einheiten", "einheit", fallback="ct/kWh"),
        # CSV
        "csv_filepath":    cp.get("csv", "dateipfad", fallback="config/strompreise.csv"),
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
LOG_FILE = LOG_DIR / "strompreis_csv.log"


# ════════════════════════════════════════════════════════════════
#  LOGGING EINRICHTEN
# ════════════════════════════════════════════════════════════════

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("strompreis_csv")
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
#  ZEITZONEN-HILFSFUNKTIONEN
# ════════════════════════════════════════════════════════════════

def _berlin_now():
    """Aktuelle Zeit in Europe/Berlin."""
    if TZ_BERLIN is not None:
        return datetime.now(TZ_BERLIN)
    return datetime.now(_get_berlin_offset())


def _get_berlin_offset():
    """Bestimmt UTC-Offset für Berlin (CET +1 / CEST +2)."""
    now = datetime.now(timezone.utc)
    y = now.year
    # Letzter Sonntag im März 01:00 UTC
    d = datetime(y, 3, 31, 1, tzinfo=timezone.utc)
    dst_start = d - timedelta(days=(d.weekday() + 1) % 7)
    # Letzter Sonntag im Oktober 01:00 UTC
    d = datetime(y, 10, 31, 1, tzinfo=timezone.utc)
    dst_end = d - timedelta(days=(d.weekday() + 1) % 7)
    if dst_start <= now < dst_end:
        return timezone(timedelta(hours=2))
    return timezone(timedelta(hours=1))


def get_yesterday_today_range():
    """
    Berechnet die Millisekunden-Timestamps (UTC) für gestern 00:00 Uhr
    bis heute 23:59 Uhr (Berliner Zeit).
    """
    now = _berlin_now()
    yesterday = now - timedelta(days=1)

    # Start: Gestern 00:00:00 Uhr Berliner Zeit
    if TZ_BERLIN is not None:
        start_dt = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=TZ_BERLIN)
    else:
        offset = _get_berlin_offset()
        start_dt = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=offset)
    
    # Ende: Morgen 00:00:00 Uhr Berliner Zeit (damit heute 23:00 - 24:00 abgedeckt ist)
    tomorrow = now + timedelta(days=1)
    if TZ_BERLIN is not None:
        end_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0, tzinfo=TZ_BERLIN)
    else:
        offset = _get_berlin_offset()
        end_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0, tzinfo=offset)

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    
    return start_ms, end_ms


# ════════════════════════════════════════════════════════════════
#  SMARD API ABFRAGE
# ════════════════════════════════════════════════════════════════

SMARD_BASE = "https://www.smard.de/app/chart_data"


def _smard_index(log):
    """Lädt den Index verfügbarer Datenblöcke."""
    f = CFG["smard_filter"]
    r = CFG["smard_region"]
    url = f"{SMARD_BASE}/{f}/{r}/index_hour.json"
    log.debug(f"SMARD Index: {url}")
    resp = requests.get(url, timeout=CFG["smard_timeout"], verify=False)
    resp.raise_for_status()
    ts = resp.json().get("timestamps", [])
    if not ts:
        raise ValueError("SMARD-Index leer")
    return ts


def _smard_block(block_ts, log):
    """Lädt einen Datenblock."""
    f = CFG["smard_filter"]
    r = CFG["smard_region"]
    url = f"{SMARD_BASE}/{f}/{r}/{f}_{r}_hour_{block_ts}.json"
    log.debug(f"SMARD Block: {url}")
    resp = requests.get(url, timeout=CFG["smard_timeout"], verify=False)
    resp.raise_for_status()
    return resp.json().get("series", [])


def fetch_prices_for_range(start_ms, end_ms, log):
    """
    Holt alle stündlichen Preise im angegebenen Zeitbereich.
    """
    timestamps = _smard_index(log)
    h = 3_600_000
    
    num_hours = (end_ms - start_ms) // h
    log.info(f"Frage {num_hours} Stundenwerte ab...")

    raw_prices = [None] * num_hours

    # Wir durchsuchen die letzten Blöcke rückwärts
    for bts in reversed(timestamps[-6:]):
        if bts > end_ms:
            continue
        try:
            series = _smard_block(bts, log)
        except Exception as e:
            log.warning(f"Fehler beim Laden von Block {bts}: {e}")
            continue

        for ts, price in series:
            if price is not None and start_ms <= ts < end_ms:
                idx = (ts - start_ms) // h
                if 0 <= idx < num_hours:
                    # Neuerer Block überschreibt älteren
                    if raw_prices[idx] is None:
                        raw_prices[idx] = price

        if all(p is not None for p in raw_prices):
            log.debug("Alle Stundenwerte erfolgreich gefunden.")
            break

    return raw_prices


# ════════════════════════════════════════════════════════════════
#  CSV SCHREIBEN
# ════════════════════════════════════════════════════════════════

def write_csv(start_ms, raw_prices, log):
    """
    Formatiert die Daten und schreibt sie in die CSV-Datei.
    """
    h = 3_600_000
    csv_file = Path(CFG["csv_filepath"])
    if not csv_file.is_absolute():
        csv_file = CFG["base_dir"] / csv_file
        
    csv_file.parent.mkdir(parents=True, exist_ok=True)

    sep = CFG["csv_separator"]
    dec = CFG["csv_decimal"]
    date_fmt = CFG["csv_date_format"]
    factor = CFG["price_factor"]
    unit = CFG["price_unit"]

    log.info(f"Schreibe CSV in: {csv_file}")

    try:
        with open(csv_file, "w", encoding="utf-8") as f:
            # Header schreiben
            f.write(f"Datum{sep}Uhrzeit{sep}Preis ({unit})\n")

            for idx, price in enumerate(raw_prices):
                ts = start_ms + idx * h
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                local_dt = dt.astimezone(TZ_BERLIN or _get_berlin_offset())
                
                date_str = local_dt.strftime(date_fmt)
                time_str = local_dt.strftime("%H:%M")

                if price is not None:
                    # Preis konvertieren (z.B. MWh -> kWh)
                    conv_price = price * factor
                    # Dezimaltrennzeichen anpassen (z.B. Komma für Excel)
                    price_str = f"{conv_price:.4f}".replace(".", dec)
                else:
                    price_str = ""

                f.write(f"{date_str}{sep}{time_str}{sep}{price_str}\n")
                
        log.info("CSV-Datei erfolgreich geschrieben!")
        return True
    except Exception as e:
        log.error(f"Fehler beim Schreiben der CSV: {e}")
        return False


# ════════════════════════════════════════════════════════════════
#  HAUPTPROGRAMM
# ════════════════════════════════════════════════════════════════

def main():
    log = setup_logging()
    log.info("=" * 55)
    log.info("SMARD Strompreis CSV-Exporter gestartet")
    log.info(f"Einheit: {CFG['price_unit']} | Region: {CFG['smard_region']}")
    
    exit_code = 0
    try:
        # 1. Zeitbereich berechnen (gestern bis heute)
        start_ms, end_ms = get_yesterday_today_range()
        
        # 2. Preise von SMARD holen
        raw_prices = fetch_prices_for_range(start_ms, end_ms, log)
        
        # 3. Fehlende Werte prüfen
        missing = sum(1 for p in raw_prices if p is None)
        if missing > 0:
            log.warning(f"Warnung: {missing} von {len(raw_prices)} Stundenwerten fehlen!")
            
        # 4. CSV schreiben
        ok = write_csv(start_ms, raw_prices, log)
        if not ok:
            exit_code = 1
            
    except requests.RequestException as e:
        log.error(f"Netzwerkfehler bei SMARD-API: {e}")
        exit_code = 2
    except Exception as e:
        log.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        exit_code = 99
        
    log.info(f"Beendet (Exit-Code {exit_code})")
    log.info("=" * 55)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
