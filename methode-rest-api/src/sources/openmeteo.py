#!/usr/bin/env python3
"""
sources/openmeteo.py - Wetterprognose von Open-Meteo
====================================================
Oeffentliche API, kostenlos, kein API-Key. Passt zur Philosophie von SMARD.
Doku: https://open-meteo.com/en/docs

Liefert stuendliche Prognosewerte, z.B.:
  temperature_2m       Lufttemperatur 2 m  (Grad C)   -> Heizungssteuerung
  shortwave_radiation  Globalstrahlung     (W/m2)     -> PV-Ertragsschaetzung
  cloud_cover          Bewoelkung          (%)
  wind_speed_10m       Windgeschwindigkeit (km/h)

Diese Datei kennt KEIN BACnet und KEINE REST-API. Sie liefert nur Zahlen.
"""

from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    TZ_BERLIN = ZoneInfo("Europe/Berlin")
except Exception:
    TZ_BERLIN = None

import requests

OPENMETEO_BASE = "https://api.open-meteo.com/v1/forecast"


def get_forecast(cfg, log):
    """
    Holt die Wetterprognose fuer einen Standort.

    cfg erwartet: latitude, longitude, werte (Liste von Variablennamen),
                  timeout, forecast_days (optional, default 2)
    Rueckgabe: dict {
        "aktuell":  {variable: wert, ...},          # aktuelle Stunde
        "stunden":  [(iso_zeit, {variable: wert}), ...],
    }
    """
    variables = cfg["werte"]
    params = {
        "latitude": cfg["latitude"],
        "longitude": cfg["longitude"],
        "hourly": ",".join(variables),
        "timezone": "Europe/Berlin",
        "forecast_days": cfg.get("forecast_days", 2),
    }
    log.debug(f"Open-Meteo: {OPENMETEO_BASE} {params}")
    r = requests.get(OPENMETEO_BASE, params=params, timeout=cfg["timeout"])
    r.raise_for_status()
    data = r.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("Open-Meteo: keine stuendlichen Daten erhalten")

    # Stundenliste aufbauen
    stunden = []
    for i, t in enumerate(times):
        werte = {v: hourly.get(v, [None] * len(times))[i] for v in variables}
        stunden.append((t, werte))

    # Aktuelle Stunde finden (Berliner Zeit, auf volle Stunde gerundet)
    now = datetime.now(TZ_BERLIN or timezone.utc)
    schluessel = now.strftime("%Y-%m-%dT%H:00")
    aktuell = {}
    for t, werte in stunden:
        if t == schluessel:
            aktuell = werte
            break
    if not aktuell and stunden:
        aktuell = stunden[0][1]  # Fallback: erste verfuegbare Stunde

    teile = ", ".join(f"{k}={v}" for k, v in aktuell.items())
    log.info(f"Wetter aktuell ({schluessel}): {teile}")
    return {"aktuell": aktuell, "stunden": stunden}
