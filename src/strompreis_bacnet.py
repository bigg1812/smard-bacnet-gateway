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
        "bv_status":       cp.getint("bacnet_objekte", "bv_status", fallback=cp.getint("bacnet_objekte", "av_status", fallback=1025)),
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
OBJ_TYPE_BV = 5
PROP_PV = 85


def _pkt_write(obj_type, instance, value, priority, invoke_id):
    """Baut WriteProperty-Paket fuer AV (Real/Float) oder BV (Enumerated)."""
    apdu = bytearray([0x00, 0x04, invoke_id & 0xFF, 0x0F])
    oid = (obj_type << 22) | instance
    apdu.append(0x0C)
    apdu.extend(struct.pack(">I", oid))
    apdu.extend([0x19, PROP_PV])
    apdu.append(0x3E)
    
    if obj_type == OBJ_TYPE_BV:
        # Enumerated (Tag 9) fuer BV Present_Value
        apdu.append(0x91)
        apdu.append(int(value) & 0xFF)
    else:
        # Real/Float (Tag 4) fuer AV Present_Value
        apdu.append(0x44)
        apdu.extend(struct.pack(">f", float(value)))
        
    apdu.append(0x3F)
    apdu.extend([0x49, priority & 0xFF])
    npdu = bytes([0x01, 0x04])
    bvlc = bytes([0x81, 0x0A]) + struct.pack(">H", 4 + len(npdu) + len(apdu))
    return bvlc + npdu + bytes(apdu)


def _pkt_read(obj_type, instance, invoke_id):
    """Baut ReadProperty-Paket."""
    apdu = bytearray([0x00, 0x04, invoke_id & 0xFF, 0x0C])
    oid = (obj_type << 22) | instance
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


def _read_value(data):
    """Extrahiert Float (AV) oder Int (BV) aus ReadProperty-Antwort."""
    if not data:
        return None
    for i in range(len(data) - 2):
        if data[i] == 0x3E:  # Opening tag
            for j in range(i + 2, len(data)):
                if data[j] == 0x3F:  # Closing tag
                    tag_byte = data[i+1]
                    val_bytes = data[i+2:j]
                    tag_num = tag_byte >> 4
                    is_app_tag = (tag_byte & 0x08) == 0
                    if is_app_tag:
                        if tag_num == 4 and len(val_bytes) == 4:  # Real/Float
                            return round(struct.unpack(">f", val_bytes)[0], 4)
                        elif tag_num == 9 and len(val_bytes) == 1:  # Enumerated
                            return int(val_bytes[0])
                        elif tag_num == 2 and len(val_bytes) == 1:  # Unsigned
                            return int(val_bytes[0])
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

    def write(self, obj_type, instance, value, invoke_id=1):
        """
        Schreibt einen Wert auf AV:instance (Float) oder BV:instance (Enumerated).
        Versucht mehrfach bei Timeout.
        Gibt True/False zurueck.
        """
        for attempt in range(1, CFG["bacnet_retries"] + 1):
            iid = (invoke_id + attempt) & 0xFF
            pkt = _pkt_write(obj_type, instance, value, CFG["priority"], iid)
            self.sock.sendto(pkt, self.target)

            data = _recv(self.sock)
            type_str = "BV" if obj_type == OBJ_TYPE_BV else "AV"

            if data is None:
                self.log.warning(
                    f"  {type_str}:{instance} Timeout "
                    f"({attempt}/{CFG['bacnet_retries']})"
                )
                if attempt < CFG["bacnet_retries"]:
                    time.sleep(0.5)
                continue

            if _is_ack(data):
                val_str = f"{value}" if obj_type == OBJ_TYPE_BV else f"{value:.4f}"
                self.log.debug(f"  {type_str}:{instance} = {val_str} OK")
                return True

            self.log.warning(
                f"  {type_str}:{instance} Fehler: {_error_text(data)}"
            )
            return False

        type_str = "BV" if obj_type == OBJ_TYPE_BV else "AV"
        self.log.error(
            f"  {type_str}:{instance} FEHLGESCHLAGEN "
            f"nach {CFG['bacnet_retries']} Versuchen"
        )
        return False

    def read(self, obj_type, instance, invoke_id=200):
        """Liest presentValue von obj_type:instance. Gibt Wert (float/int) oder None."""
        pkt = _pkt_read(obj_type, instance, invoke_id & 0xFF)
        self.sock.sendto(pkt, self.target)
        data = _recv(self.sock)
        return _read_value(data) if data else None


# ════════════════════════════════════════════════════════════════
#  HAUPTLOGIK
# ════════════════════════════════════════════════════════════════

def run_aktuell(conn, log):
    """Schreibt aktuellen Preis auf AV:1000."""
    log.info("── Aktuellen Preis abrufen ──")
    raw, conv, dt = get_current_price(log)
    ok = conn.write(OBJ_TYPE_AV, CFG["av_aktuell"], conv, invoke_id=100)
    if ok:
        log.info(f"AV:{CFG['av_aktuell']} = {conv:.2f} {CFG['price_unit']}")
    else:
        log.error(f"AV:{CFG['av_aktuell']} Schreiben fehlgeschlagen")
    return ok


def run_morgen(conn, log):
    """Prueft ob die Preise fuer morgen vorliegen und schreibt den Status auf BV:status."""
    log.info("── Status der Morgen-Preise pruefen ──")
    status_ok = False
    try:
        prices = get_tomorrow_prices(log)
        vorhanden = sum(1 for hour, price in prices if price is not None)
        if vorhanden == 24:
            log.info("Alle 24 Preise fuer morgen erfolgreich geladen.")
            status_ok = True
        else:
            log.warning(f"Es liegen nur {vorhanden}/24 Preise fuer morgen vor.")
    except Exception as e:
        log.error(f"Fehler beim Laden der Morgen-Preise: {e}")
        status_ok = False

    # Wert fuer BV bestimmen (1.0 = Aktiv/True, 0.0 = Inaktiv/False)
    val = 1.0 if status_ok else 0.0
    log.info(f"Schreibe Status auf BV:{CFG['bv_status']} = {val}")
    ok = conn.write(OBJ_TYPE_BV, CFG["bv_status"], val, invoke_id=50)
    if ok:
        log.info(f"BV:{CFG['bv_status']} erfolgreich geschrieben.")
    else:
        log.error(f"BV:{CFG['bv_status']} Schreiben fehlgeschlagen.")
    
    return ok


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
        help="aktuell=AV:aktuell, morgen=BV:status (Preise für morgen da?), alle=beides (Standard)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur Preise von SMARD laden und im Terminal anzeigen (kein BACnet)",
    )
    args = parser.parse_args()

    log = setup_logging()
    log.info("=" * 55)
    log.info(f"SMARD-BACnet Gateway v2.2 (Modus: {args.modus})")
    log.info(
        f"Controller: {CFG['controller_ip']}:{CFG['controller_port']} | "
        f"{CFG['price_unit']} | {CFG['smard_region']}"
    )

    if args.dry_run:
        log.info("=== DRY-RUN MODUS: Keine BACnet-Uebertragung ===")
        exit_code = 0
        try:
            if args.modus in ("aktuell", "alle"):
                log.info("── Aktuellen Preis abrufen ──")
                get_current_price(log)
            if args.modus in ("morgen", "alle"):
                log.info("── Status der Morgen-Preise pruefen ──")
                get_tomorrow_prices(log)
            log.info("Dry-Run erfolgreich beendet.")
        except Exception as e:
            log.error(f"Fehler im Dry-Run: {e}")
            exit_code = 99
        log.info("=" * 55)
        return exit_code

    exit_code = 0
    try:
        with BACnetConnection(log) as conn:
            try:
                if args.modus in ("aktuell", "alle"):
                    if not run_aktuell(conn, log):
                        exit_code = max(exit_code, 3)
                        # Wenn die Aktualisierung des aktuellen Preises fehlschlaegt,
                        # setzen wir den Status auf 0 (Fehler)
                        conn.write(OBJ_TYPE_BV, CFG["bv_status"], 0.0, invoke_id=99)

                if args.modus in ("morgen", "alle"):
                    if not run_morgen(conn, log):
                        exit_code = max(exit_code, 3)
            except (requests.RequestException, ValueError) as api_err:
                log.error(f"Fehler bei der SMARD-API-Abfrage: {api_err}")
                # Im Fehlerfall versuchen wir den Fehlerstatus (0.0) an den Controller zu uebertragen
                conn.write(OBJ_TYPE_BV, CFG["bv_status"], 0.0, invoke_id=99)
                raise

            # Verifikation
            rb = conn.read(OBJ_TYPE_AV, CFG["av_aktuell"])
            if rb is not None:
                log.info(f"Verifikation AV:{CFG['av_aktuell']} = {rb}")

            rb_status = conn.read(OBJ_TYPE_BV, CFG["bv_status"])
            if rb_status is not None:
                log.info(f"Verifikation BV:{CFG['bv_status']} = {rb_status}")

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
