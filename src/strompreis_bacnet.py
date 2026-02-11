#!/usr/bin/env python3
"""
strompreis_bacnet.py – SMARD-BACnet Gateway
============================================
Holt Day-Ahead Strompreise von der SMARD-API (Bundesnetzagentur)
und schreibt sie via BACnet/IP in einen Gebaeudeautomations-Controller.

Ausfuehrung:
  python strompreis_bacnet.py                  (alles)
  python strompreis_bacnet.py --modus aktuell  (nur aktueller Preis)
  python strompreis_bacnet.py --modus morgen   (nur 24h Morgen-Preise)

Version: 2.2.0
"""

import socket
import struct
import time
import logging
import sys
import argparse
import configparser
from datetime import datetime, date, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

# --- Zeitzone ---
try:
    from zoneinfo import ZoneInfo
    TZ_BERLIN = ZoneInfo("Europe/Berlin")
except Exception:
    TZ_BERLIN = None

try:
    import requests
except ImportError:
    print("")
    print("  FEHLER: Das Paket 'requests' ist nicht installiert.")
    print("")
    print("  Loesung: Fuehre folgenden Befehl aus:")
    print("    pip install requests")
    print("")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════
#  KONFIGURATION LADEN
# ════════════════════════════════════════════════════════════════

def load_config():
    """
    Liest die Konfiguration aus config/einstellungen.ini.
    Gibt ein Dictionary mit allen Einstellungen zurueck.
    """
    # Pfad zur Konfigurationsdatei (relativ zum Skript)
    script_dir = Path(__file__).parent.parent  # smard-bacnet-gateway/
    config_file = script_dir / "config" / "einstellungen.ini"

    if not config_file.exists():
        print(f"")
        print(f"  FEHLER: Konfigurationsdatei nicht gefunden!")
        print(f"  Erwartet: {config_file}")
        print(f"")
        print(f"  Bitte config/einstellungen.ini erstellen.")
        print(f"  Eine Vorlage liegt im Repository.")
        print(f"")
        sys.exit(1)

    cp = configparser.ConfigParser()
    cp.read(config_file, encoding="utf-8")

    cfg = {
        # Netzwerk
        "controller_ip":   cp.get("netzwerk", "controller_ip"),
        "controller_port": cp.getint("netzwerk", "controller_port"),
        "local_ip":        cp.get("netzwerk", "local_ip"),
        "local_port":      cp.getint("netzwerk", "local_port"),
        # BACnet Objekte
        "av_aktuell":      cp.getint("bacnet_objekte", "av_aktuell"),
        "av_morgen_start": cp.getint("bacnet_objekte", "av_morgen_start"),
        "av_morgen_ende":  cp.getint("bacnet_objekte", "av_morgen_ende"),
        "av_status":       cp.getint("bacnet_objekte", "av_status"),
        "priority":        cp.getint("bacnet_objekte", "priority"),
        "fehlwert":        cp.getfloat("bacnet_objekte", "fehlwert"),
        # SMARD
        "smard_filter":    cp.getint("smard_api", "filter_id"),
        "smard_region":    cp.get("smard_api", "region"),
        "smard_timeout":   cp.getint("smard_api", "timeout"),
        # Einheiten
        "price_factor":    cp.getfloat("einheiten", "faktor"),
        "price_unit":      cp.get("einheiten", "einheit"),
        # Robustheit
        "bacnet_timeout":  cp.getint("robustheit", "bacnet_timeout"),
        "bacnet_retries":  cp.getint("robustheit", "bacnet_retries"),
        "write_delay":     cp.getfloat("robustheit", "write_delay"),
        # Pfade
        "base_dir":        script_dir,
    }
    return cfg


# Globale Konfiguration laden
CFG = load_config()

# Logging-Pfade
LOG_DIR  = CFG["base_dir"] / "logs"
LOG_FILE = LOG_DIR / "strompreis.log"


# ════════════════════════════════════════════════════════════════
#  HILFSFUNKTIONEN: ZEITZONE
# ════════════════════════════════════════════════════════════════

def _berlin_now():
    """Aktuelle Zeit in Europe/Berlin."""
    if TZ_BERLIN is not None:
        return datetime.now(TZ_BERLIN)
    return datetime.now(_get_berlin_offset())


def _get_berlin_offset():
    """Bestimmt UTC-Offset fuer Berlin (CET +1 / CEST +2)."""
    now = datetime.now(timezone.utc)
    y = now.year
    # Letzter Sonntag im Maerz 01:00 UTC
    d = datetime(y, 3, 31, 1, tzinfo=timezone.utc)
    dst_start = d - timedelta(days=(d.weekday() + 1) % 7)
    # Letzter Sonntag im Oktober 01:00 UTC
    d = datetime(y, 10, 31, 1, tzinfo=timezone.utc)
    dst_end = d - timedelta(days=(d.weekday() + 1) % 7)
    if dst_start <= now < dst_end:
        return timezone(timedelta(hours=2))
    return timezone(timedelta(hours=1))


def _tomorrow_midnight_utc_ms():
    """UTC-Timestamp in ms fuer morgen 00:00 Berliner Zeit."""
    now = _berlin_now()
    if TZ_BERLIN is not None:
        tomorrow = (now + timedelta(days=1)).date()
        midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day,
                            tzinfo=TZ_BERLIN)
    else:
        offset = _get_berlin_offset()
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        midnight = tomorrow.replace(tzinfo=offset)
    return int(midnight.timestamp() * 1000)


# ════════════════════════════════════════════════════════════════
#  LOGGING
# ════════════════════════════════════════════════════════════════

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("strompreis")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024,
        backupCount=3, encoding="utf-8",
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
#  SMARD API
# ════════════════════════════════════════════════════════════════

SMARD_BASE = "https://www.smard.de/app/chart_data"


def _smard_index(log):
    """Laedt den Index verfuegbarer Datenbloecke."""
    f = CFG["smard_filter"]
    r = CFG["smard_region"]
    url = f"{SMARD_BASE}/{f}/{r}/index_hour.json"
    log.debug(f"SMARD Index: {url}")
    resp = requests.get(url, timeout=CFG["smard_timeout"])
    resp.raise_for_status()
    ts = resp.json().get("timestamps", [])
    if not ts:
        raise ValueError("SMARD-Index leer")
    log.debug(f"SMARD: {len(ts)} Bloecke")
    return ts


def _smard_block(block_ts, log):
    """Laedt einen Datenblock."""
    f = CFG["smard_filter"]
    r = CFG["smard_region"]
    url = f"{SMARD_BASE}/{f}/{r}/{f}_{r}_hour_{block_ts}.json"
    log.debug(f"SMARD Block: {url}")
    resp = requests.get(url, timeout=CFG["smard_timeout"])
    resp.raise_for_status()
    return resp.json().get("series", [])


def get_current_price(log):
    """
    Holt den Strompreis fuer die aktuelle Stunde.

    Gibt zurueck: (rohpreis, konvertierter_preis, zeitstempel)
    """
    timestamps = _smard_index(log)
    now_ms = int(time.time() * 1000)
    h = 3_600_000

    for bts in reversed(timestamps[-3:]):
        for ts, price in _smard_block(bts, log):
            if price is not None and ts <= now_ms < ts + h:
                conv = round(price * CFG["price_factor"], 4)
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                local = dt.astimezone(TZ_BERLIN or _get_berlin_offset())
                log.info(
                    f"Aktueller Preis: {price:.2f} EUR/MWh = "
                    f"{conv:.2f} {CFG['price_unit']} "
                    f"({local.strftime('%d.%m.%Y %H:%M')})"
                )
                return price, conv, dt

    # Fallback
    log.warning("Kein Preis fuer aktuelle Stunde – nutze letzten bekannten")
    for bts in reversed(timestamps[-2:]):
        for ts, price in reversed(_smard_block(bts, log)):
            if price is not None:
                conv = round(price * CFG["price_factor"], 4)
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                log.warning(f"Fallback: {price:.2f} EUR/MWh = {conv:.2f} {CFG['price_unit']}")
                return price, conv, dt

    raise ValueError("Kein Preis verfuegbar")


def get_tomorrow_prices(log):
    """
    Holt die 24 Stundenpreise fuer morgen.

    Gibt zurueck: Liste mit 24 Tupeln [(stunde, preis_oder_None), ...]
    """
    timestamps = _smard_index(log)
    start_ms = _tomorrow_midnight_utc_ms()
    h = 3_600_000
    end_ms = start_ms + 24 * h

    now = _berlin_now()
    log.info(f"Suche Preise fuer {(now + timedelta(days=1)).strftime('%d.%m.%Y')}")

    raw = [None] * 24

    for bts in reversed(timestamps[-5:]):
        if bts > end_ms:
            continue
        for ts, price in _smard_block(bts, log):
            if price is not None and start_ms <= ts < end_ms:
                idx = (ts - start_ms) // h
                if 0 <= idx < 24:
                    raw[idx] = price
        if all(p is not None for p in raw):
            break

    result = []
    found = 0
    for hour in range(24):
        if raw[hour] is not None:
            result.append((hour, round(raw[hour] * CFG["price_factor"], 4)))
            found += 1
        else:
            result.append((hour, None))

    log.info(f"Morgen-Preise: {found}/24 Stunden gefunden")

    if found == 0:
        log.warning("KEINE Preise fuer morgen! Auktion noch nicht veroeffentlicht?")
    elif found < 24:
        log.warning(f"Fehlende Stunden: {[h for h, p in result if p is None]}")

    if found > 0:
        u = CFG["price_unit"]
        log.info("+----------+--------------+")
        log.info(f"|  Stunde  | {u:>12s} |")
        log.info("+----------+--------------+")
        for hour, price in result:
            s = f"{price:>10.2f}" if price is not None else "     fehlt"
            log.info(f"|  {hour:02d}:00   | {s}   |")
        log.info("+----------+--------------+")
        valid = [p for _, p in result if p is not None]
        log.info(f"Min: {min(valid):.2f} | Max: {max(valid):.2f} | "
                 f"Schnitt: {sum(valid)/len(valid):.2f} {u}")

    return result


# ════════════════════════════════════════════════════════════════
#  BACnet/IP – Rohe UDP-Pakete
# ════════════════════════════════════════════════════════════════

OBJ_TYPE_AV = 2
PROP_PV = 85


def _pkt_write(instance, value, priority, invoke_id):
    """Baut WriteProperty-Paket."""
    apdu = bytearray([0x00, 0x04, invoke_id & 0xFF, 0x0F])
    oid = (OBJ_TYPE_AV << 22) | instance
    apdu.append(0x0C)
    apdu.extend(struct.pack(">I", oid))
    apdu.extend([0x19, PROP_PV])
    apdu.append(0x3E)
    apdu.append(0x44)
    apdu.extend(struct.pack(">f", value))
    apdu.append(0x3F)
    apdu.extend([0x49, priority & 0xFF])
    npdu = bytes([0x01, 0x04])
    bvlc = bytes([0x81, 0x0A]) + struct.pack(">H", 4 + len(npdu) + len(apdu))
    return bvlc + npdu + bytes(apdu)


def _pkt_read(instance, invoke_id):
    """Baut ReadProperty-Paket."""
    apdu = bytearray([0x00, 0x04, invoke_id & 0xFF, 0x0C])
    oid = (OBJ_TYPE_AV << 22) | instance
    apdu.append(0x0C)
    apdu.extend(struct.pack(">I", oid))
    apdu.extend([0x19, PROP_PV])
    npdu = bytes([0x01, 0x04])
    bvlc = bytes([0x81, 0x0A]) + struct.pack(">H", 4 + len(npdu) + len(apdu))
    return bvlc + npdu + bytes(apdu)


def _recv(sock, timeout=None):
    """Empfaengt Antwort vom Controller."""
    t = timeout or CFG["bacnet_timeout"]
    end = time.time() + t
    while True:
        left = end - time.time()
        if left <= 0:
            return None
        sock.settimeout(max(left, 0.1))
        try:
            data, addr = sock.recvfrom(1500)
            if addr[0] == CFG["controller_ip"]:
                return data
        except socket.timeout:
            return None


def _is_ack(data):
    """Prueft auf WriteProperty SimpleACK."""
    return data and len(data) >= 9 and (data[6] >> 4) == 2 and data[8] == 0x0F


def _read_float(data):
    """Extrahiert Float aus ReadProperty-Antwort."""
    if not data:
        return None
    for i in range(len(data) - 6):
        if data[i] == 0x3E and data[i+1] == 0x44 and data[i+6] == 0x3F:
            return round(struct.unpack(">f", data[i+2:i+6])[0], 4)
    return None


def _error_text(data):
    """Fehlerbeschreibung aus BACnet-Antwort."""
    if not data or len(data) < 7:
        return "Keine Antwort"
    t = (data[6] >> 4) & 0x0F
    n = {5: "ERROR", 6: "REJECT", 7: "ABORT"}.get(t, f"PDU-{t}")
    if t == 5 and len(data) > 11:
        return f"{n} (Class={data[9]}, Code={data[11]})"
    return n


class BACnetConnection:
    """
    Verwaltet die UDP-Verbindung zum BACnet-Controller.

    Verwendung:
        with BACnetConnection(log) as conn:
            conn.write(1000, 11.67)
            wert = conn.read(1000)
    """

    def __init__(self, log):
        self.log = log
        self.sock = None
        self.target = (CFG["controller_ip"], CFG["controller_port"])

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((CFG["local_ip"], CFG["local_port"]))
            self.log.debug(f"Socket: {CFG['local_ip']}:{CFG['local_port']}")
            return self
        except OSError as e:
            self.sock.close()
            raise ConnectionError(
                f"Port {CFG['local_port']} nicht verfuegbar: {e}"
            )

    def __exit__(self, *args):
        if self.sock:
            self.sock.close()
            self.log.debug("Socket geschlossen")

    def write(self, instance, value, invoke_id=1):
        """
        Schreibt einen Wert auf AV:instance.
        Versucht mehrfach bei Timeout.
        Gibt True/False zurueck.
        """
        for attempt in range(1, CFG["bacnet_retries"] + 1):
            iid = (invoke_id + attempt) & 0xFF
            pkt = _pkt_write(instance, value, CFG["priority"], iid)
            self.sock.sendto(pkt, self.target)

            data = _recv(self.sock)

            if data is None:
                self.log.warning(
                    f"  AV:{instance} Timeout "
                    f"({attempt}/{CFG['bacnet_retries']})"
                )
                if attempt < CFG["bacnet_retries"]:
                    time.sleep(0.5)
                continue

            if _is_ack(data):
                self.log.debug(f"  AV:{instance} = {value:.4f} OK")
                return True

            self.log.warning(
                f"  AV:{instance} Fehler: {_error_text(data)}"
            )
            return False

        self.log.error(
            f"  AV:{instance} FEHLGESCHLAGEN "
            f"nach {CFG['bacnet_retries']} Versuchen"
        )
        return False

    def read(self, instance, invoke_id=200):
        """Liest presentValue von AV:instance. Gibt float oder None."""
        pkt = _pkt_read(instance, invoke_id & 0xFF)
        self.sock.sendto(pkt, self.target)
        data = _recv(self.sock)
        return _read_float(data) if data else None


# ════════════════════════════════════════════════════════════════
#  HAUPTLOGIK
# ════════════════════════════════════════════════════════════════

def run_aktuell(conn, log):
    """Schreibt aktuellen Preis auf AV:1000."""
    log.info("── Aktuellen Preis abrufen ──")
    raw, conv, dt = get_current_price(log)
    ok = conn.write(CFG["av_aktuell"], conv, invoke_id=100)
    if ok:
        log.info(f"AV:{CFG['av_aktuell']} = {conv:.2f} {CFG['price_unit']}")
    else:
        log.error(f"AV:{CFG['av_aktuell']} Schreiben fehlgeschlagen")
    return ok


def run_morgen(conn, log):
    """Schreibt 24 Morgen-Preise + Status."""
    log.info("── Morgen-Preise abrufen ──")
    prices = get_tomorrow_prices(log)

    log.info("── Schreibe in Controller ──")
    erfolg = 0
    vorhanden = 0

    for hour, price in prices:
        av = CFG["av_morgen_start"] + hour
        if price is not None:
            value = price
            vorhanden += 1
        else:
            value = CFG["fehlwert"]

        if conn.write(av, value, invoke_id=hour + 1):
            erfolg += 1
        time.sleep(CFG["write_delay"])

    # Status/Watchdog
    conn.write(CFG["av_status"], float(vorhanden), invoke_id=50)

    log.info(f"Ergebnis: {erfolg}/24 geschrieben, {vorhanden}/24 Preise vorhanden")
    return erfolg == 24 and vorhanden > 0


def main():
    """
    Exit-Codes: 0=OK, 1=BACnet-Fehler, 2=SMARD-Fehler, 3=Keine Daten, 99=Sonstig
    """
    parser = argparse.ArgumentParser(
        description="SMARD-BACnet Gateway: Strompreise in den Controller schreiben"
    )
    parser.add_argument(
        "--modus",
        choices=["aktuell", "morgen", "alle"],
        default="alle",
        help="aktuell=AV:1000, morgen=AV:1001-1025, alle=beides (Standard)",
    )
    args = parser.parse_args()

    log = setup_logging()
    log.info("=" * 55)
    log.info(f"SMARD-BACnet Gateway v2.2 (Modus: {args.modus})")
    log.info(
        f"Controller: {CFG['controller_ip']}:{CFG['controller_port']} | "
        f"{CFG['price_unit']} | {CFG['smard_region']}"
    )

    exit_code = 0
    try:
        with BACnetConnection(log) as conn:
            if args.modus in ("aktuell", "alle"):
                if not run_aktuell(conn, log):
                    exit_code = max(exit_code, 3)

            if args.modus in ("morgen", "alle"):
                if not run_morgen(conn, log):
                    exit_code = max(exit_code, 3)

            # Verifikation
            rb = conn.read(CFG["av_aktuell"])
            if rb is not None:
                log.info(f"Verifikation AV:{CFG['av_aktuell']} = {rb}")

    except ConnectionError as e:
        log.error(f"BACnet: {e}")
        exit_code = 1
    except requests.ConnectionError as e:
        log.error(f"SMARD nicht erreichbar: {e}")
        exit_code = 2
    except requests.Timeout:
        log.error(f"SMARD Timeout ({CFG['smard_timeout']}s)")
        exit_code = 2
    except requests.RequestException as e:
        log.error(f"SMARD HTTP-Fehler: {e}")
        exit_code = 2
    except ValueError as e:
        log.error(f"Datenfehler: {e}")
        exit_code = 3
    except Exception as e:
        log.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        exit_code = 99

    log.info(f"Beendet (Exit-Code {exit_code})")
    log.info("=" * 55)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
