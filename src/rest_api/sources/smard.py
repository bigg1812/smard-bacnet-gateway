#!/usr/bin/env python3
"""
sources/smard.py - Strompreise von der SMARD-Plattform (Bundesnetzagentur)
==========================================================================
Holt Day-Ahead Grosshandelspreise. Oeffentliche API, kostenlos, kein Key.

Diese Datei kennt KEIN BACnet und KEINE REST-API. Sie liefert nur Zahlen.
Das Schreiben uebernimmt der Writer (enteliweb.py).
"""

import time
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ_BERLIN = ZoneInfo("Europe/Berlin")
except Exception:
    TZ_BERLIN = None

import requests

SMARD_BASE = "https://www.smard.de/app/chart_data"
_HOUR_MS = 3_600_000


# ----------------------------------------------------------------------
#  Zeitzone
# ----------------------------------------------------------------------

def _berlin_offset():
    """UTC-Offset fuer Berlin (CET +1 / CEST +2), falls zoneinfo fehlt."""
    now = datetime.now(timezone.utc)
    y = now.year
    d = datetime(y, 3, 31, 1, tzinfo=timezone.utc)
    dst_start = d - timedelta(days=(d.weekday() + 1) % 7)
    d = datetime(y, 10, 31, 1, tzinfo=timezone.utc)
    dst_end = d - timedelta(days=(d.weekday() + 1) % 7)
    return timezone(timedelta(hours=2)) if dst_start <= now < dst_end else timezone(timedelta(hours=1))


def _berlin_tz():
    return TZ_BERLIN or _berlin_offset()


def _tomorrow_midnight_utc_ms():
    """UTC-Timestamp in ms fuer morgen 00:00 Berliner Zeit."""
    now = datetime.now(_berlin_tz())
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=_berlin_tz())
    return int(midnight.timestamp() * 1000)


# ----------------------------------------------------------------------
#  SMARD-API Roh-Zugriff
# ----------------------------------------------------------------------

def _index(filter_id, region, timeout, log):
    url = f"{SMARD_BASE}/{filter_id}/{region}/index_hour.json"
    log.debug(f"SMARD Index: {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    ts = r.json().get("timestamps", [])
    if not ts:
        raise ValueError("SMARD-Index leer")
    return ts


def _block(filter_id, region, block_ts, timeout, log):
    url = f"{SMARD_BASE}/{filter_id}/{region}/{filter_id}_{region}_hour_{block_ts}.json"
    log.debug(f"SMARD Block: {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json().get("series", [])


# ----------------------------------------------------------------------
#  Oeffentliche Funktionen
# ----------------------------------------------------------------------

def get_current_price(cfg, log):
    """
    Preis fuer die aktuelle Stunde.

    cfg erwartet: filter_id, region, timeout, faktor, einheit
    Rueckgabe: (rohpreis_eur_mwh, konvertierter_preis, zeitpunkt_utc)
    """
    fid, reg, to = cfg["filter_id"], cfg["region"], cfg["timeout"]
    timestamps = _index(fid, reg, to, log)
    now_ms = int(time.time() * 1000)

    for bts in reversed(timestamps[-3:]):
        for ts, price in _block(fid, reg, bts, to, log):
            if price is not None and ts <= now_ms < ts + _HOUR_MS:
                conv = round(price * cfg["faktor"], 4)
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                local = dt.astimezone(_berlin_tz())
                log.info(f"Aktueller Preis: {price:.2f} EUR/MWh = {conv:.2f} {cfg['einheit']} "
                         f"({local.strftime('%d.%m.%Y %H:%M')})")
                return price, conv, dt

    # Fallback: letzter bekannter Wert
    log.warning("Kein Preis fuer aktuelle Stunde - nutze letzten bekannten")
    for bts in reversed(timestamps[-2:]):
        for ts, price in reversed(_block(fid, reg, bts, to, log)):
            if price is not None:
                conv = round(price * cfg["faktor"], 4)
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                return price, conv, dt

    raise ValueError("Kein Preis verfuegbar")


def get_tomorrow_prices(cfg, log):
    """
    24 Stundenpreise fuer morgen.

    Rueckgabe: Liste mit 24 Tupeln [(stunde_0_23, konvertierter_preis_oder_None), ...]
    """
    fid, reg, to = cfg["filter_id"], cfg["region"], cfg["timeout"]
    timestamps = _index(fid, reg, to, log)
    start_ms = _tomorrow_midnight_utc_ms()
    end_ms = start_ms + 24 * _HOUR_MS

    raw = [None] * 24
    for bts in reversed(timestamps[-5:]):
        if bts > end_ms:
            continue
        for ts, price in _block(fid, reg, bts, to, log):
            if price is not None and start_ms <= ts < end_ms:
                idx = (ts - start_ms) // _HOUR_MS
                if 0 <= idx < 24:
                    raw[idx] = price
        if all(p is not None for p in raw):
            break

    result = [(h, round(raw[h] * cfg["faktor"], 4) if raw[h] is not None else None)
              for h in range(24)]
    found = sum(1 for _, p in result if p is not None)
    log.info(f"Morgen-Preise: {found}/24 Stunden gefunden")
    if found == 0:
        log.warning("KEINE Preise fuer morgen - Auktion noch nicht veroeffentlicht?")
    return result
