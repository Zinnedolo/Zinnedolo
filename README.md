# LG-TV optimieren

Eine einzelne Webseite mit empfohlenen Bild-, HDR-, Bewegungs-, Gaming-, Ton-, Datenschutz- und OLED-Pflege-Einstellungen für LG-Fernseher mit webOS (Baujahr 2020–2025).

- Modellnummer eingeben (z. B. `OLED55C47LA`, `50QNED816RE`, `43UR78006LK`): Bildschirmtyp und Baujahr werden erkannt, Werte und Menüpfade passen sich an.
- Einstellungen abhaken; der Fortschritt wird lokal im Browser gespeichert.

## Aufbau

- `src/content.html` – Quelle (Styles, Inhalt, Script)
- `build.sh` – erzeugt daraus `index.html`
- `index.html` – fertige Seite, direkt auf Vercel / GitHub Pages deploybar (keine Build-Schritte nötig)
