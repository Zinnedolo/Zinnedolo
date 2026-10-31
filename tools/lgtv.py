#!/usr/bin/env python3
"""Steuerskript für LG-Fernseher mit webOS (2014 und neuer) über das Heimnetz.

Nutzt die offizielle „Second Screen“-Schnittstelle des Fernsehers (WebSocket,
Port 3000/3001), dieselbe, die auch die LG-ThinQ-App verwendet.

Installation:   pip install aiowebostv
Erster Start:   python lgtv.py find      (Fernseher im Netz suchen)
                python lgtv.py pair      (Anfrage am TV mit „Zulassen“ bestätigen)
Danach z. B.:   python lgtv.py info | apps | close | restart | netcheck

Die Kopplung (IP, Client-Key, MAC-Adresse) wird in ~/.lgtv-claude.json gespeichert.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import platform
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

CONFIG = Path.home() / ".lgtv-claude.json"

# Häufige App-IDs. "lgtv.py apps" zeigt alle auf deinem Gerät installierten.
KNOWN_APPS = {
    "netflix": "netflix",
    "youtube": "youtube.leanback.v4",
    "prime": "amazon",
    "disney": "com.disney.disneyplus-prod",
    "appletv": "com.apple.appletv",
    "dazn": "dazn",
    "joyn": "joyn",
    "rtl+": "de.rtl.tvnow",
    "ard": "de.ard.mediathek",
    "zdf": "zdf.mediathek",
    "spotify": "spotify-beehive",
    "browser": "com.webos.app.browser",
    "tv": "com.webos.app.livetv",
    "einstellungen": "com.palm.app.settings",
}

# Tasten, die "lgtv.py key" kennt (Namen der webOS-Schnittstelle).
BUTTONS = [
    "HOME", "BACK", "UP", "DOWN", "LEFT", "RIGHT", "ENTER", "EXIT", "MENU", "INFO",
    "VOLUMEUP", "VOLUMEDOWN", "MUTE", "CHANNELUP", "CHANNELDOWN", "PLAY", "PAUSE",
    "STOP", "REWIND", "FASTFORWARD", "RED", "GREEN", "YELLOW", "BLUE",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "DASH", "ASTERISK",
]


# ---------------------------------------------------------------- Hilfen
def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2))
    try:
        CONFIG.chmod(0o600)
    except OSError:
        pass


def die(msg: str) -> None:
    print(f"Fehler: {msg}", file=sys.stderr)
    sys.exit(1)


def need_lib():
    try:
        from aiowebostv import WebOsClient  # noqa: F401
    except ImportError:
        die("Bibliothek fehlt. Bitte zuerst ausführen:  pip install aiowebostv")
    from aiowebostv import WebOsClient
    return WebOsClient


def ssdp_discover(timeout: float = 3.0) -> list[dict]:
    """Sucht LG-webOS-Fernseher per SSDP im lokalen Netz."""
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 2\r\n"
        "ST: urn:lge-com:service:webos-second-screen:1\r\n\r\n"
    ).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.5)
    found: dict[str, dict] = {}
    for _ in range(2):
        sock.sendto(msg, ("239.255.255.250", 1900))
    end = time.time() + timeout
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        text = data.decode(errors="replace")
        headers = {k.strip().upper(): v.strip() for k, _, v in
                   (line.partition(":") for line in text.split("\r\n")[1:]) if k}
        found[addr[0]] = {"ip": addr[0], "server": headers.get("SERVER", ""),
                          "location": headers.get("LOCATION", "")}
    sock.close()
    return list(found.values())


def send_wol(mac: str, ip: str | None = None) -> None:
    """Schickt ein Wake-on-LAN-Paket (Fernseher einschalten)."""
    mac_bytes = bytes.fromhex(re.sub(r"[^0-9A-Fa-f]", "", mac))
    if len(mac_bytes) != 6:
        die(f"Ungültige MAC-Adresse: {mac}")
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        targets = ["255.255.255.255"]
        if ip:
            targets.append(ip.rsplit(".", 1)[0] + ".255")
        for t in targets:
            for port in (9, 7):
                try:
                    s.sendto(packet, (t, port))
                except OSError:
                    pass


def port_open(ip: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


async def connect(cfg: dict, host: str | None = None, key: str | None = None):
    WebOsClient = need_lib()
    host = host or cfg.get("host")
    if not host:
        die("Kein Fernseher bekannt. Erst 'python lgtv.py find' und 'python lgtv.py pair' ausführen.")
    client = WebOsClient(host, key if key is not None else cfg.get("client_key"), connect_timeout=10)
    try:
        await client.connect()
    except Exception as e:  # noqa: BLE001
        try:
            await client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        if "Pair" in type(e).__name__:
            die("Kopplung abgelehnt oder nicht rechtzeitig bestätigt (der TV wartet nur ca. 10 Sekunden). "
                "Fernbedienung bereithalten und 'pair' noch einmal ausführen.")
        die(f"Keine Verbindung zu {host} ({type(e).__name__}: {e}). Ist der Fernseher an und im selben Netz?")
    return client


def find_app(client, query: str) -> tuple[str, str]:
    apps = client.tv_state.apps or {}
    q = query.lower()
    if q in KNOWN_APPS and KNOWN_APPS[q] in apps:
        return KNOWN_APPS[q], apps[KNOWN_APPS[q]].get("title", q)
    if query in apps:
        return query, apps[query].get("title", query)
    for app_id, app in apps.items():
        if q in str(app.get("title", "")).lower():
            return app_id, app["title"]
    die(f"App '{query}' nicht gefunden. 'python lgtv.py apps' listet alle installierten Apps.")


# ---------------------------------------------------------------- Befehle
def cmd_find(args) -> None:
    print("Suche LG-Fernseher im Netz (3 Sekunden) …")
    tvs = ssdp_discover()
    if not tvs:
        print("Nichts gefunden. Prüfe: Fernseher an? PC im selben Netz/WLAN wie der Fernseher?\n"
              "Alternativ IP am TV ablesen (Einstellungen › Allgemein › Netzwerk) und\n"
              "'python lgtv.py pair --host <IP>' verwenden.")
        return
    for tv in tvs:
        ports = [p for p in (3000, 3001) if port_open(tv["ip"], p)]
        print(f"- {tv['ip']}  {tv['server']}  Steuer-Ports offen: {ports or 'keine'}")
    if len(tvs) == 1:
        cfg = load_config()
        cfg["host"] = tvs[0]["ip"]
        save_config(cfg)
        print(f"IP {tvs[0]['ip']} gespeichert. Weiter mit: python lgtv.py pair")


async def cmd_pair(args) -> None:
    cfg = load_config()
    if args.host:
        cfg["host"] = args.host
    print("Verbinde … Bitte am Fernseher die Anfrage mit „Zulassen“ bzw. „Akzeptieren“ bestätigen.")
    client = await connect(cfg, key="")
    cfg["client_key"] = client.client_key
    sysinfo = client.tv_info.system or {}
    conn = client.tv_info.connection or {}
    mac = (conn.get("wiredInfo") or {}).get("macAddress") or (conn.get("wifiInfo") or {}).get("macAddress")
    if mac:
        cfg["mac"] = mac
    cfg["model"] = sysinfo.get("modelName")
    save_config(cfg)
    await client.disconnect()
    print(f"Gekoppelt mit {cfg.get('model') or 'Fernseher'} ({cfg['host']}). Schlüssel gespeichert in {CONFIG}.")
    if not mac:
        print("Hinweis: MAC-Adresse nicht ermittelt, 'on' und 'restart' brauchen sie (Option --mac).")


async def cmd_info(args) -> None:
    client = await connect(load_config())
    s, sw, c = client.tv_info.system, client.tv_info.software, client.tv_info.connection
    st = client.tv_state
    print(json.dumps({
        "modell": s.get("modelName"),
        "webos_version": sw.get("product_name") or sw.get("major_ver"),
        "firmware": f"{sw.get('major_ver')}.{sw.get('minor_ver')}" if sw.get("major_ver") else None,
        "aktive_app": st.current_app_id,
        "lautstaerke": st.volume,
        "stumm": st.muted,
        "tonausgabe": st.sound_output,
        "installierte_apps": len(st.apps or {}),
        "netzwerk": c,
    }, indent=2, ensure_ascii=False))
    await client.disconnect()


async def cmd_apps(args) -> None:
    client = await connect(load_config())
    for app_id, app in sorted((client.tv_state.apps or {}).items(), key=lambda x: str(x[1].get("title", "")).lower()):
        print(f"{app.get('title', '?'):35} {app_id}")
    await client.disconnect()


async def cmd_launch(args) -> None:
    client = await connect(load_config())
    app_id, title = find_app(client, args.app)
    await client.launch_app(app_id)
    print(f"{title} gestartet.")
    await client.disconnect()


async def cmd_close(args) -> None:
    """Schließt die laufende App und, mit --all, alle bekannten Streaming-Apps."""
    client = await connect(load_config())
    installed = client.tv_state.apps or {}
    targets = []
    current = client.tv_state.current_app_id
    if current and current not in ("com.webos.app.home", "com.webos.app.livetv"):
        targets.append(current)
    if args.all:
        targets += [a for a in KNOWN_APPS.values() if a in installed and a not in targets
                    and a not in ("com.webos.app.livetv", "com.palm.app.settings")]
    closed = []
    for app_id in targets:
        try:
            await client.close_app(app_id)
            closed.append(installed.get(app_id, {}).get("title", app_id))
        except Exception:  # noqa: BLE001  (App lief nicht)
            pass
    await client.button("HOME")
    print("Geschlossen: " + (", ".join(closed) if closed else "keine laufende App gefunden"))
    await client.disconnect()


async def cmd_key(args) -> None:
    client = await connect(load_config())
    for name in args.keys:
        name = name.upper()
        if name not in BUTTONS:
            die(f"Unbekannte Taste '{name}'. Bekannt: {', '.join(BUTTONS)}")
        await client.button(name)
        await asyncio.sleep(0.3)
    await client.disconnect()


async def cmd_text(args) -> None:
    client = await connect(load_config())
    await client.send_message(args.message)
    await client.disconnect()


async def cmd_off(args) -> None:
    client = await connect(load_config())
    await client.power_off()
    print("Fernseher ausgeschaltet.")


def cmd_on(args) -> None:
    cfg = load_config()
    mac = args.mac or cfg.get("mac")
    if not mac:
        die("MAC-Adresse unbekannt. Mit --mac angeben (steht am TV unter Allgemein › Netzwerk).")
    send_wol(mac, cfg.get("host"))
    print("Einschaltsignal gesendet. Klappt nur, wenn am TV „Über WLAN/LAN einschalten“ aktiv ist.")


async def cmd_restart(args) -> None:
    cfg = load_config()
    mac = args.mac or cfg.get("mac")
    if not mac:
        die("MAC-Adresse unbekannt. Erst 'pair' ausführen oder --mac angeben.")
    client = await connect(cfg)
    await client.power_off()
    print(f"Ausgeschaltet. Warte {args.wait} Sekunden, damit webOS den Speicher freigibt …")
    await asyncio.sleep(args.wait)
    for _ in range(3):
        send_wol(mac, cfg.get("host"))
        await asyncio.sleep(1)
    for _ in range(30):
        if port_open(cfg["host"], 3001) or port_open(cfg["host"], 3000):
            print("Fernseher ist wieder an.")
            return
        await asyncio.sleep(2)
    print("Fernseher hat sich nicht gemeldet. Prüfe, ob „Über WLAN/LAN einschalten“ aktiv ist,\n"
          "oder schalte ihn mit der Fernbedienung ein.")


async def cmd_netcheck(args) -> None:
    cfg = load_config()
    host = cfg.get("host") or die("Kein Fernseher bekannt. Erst 'find' ausführen.")
    print(f"Pinge {host} 20-mal …")
    flag = "-n" if platform.system() == "Windows" else "-c"
    try:
        out = subprocess.run(["ping", flag, "20", host], capture_output=True, text=True).stdout
    except FileNotFoundError:
        out = ""
        print("Programm 'ping' nicht gefunden, überspringe Messung der Antwortzeit.")
    loss = re.search(r"(\d+(?:[.,]\d+)?)\s*%", out)
    times = [float(t.replace(",", ".")) for t in re.findall(r"(?:time|Zeit)[=<]\s*([\d.,]+)", out)]
    loss_pct = float(loss.group(1).replace(",", ".")) if loss else None
    print(f"Paketverlust: {loss_pct if loss_pct is not None else '?'} %")
    if times:
        avg, worst = sum(times) / len(times), max(times)
        print(f"Antwortzeit: Ø {avg:.1f} ms, schlechteste {worst:.1f} ms")
    client = await connect(cfg)
    conn = client.tv_info.connection or {}
    await client.disconnect()
    wired = (conn.get("wiredInfo") or {}).get("state") == "connected"
    print(f"Verbindung des TVs: {'LAN-Kabel' if wired else 'WLAN'}")
    print("Rohdaten vom TV:", json.dumps(conn, ensure_ascii=False))
    verdict = "gut" if times else "ohne Ping-Messung nicht bewertbar"
    if loss_pct and loss_pct > 2 or times and max(times) > 150:
        verdict = "instabil: Router näher, 5-GHz-WLAN oder LAN-Kabel verwenden"
    elif times and sum(times) / len(times) > 30:
        verdict = "mittel: für 4K-Streaming eher knapp, 5 GHz oder LAN empfohlen"
    print(f"Bewertung: {verdict}")


# ---------------------------------------------------------------- Main
def main() -> None:
    p = argparse.ArgumentParser(description="LG-webOS-Fernseher über das Heimnetz steuern.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find", help="Fernseher im Netz suchen")
    sp = sub.add_parser("pair", help="mit dem Fernseher koppeln (einmalig)")
    sp.add_argument("--host", help="IP-Adresse, falls 'find' nichts findet")
    sub.add_parser("info", help="Modell, Software, aktive App, Netzwerk")
    sub.add_parser("apps", help="installierte Apps auflisten")
    sp = sub.add_parser("launch", help="App starten, z. B. netflix, youtube, prime")
    sp.add_argument("app")
    sp = sub.add_parser("close", help="laufende App schließen")
    sp.add_argument("--all", action="store_true", help="auch alle bekannten Streaming-Apps schließen")
    sp = sub.add_parser("key", help="Fernbedienungstasten senden, z. B. HOME BACK")
    sp.add_argument("keys", nargs="+")
    sp = sub.add_parser("text", help="Meldung auf dem Bildschirm anzeigen")
    sp.add_argument("message")
    sub.add_parser("off", help="ausschalten")
    sp = sub.add_parser("on", help="per Wake-on-LAN einschalten")
    sp.add_argument("--mac")
    sp = sub.add_parser("restart", help="aus, warten, wieder an (Speicher leeren)")
    sp.add_argument("--wait", type=int, default=20)
    sp.add_argument("--mac")
    sub.add_parser("netcheck", help="Netzwerkverbindung zum TV prüfen")
    args = p.parse_args()

    fn = globals()[f"cmd_{args.cmd}"]
    if asyncio.iscoroutinefunction(fn):
        asyncio.run(fn(args))
    else:
        fn(args)


if __name__ == "__main__":
    main()
