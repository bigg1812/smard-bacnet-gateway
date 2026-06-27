#!/usr/bin/env python3
"""
enteliweb.py - Writer fuer die enteliWEB REST-API
=================================================
Schreibt Werte ueber HTTP in BACnet-Objekte, OHNE selbst BACnet zu sprechen.
enteliWEB uebersetzt den HTTP-Request in den BACnet-WriteProperty-Befehl.

Endpoint (laut Delta "Web Services and Interface Class API"):
  PUT  {proto}://{host}:{port}/enteliweb/api/.bacnet/{site}/{device}/{objekt}/present-value?priority=N&alt=json
  GET  ... (zum Verifizieren)
  Body (PUT): {"$base":"Real","value":"85.4"}
  Auth: HTTP Basic

VORAUSSETZUNG: enteliWEB mit lizenzierter Web-API.

Sicherheit:
  - dry_run=True sendet NICHTS, sondern loggt nur die Requests. Standard zum Testen.
  - priority bewusst waehlen (14 laesst manuelle Uebersteuerung im Controller zu).
  - Erst gegen ungenutzte Test-Objekte schreiben, nie gegen produktive Anlagen.
"""

import requests
from requests.auth import HTTPBasicAuth


class EnteliwebClient:
    """
    HTTP-Client fuer die enteliWEB REST-API.

    Verwendung:
        with EnteliwebClient(cfg, log) as ew:
            ew.write("analog-value,1000", 11.67)
            wert = ew.read("analog-value,1000")
    """

    def __init__(self, cfg, log):
        self.log = log
        self.cfg = cfg
        proto = cfg.get("protokoll", "http")
        host = cfg["host"]
        port = cfg.get("port", 80)
        # Port nur anhaengen, wenn nicht Standard
        if (proto == "http" and port == 80) or (proto == "https" and port == 443):
            netloc = host
        else:
            netloc = f"{host}:{port}"
        self.base = f"{proto}://{netloc}/enteliweb/api/.bacnet/{cfg['site']}/{cfg['device']}"
        self.auth = HTTPBasicAuth(cfg["benutzer"], cfg["passwort"])
        self.priority = cfg.get("priority", 14)
        self.timeout = cfg.get("http_timeout", 30)
        self.retries = cfg.get("http_retries", 3)
        self.dry_run = cfg.get("dry_run", True)
        self.verify_tls = cfg.get("verify_tls", True)
        self.session = None

    def __enter__(self):
        self.session = requests.Session()
        modus = "DRY-RUN (sendet nichts)" if self.dry_run else "LIVE"
        self.log.info(f"enteliWEB-Writer: {self.base}  [{modus}]")
        return self

    def __exit__(self, *args):
        if self.session:
            self.session.close()

    def _url(self, objekt, prop="present-value"):
        return f"{self.base}/{objekt}/{prop}?priority={self.priority}&alt=json"

    def write(self, objekt, value, basis="Real"):
        """
        Schreibt einen Wert auf {objekt}/present-value.

        objekt: z.B. "analog-value,1000"
        value:  Zahl
        basis:  BACnet-Datentyp ("Real" fuer AV, "Enumerated" fuer BV)
        Rueckgabe: True/False
        """
        url = self._url(objekt)
        body = {"$base": basis, "value": str(value)}

        if self.dry_run:
            self.log.info(f"  [DRY-RUN] PUT {url}")
            self.log.info(f"  [DRY-RUN] Body: {body}")
            return True

        for versuch in range(1, self.retries + 1):
            try:
                resp = self.session.put(
                    url, json=body, auth=self.auth,
                    timeout=self.timeout, verify=self.verify_tls,
                )
                if 200 <= resp.status_code < 300:
                    self.log.debug(f"  PUT {objekt} = {value} OK ({resp.status_code})")
                    return True
                self.log.warning(
                    f"  PUT {objekt} HTTP {resp.status_code}: {resp.text[:200]} "
                    f"(Versuch {versuch}/{self.retries})"
                )
            except requests.RequestException as e:
                self.log.warning(f"  PUT {objekt} Fehler: {e} (Versuch {versuch}/{self.retries})")
        self.log.error(f"  PUT {objekt} FEHLGESCHLAGEN nach {self.retries} Versuchen")
        return False

    # ------------------------------------------------------------------
    #  Pruef-Methoden (read-only) - fuer den --check-Modus.
    #  Diese senden IMMER echtes HTTP, auch im Dry-Run, weil sie genau die
    #  Verbindung testen sollen. Sie schreiben nie etwas (nur GET).
    # ------------------------------------------------------------------

    def _deute_status(self, status, text=""):
        """Uebersetzt einen HTTP-Status in Klartext."""
        if 200 <= status < 300:
            return "OK"
        texte = {
            401: "401 - Authentifizierung fehlgeschlagen (Benutzer/Passwort pruefen)",
            403: "403 - Verboten: Web-API-Lizenz fehlt oder keine Berechtigung",
            404: "404 - Nicht gefunden: Site / Device / Objekt pruefen",
        }
        return texte.get(status, f"HTTP {status}: {text[:150]}")

    def _get_pruefen(self, url):
        """GET mit Klartext-Fehlerdeutung. Rueckgabe: (ok, status_or_None, klartext)."""
        try:
            resp = self.session.get(url, auth=self.auth, timeout=self.timeout, verify=self.verify_tls)
        except requests.ConnectionError:
            return False, None, "Server nicht erreichbar - Routing/Firewall/VPN zwischen IPC und enteliWEB pruefen"
        except requests.Timeout:
            return False, None, f"Zeitueberschreitung nach {self.timeout}s - Server antwortet nicht"
        except requests.RequestException as e:
            return False, None, f"HTTP-Fehler: {e}"
        ok = 200 <= resp.status_code < 300
        return ok, resp.status_code, self._deute_status(resp.status_code, resp.text)

    def ping(self):
        """Stufe 1: Erreichbarkeit + Auth + Lizenz ueber das Device-Objekt."""
        return self._get_pruefen(f"{self.base}?alt=json")

    def probe(self, objekt):
        """Stufe 2: Ein Zielobjekt lesen (read-only) - existiert es, ist es lesbar?"""
        return self._get_pruefen(f"{self.base}/{objekt}/present-value?alt=json")

    def read(self, objekt):
        """Liest present-value zurueck (zur Verifikation). Gibt Rohtext oder None."""
        if self.dry_run:
            self.log.info(f"  [DRY-RUN] GET {self._url(objekt)} (uebersprungen)")
            return None
        try:
            resp = self.session.get(
                self._url(objekt), auth=self.auth,
                timeout=self.timeout, verify=self.verify_tls,
            )
            if 200 <= resp.status_code < 300:
                return resp.text
            self.log.warning(f"  GET {objekt} HTTP {resp.status_code}")
        except requests.RequestException as e:
            self.log.warning(f"  GET {objekt} Fehler: {e}")
        return None
