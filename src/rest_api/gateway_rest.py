#!/usr/bin/env python3
"""
gateway_rest.py - SMARD/Wetter -> enteliWEB REST-API
====================================================
Holt Strompreise (SMARD) und Wetterprognose (Open-Meteo) und schreibt sie
ueber die enteliWEB REST-API in BACnet-Objekte. KEIN direktes BACnet.

Ablauf:
  Config laden -> aktive Quellen abfragen -> Schreibauftraege bauen
  -> ueber HTTP PUT an enteliWEB senden -> verifizieren.

Ausfuehrung:
  python src/gateway_rest.py                 (alle aktiven Quellen)
  python src/gateway_rest.py --modus preis   (nur Strompreis)
  python src/gateway_rest.py --modus wetter  (nur Wetter)
  python src/gateway_rest.py --live          (wirklich senden; sonst Dry-Run)

Exit-Codes: 0=OK, 1=Verbindungs-/HTTP-Fehler, 2=Quellen-Fehler, 99=Sonstig
"""

import sys
import argparse
import configparser
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from sources import smard, openmeteo
from enteliweb import EnteliwebClient

# Repo-Wurzel: diese Datei liegt unter src/rest_api/, also drei Ebenen hoch.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "config" / "einstellungen.ini"
LOG_FILE = BASE_DIR / "logs" / "gateway_rest.log"


# ----------------------------------------------------------------------
#  Config & Logging
# ----------------------------------------------------------------------

def load_config():
    if not CONFIG_FILE.exists():
        print(f"FEHLER: Konfiguration nicht gefunden: {CONFIG_FILE}")
        sys.exit(1)
    cp = configparser.ConfigParser()
    cp.read(CONFIG_FILE, encoding="utf-8")
    return cp


def _ja(cp, section, key, default=False):
    if not cp.has_option(section, key):
        return default
    return cp.get(section, key).strip().lower() in ("an", "ja", "true", "1", "yes")


def setup_logging():
    LOG_FILE.parent.mkdir(exist_ok=True)
    log = logging.getLogger("gateway_rest")
    if log.handlers:
        return log
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(ch)
    return log


# ----------------------------------------------------------------------
#  Quellen -> Schreibauftraege
#  Ein Schreibauftrag ist ein Tupel: (objekt, wert, label)
# ----------------------------------------------------------------------

def tasks_strompreis(cp, log):
    cfg = {
        "filter_id": cp.getint("smard_api", "filter_id"),
        "region": cp.get("smard_api", "region"),
        "timeout": cp.getint("smard_api", "timeout"),
        "aufloesung": cp.get("smard_api", "aufloesung", fallback="hour"),
        "faktor": cp.getfloat("einheiten", "faktor"),
        "einheit": cp.get("einheiten", "einheit"),
    }
    tasks = []

    fehlwert = cp.getfloat("strompreis_objekte", "fehlwert", fallback=-1.0)

    # Aktueller Preis -> ein AV
    _, conv, _ = smard.get_current_price(cfg, log)
    obj_aktuell = cp.get("strompreis_objekte", "av_aktuell")
    tasks.append((obj_aktuell, conv, f"Strompreis aktuell ({cfg['einheit']})"))

    # Optional: Preis in 24 Stunden -> ein AV
    if cp.has_option("strompreis_objekte", "av_in_24h"):
        obj_24h = cp.get("strompreis_objekte", "av_in_24h")
        ergebnis = smard.get_price_in_hours(cfg, log, hours=24)
        wert = ergebnis[1] if ergebnis is not None else fehlwert
        tasks.append((obj_24h, wert, f"Strompreis in 24h ({cfg['einheit']})"))

    # Optional: 24 Stundenpreise fuer morgen -> 24 fortlaufende AVs
    if cp.has_option("strompreis_objekte", "av_morgen_basis"):
        basis = cp.getint("strompreis_objekte", "av_morgen_basis")
        for stunde, preis in smard.get_tomorrow_prices(cfg, log):
            wert = preis if preis is not None else fehlwert
            tasks.append((f"analog-value,{basis + stunde}", wert,
                          f"Strompreis morgen {stunde:02d}:00"))

    return tasks


def tasks_wetter(cp, log):
    werte = [w.strip() for w in cp.get("wetter_api", "werte").split(",") if w.strip()]
    cfg = {
        "latitude": cp.getfloat("wetter_api", "latitude"),
        "longitude": cp.getfloat("wetter_api", "longitude"),
        "werte": werte,
        "timeout": cp.getint("wetter_api", "timeout", fallback=30),
        "forecast_days": cp.getint("wetter_api", "forecast_days", fallback=2),
    }
    prognose = openmeteo.get_forecast(cfg, log)
    aktuell = prognose["aktuell"]

    # Jede Wetter-Variable bekommt ihr Objekt aus [wetter_objekte] zugeordnet.
    tasks = []
    for variable in werte:
        if not cp.has_option("wetter_objekte", variable):
            log.warning(f"Wetter: kein BACnet-Objekt fuer '{variable}' in [wetter_objekte] - uebersprungen")
            continue
        objekt = cp.get("wetter_objekte", variable)
        wert = aktuell.get(variable)
        if wert is None:
            log.warning(f"Wetter: kein Wert fuer '{variable}'")
            continue
        tasks.append((objekt, wert, f"Wetter {variable}"))
    return tasks


# ----------------------------------------------------------------------
#  Hauptlogik
# ----------------------------------------------------------------------

def ziel_objekte(cp):
    """Sammelt alle konfigurierten Ziel-Objekte fuer den --check-Modus."""
    objekte = []
    if cp.has_option("strompreis_objekte", "av_aktuell"):
        objekte.append(("Strompreis aktuell", cp.get("strompreis_objekte", "av_aktuell")))
    if cp.has_option("strompreis_objekte", "av_in_24h"):
        objekte.append(("Strompreis in 24h", cp.get("strompreis_objekte", "av_in_24h")))
    if cp.has_option("strompreis_objekte", "av_morgen_basis"):
        basis = cp.getint("strompreis_objekte", "av_morgen_basis")
        # Stichprobe: erste und letzte Stunde reicht zum Pruefen des Bereichs
        objekte.append(("Strompreis morgen 00:00", f"analog-value,{basis}"))
        objekte.append(("Strompreis morgen 23:00", f"analog-value,{basis + 23}"))
    if cp.has_section("wetter_objekte"):
        for variable, objekt in cp.items("wetter_objekte"):
            objekte.append((f"Wetter {variable}", objekt))
    return objekte


def run_check(ew_cfg, cp, log):
    """Prueft die HTTP-Strecke und die Ziel-Objekte (read-only, schreibt nie)."""
    log.info("PRUEFMODUS: nur Lesezugriffe (read-only) - es wird nichts geschrieben.")
    with EnteliwebClient(ew_cfg, log) as ew:
        log.info("-- Stufe 1: enteliWEB erreichbar + Auth + Lizenz --")
        ok, status, msg = ew.ping()
        zeichen = "OK " if ok else "FEHLER"
        log.info(f"  [{zeichen}] Device {ew_cfg['site']}/{ew_cfg['device']}: {msg}")
        if not ok:
            log.error("Abbruch: Grundverbindung steht nicht. Objekt-Pruefung uebersprungen.")
            return 1

        objekte = ziel_objekte(cp)
        log.info(f"-- Stufe 2: {len(objekte)} Ziel-Objekt(e) lesbar? --")
        fehler = 0
        for label, objekt in objekte:
            ok, status, msg = ew.probe(objekt)
            zeichen = "OK " if ok else "FEHLER"
            log.info(f"  [{zeichen}] {label} ({objekt}): {msg}")
            if not ok:
                fehler += 1
        log.info(f"-- Ergebnis: {len(objekte) - fehler}/{len(objekte)} Objekte ok --")
        return 0 if fehler == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="SMARD/Wetter -> enteliWEB REST-API")
    parser.add_argument("--modus", choices=["preis", "wetter", "alle"], default="alle")
    parser.add_argument("--live", action="store_true",
                        help="Wirklich senden. Ohne dieses Flag: Dry-Run (loggt nur).")
    parser.add_argument("--check", action="store_true",
                        help="Nur Verbindung und Ziel-Objekte pruefen (read-only). Schreibt nichts.")
    args = parser.parse_args()

    log = setup_logging()
    cp = load_config()

    # enteliWEB-Client-Konfiguration
    ew_cfg = {
        "protokoll": cp.get("enteliweb", "protokoll", fallback="http"),
        "host": cp.get("enteliweb", "host"),
        "port": cp.getint("enteliweb", "port", fallback=80),
        "benutzer": cp.get("enteliweb", "benutzer"),
        "passwort": cp.get("enteliweb", "passwort"),
        "site": cp.get("enteliweb", "site"),
        "device": cp.get("enteliweb", "device"),
        "priority": cp.getint("enteliweb", "priority", fallback=14),
        "http_timeout": cp.getint("enteliweb", "http_timeout", fallback=30),
        "http_retries": cp.getint("enteliweb", "http_retries", fallback=3),
        "verify_tls": _ja(cp, "enteliweb", "verify_tls", default=True),
    }
    # Dry-Run ist die sichere Grundeinstellung. Scharf geschaltet wird nur,
    # wenn das Flag --live gesetzt ist ODER in der Config dry_run=nein steht.
    config_live = cp.has_option("enteliweb", "dry_run") and not _ja(cp, "enteliweb", "dry_run", default=True)
    ew_cfg["dry_run"] = not (args.live or config_live)

    log.info("=" * 60)

    # Pruefmodus: nur lesen, dann beenden (kein Datenabruf von SMARD/Wetter noetig)
    if args.check:
        log.info("Gateway REST (--check)")
        try:
            code = run_check(ew_cfg, cp, log)
        except KeyError as e:
            log.error(f"Konfiguration unvollstaendig - fehlt: {e}")
            code = 1
        except Exception as e:
            log.error(f"Fehler im Pruefmodus: {e}", exc_info=True)
            code = 99
        log.info(f"Beendet (Exit-Code {code})")
        log.info("=" * 60)
        return code

    log.info(f"Gateway REST (Modus: {args.modus})")

    # Schreibauftraege sammeln
    alle_tasks = []
    exit_code = 0
    try:
        if args.modus in ("preis", "alle") and _ja(cp, "quellen", "strompreis", default=True):
            log.info("-- Quelle: Strompreis (SMARD) --")
            alle_tasks += tasks_strompreis(cp, log)
        if args.modus in ("wetter", "alle") and _ja(cp, "quellen", "wetter", default=False):
            log.info("-- Quelle: Wetter (Open-Meteo) --")
            alle_tasks += tasks_wetter(cp, log)
    except Exception as e:
        log.error(f"Fehler beim Abrufen der Quellen: {e}", exc_info=True)
        exit_code = 2

    if not alle_tasks:
        log.warning("Keine Schreibauftraege - nichts zu tun.")
        log.info("=" * 60)
        return exit_code

    # Schreiben via enteliWEB REST-API
    log.info(f"-- Schreibe {len(alle_tasks)} Wert(e) ueber enteliWEB REST-API --")
    try:
        with EnteliwebClient(ew_cfg, log) as ew:
            erfolg = 0
            for objekt, wert, label in alle_tasks:
                log.info(f"{label}: {objekt} = {wert}")
                if ew.write(objekt, wert):
                    erfolg += 1
            log.info(f"Geschrieben: {erfolg}/{len(alle_tasks)}")
            if erfolg < len(alle_tasks):
                exit_code = max(exit_code, 1)
    except KeyError as e:
        log.error(f"Konfiguration unvollstaendig - fehlt: {e}")
        exit_code = 1
    except Exception as e:
        log.error(f"Fehler beim Schreiben: {e}", exc_info=True)
        exit_code = 1

    log.info(f"Beendet (Exit-Code {exit_code})")
    log.info("=" * 60)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
