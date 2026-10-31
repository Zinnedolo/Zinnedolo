# LG-TV optimieren

Anleitung und Werkzeug, um einen LG-Fernseher mit webOS aufzuräumen und richtig einzustellen.

**Mit Claude Code** (über das Heimnetz, Skript `tools/lgtv.py`):
01 Finden · 02 Koppeln · 03 Steuerskript · 04 Apps schließen · 05 Neustart · 06 WLAN prüfen

**Von Hand:**
07 Einstellungen (Checkliste mit Modellerkennung, z. B. `OLED55CS9LA`) · 08 Router-Sperre (Fritzbox)

## Steuerskript

```sh
pip install aiowebostv
python tools/lgtv.py find        # Fernseher suchen
python tools/lgtv.py pair        # einmalig koppeln, am TV „Zulassen“ drücken (ca. 10 s Zeit)
python tools/lgtv.py info | apps | launch netflix | close --all | key HOME | off | on | restart | netcheck
```

Die Kopplung wird in `~/.lgtv-claude.json` gespeichert.

## Aufbau

- `src/content.html` – Seite (Styles, Inhalt, Script)
- `tools/lgtv.py` – Steuerskript; `build.sh` bettet es in die Seite ein
- `build.sh` – erzeugt `index.html`
- `index.html` – fertige Seite, direkt auf Vercel / GitHub Pages deploybar
