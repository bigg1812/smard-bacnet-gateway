#!/usr/bin/env python3
"""
verbindungstest.py – Prüft ob der BACnet-Controller erreichbar ist
===================================================================
Fuehrt einen einfachen Lese- und Schreibtest durch.
Keine SMARD-API noetig – testet nur die BACnet-Verbindung.

Verwendung:
  python src/verbindungstest.py
"""

import socket
import struct
import subprocess
import sys
import time
import configparser
from pathlib import Path


def load_config():
    """Liest Netzwerk-Konfiguration aus einstellungen.ini."""
    cfg_file = Path(__file__).parent.parent / "config" / "einstellungen.ini"
    if not cfg_file.exists():
        print(f"  FEHLER: {cfg_file} nicht gefunden!")
        sys.exit(1)
    cp = configparser.ConfigParser()
    cp.read(cfg_file, encoding="utf-8")
    return {
        "controller_ip":   cp.get("netzwerk", "controller_ip"),
        "controller_port": cp.getint("netzwerk", "controller_port"),
        "local_ip":        cp.get("netzwerk", "local_ip"),
        "local_port":      cp.getint("netzwerk", "local_port"),
        "av_aktuell":      cp.getint("bacnet_objekte", "av_aktuell"),
        "priority":        cp.getint("bacnet_objekte", "priority"),
    }


def build_read(instance, invoke_id=1):
    apdu = bytearray([0x00, 0x04, invoke_id, 0x0C])
    oid = (2 << 22) | instance
    apdu.append(0x0C)
    apdu.extend(struct.pack(">I", oid))
    apdu.extend([0x19, 85])
    npdu = bytes([0x01, 0x04])
    bvlc = bytes([0x81, 0x0A]) + struct.pack(">H", 4 + len(npdu) + len(apdu))
    return bvlc + npdu + bytes(apdu)


def build_write(instance, value, priority, invoke_id=2):
    apdu = bytearray([0x00, 0x04, invoke_id, 0x0F])
    oid = (2 << 22) | instance
    apdu.append(0x0C)
    apdu.extend(struct.pack(">I", oid))
    apdu.extend([0x19, 85])
    apdu.append(0x3E)
    apdu.append(0x44)
    apdu.extend(struct.pack(">f", value))
    apdu.append(0x3F)
    apdu.extend([0x49, priority & 0xFF])
    npdu = bytes([0x01, 0x04])
    bvlc = bytes([0x81, 0x0A]) + struct.pack(">H", 4 + len(npdu) + len(apdu))
    return bvlc + npdu + bytes(apdu)


def recv(sock, controller_ip, timeout=5):
    end = time.time() + timeout
    while True:
        left = end - time.time()
        if left <= 0:
            return None
        sock.settimeout(max(left, 0.1))
        try:
            data, addr = sock.recvfrom(1500)
            if addr[0] == controller_ip:
                return data
        except socket.timeout:
            return None


def read_float(data):
    if not data:
        return None
    for i in range(len(data) - 6):
        if data[i] == 0x3E and data[i+1] == 0x44 and data[i+6] == 0x3F:
            return round(struct.unpack(">f", data[i+2:i+6])[0], 4)
    return None


def main():
    cfg = load_config()
    ip = cfg["controller_ip"]
    port = cfg["controller_port"]
    av = cfg["av_aktuell"]
    prio = cfg["priority"]

    print("")
    print("=" * 55)
    print("  SMARD-BACnet Gateway – Verbindungstest")
    print("=" * 55)
    print(f"  Controller:  {ip}:{port}")
    print(f"  Lokaler PC:  {cfg['local_ip']}:{cfg['local_port']}")
    print(f"  Test-Objekt: AV:{av}")
    print("")

    # ── 1. Ping ──
    print("[1/4] Ping...", end=" ", flush=True)
    try:
        r = subprocess.run(
            ["ping", "-n", "2", "-w", "2000", ip],
            capture_output=True, timeout=10,
        )
        if r.returncode == 0:
            print("OK")
        else:
            print("FEHLGESCHLAGEN")
            print(f"      Controller {ip} nicht erreichbar!")
            print(f"      Pruefen: Kabel, IP-Adresse, VLAN")
            return 1
    except Exception as e:
        print(f"Fehler: {e}")
        return 1

    # ── 2. Socket ──
    print(f"[2/4] UDP-Socket oeffnen (Port {cfg['local_port']})...", end=" ", flush=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((cfg["local_ip"], cfg["local_port"]))
        print("OK")
    except OSError as e:
        print(f"FEHLER: {e}")
        print(f"      Port {cfg['local_port']} ist belegt!")
        print(f"      Tipp: Laeuft das Skript bereits?")
        sock.close()
        return 1

    target = (ip, port)

    # ── 3. Read ──
    print(f"[3/4] Lese AV:{av}...", end=" ", flush=True)
    pkt = build_read(av)
    sock.sendto(pkt, target)
    data = recv(sock, ip)
    if data:
        val = read_float(data)
        if val is not None:
            print(f"OK (Wert: {val})")
        else:
            print(f"Antwort erhalten, Wert nicht lesbar")
            print(f"      Raw: {data.hex()}")
    else:
        print("TIMEOUT – Keine Antwort!")
        print(f"      Moegliche Ursachen:")
        print(f"        - Windows Firewall blockiert UDP auf Port {cfg['local_port']}")
        print(f"        - Controller antwortet nicht")
        print(f"      Tipp: Firewall-Regel anlegen:")
        print(f'        netsh advfirewall firewall add rule name="BACnet" dir=in action=allow protocol=UDP localport={cfg["local_port"]}')
        sock.close()
        return 1

    # ── 4. Write ──
    test_val = 88.88
    print(f"[4/4] Schreibe {test_val} auf AV:{av}...", end=" ", flush=True)
    pkt = build_write(av, test_val, prio)
    sock.sendto(pkt, target)
    data = recv(sock, ip)
    if data and len(data) >= 9 and (data[6] >> 4) == 2 and data[8] == 0x0F:
        print("OK (SimpleACK)")
    elif data:
        print(f"Antwort erhalten, aber kein ACK")
        print(f"      Raw: {data.hex()}")
        sock.close()
        return 1
    else:
        print("TIMEOUT")
        sock.close()
        return 1

    # ── Kontrolle ──
    time.sleep(0.5)
    pkt = build_read(av, invoke_id=3)
    sock.sendto(pkt, target)
    data = recv(sock, ip)
    verify = read_float(data) if data else None

    sock.close()

    print("")
    print("-" * 55)
    if verify is not None and abs(verify - test_val) < 0.01:
        print(f"  ERFOLG! AV:{av} = {verify}")
        print(f"  Die Verbindung funktioniert einwandfrei.")
        print("")
        print(f"  Naechster Schritt:")
        print(f"    python src/strompreis_bacnet.py --modus aktuell")
    elif verify is not None:
        print(f"  WARNUNG: Geschrieben={test_val}, Gelesen={verify}")
        print(f"  Moeglicherweise hat eine hoehere Priority den Wert.")
    else:
        print(f"  Schreiben hat geklappt (ACK), Read-Back nicht moeglich.")
        print(f"  Bitte in enteliWEB pruefen: AV:{av} = {test_val}?")

    print("-" * 55)
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
