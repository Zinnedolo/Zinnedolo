# Übergabe: LG-TV optimieren (für Claude Code auf dem PC)

## Ziel des Nutzers
Der Nutzer will seinen LG-Fernseher **OLED55CS9LA** mit Claude Code über das Heimnetz
steuern und aufräumen (Apps schließen, Neustart, WLAN prüfen) und danach von Hand optimal
einstellen. Kommunikation bitte auf **Deutsch**, einfach erklärt, Schritt für Schritt.
Vor Schritten, bei denen der Nutzer am Fernseher etwas tun muss, kurz Bescheid sagen.

## Der Fernseher
- Modell: **LG OLED55CS9LA**: 55 Zoll, OLED, Baujahr **2022**, **webOS 22**, technisch wie die C2-Serie
- Prozessor α9 Gen5, 4 × HDMI 2.1 (alle mit 4K/120 Hz, VRR, ALLM), eARC an HDMI 2
- Menüpfade (webOS 22): Bild › Bildmodus-Einstellungen …, Allgemein › System › Zusätzliche Einstellungen …,
  Allgemein › OLED Care …, Allgemein › Geräte › HDMI-Einstellungen …

## Was es schon gibt
- Webseite: **https://lg-tv-optimieren.vercel.app** (Vercel, deployt automatisch aus `main`)
- GitHub-Repo: **https://github.com/Zinnedolo/Zinnedolo** (Standard-Branch `main`)
  - `index.html`: fertige Seite (wird aus `src/content.html` gebaut)
  - `src/content.html`: Quelle der Seite; nach Änderungen `./build.sh` ausführen
  - `tools/lgtv.py`: Steuerskript (wird von `build.sh` auch in die Seite eingebettet)
- Skript direkt: https://lg-tv-optimieren.vercel.app/tools/lgtv.py

## Das Steuerskript `tools/lgtv.py`
Voraussetzung: Python 3.10+, `pip install aiowebostv`. PC und TV im selben Netz.
Kopplung (IP, Client-Key, MAC) wird in `~/.lgtv-claude.json` gespeichert.

| Befehl | Zweck |
|---|---|
| `python lgtv.py find` | TV per SSDP suchen, Ports 3000/3001 prüfen, IP speichern |
| `python lgtv.py pair [--host IP]` | einmalig koppeln, am TV **„Zulassen“ innerhalb ~10 s** |
| `python lgtv.py info` | Modell, webOS-Version, aktive App, Lautstärke, Netzwerk |
| `python lgtv.py apps` | installierte Apps mit IDs |
| `python lgtv.py launch netflix` | App starten (Name, Kurzname oder ID) |
| `python lgtv.py close --all` | laufende App + bekannte Streaming-Apps schließen |
| `python lgtv.py key HOME BACK …` | Fernbedienungstasten senden |
| `python lgtv.py text "…"` | Meldung auf dem TV anzeigen |
| `python lgtv.py off` / `on` | aus / per Wake-on-LAN an |
| `python lgtv.py restart [--wait 20]` | aus, warten, per Wake-on-LAN wieder an |
| `python lgtv.py netcheck` | Ping (Verlust/Antwortzeit) + Netzwerkinfo des TVs, mit Bewertung |

**Wichtig:** Das Skript wurde bisher **nur gegen einen simulierten Fernseher** getestet, noch nie
an einem echten LG. Fehler beim ersten echten Lauf sind möglich: Ausgabe lesen, Ursache finden,
Skript im Repo korrigieren.

## Ablauf (Schritte der Webseite)
1. **01 Finden:** `find`. Findet es nichts: PC im Gäste-WLAN? IP am TV ablesen
   (Einstellungen › Allgemein › Netzwerk) und `pair --host <IP>` verwenden.
2. **02 Koppeln:** vorher am TV „TV einschalten mit Mobilgerät“ / „Über WLAN einschalten“
   aktivieren (Allgemein › Geräte › Externe Geräte …). Dann `pair`, Nutzer drückt „Zulassen“.
   Scheitert es mit Zeitüberschreitung: einfach noch einmal ausführen.
3. **03 Steuerskript:** `info` und `apps` zeigen; ungenutzte Apps vorschlagen.
4. **04 Apps schließen:** `close --all`.
5. **05 Neustart:** `restart`. Wake-on-LAN über WLAN klappt nicht immer (besonders wenn
   Schnellstart+ aus ist). Dann Nutzer mit der Fernbedienung einschalten lassen.
   Einen echten Software-Neustart bietet die Schnittstelle nicht.
6. **06 WLAN prüfen:** `netcheck`; für 4K-HDR stabil ~25 Mbit/s, sonst 5 GHz oder LAN empfehlen.
7. **07 Einstellungen von Hand** (Checkliste auf der Webseite, Modellnummer eingeben).
   Kernpunkte für den OLED55CS9LA:
   - Bildmodus: Filmmaker Mode (dunkel) / ISF Expert Heller Raum (hell)
   - Farbtemperatur Warm 50, AI Picture Pro aus, Energiesparschritt aus
   - TruMotion bei Filmen aus oder Kino-Clear
   - Live Plus aus (Allgemein › System › Zusätzliche Einstellungen), Benutzervereinbarungen
     (Anzeigeinfos, Werbung, Sprachinfos) abwählen, Home-Promotion aus
   - Gaming: HDMI Ultra HD Deep Colour an, Spiel-Optimierer mit VRR/ALLM, HDR-Tone-Mapping HGiG
   - OLED: TV nicht per Steckdosenleiste ausschalten (Pixel-Auffrischung), Bildverschiebung an,
     Logo-Helligkeit niedrig
8. **08 Router-Sperre (Fritzbox, optional):** Internet › Filter › Listen › Gesperrte Internetseiten:
   `lgsmartad.com`, `lgad.cjpowercast.com.edgesuite.net`, `ad.lgappstv.com`, `ngfts.lge.com`, `alphonso.tv`.
   Zugangsprofil „LG-TV“ mit dieser Sperrliste anlegen und unter Kindersicherung dem TV zuweisen.
   **Nicht** sperren: `lgtvsdp.com`, `lgappstv.com`, `snu.lge.com` (App-Store, Login, Updates).
   Diese Liste stammt aus Community-Quellen und ist nicht von LG bestätigt.

## Offene Aufgaben
- [ ] Schritte 01–06 am echten Fernseher durchführen und Ergebnisse dem Nutzer erklären
- [ ] Fehler im Skript, die dabei auftauchen, in `tools/lgtv.py` beheben, `./build.sh` ausführen,
      committen und nach `main` pushen (Vercel aktualisiert die Seite dann automatisch)
- [ ] Menüpfade, die am echten TV anders heißen, in `src/content.html` korrigieren

## Hinweise
- Keine Tokens oder Passwörter in Chats oder Dateien schreiben. `~/.lgtv-claude.json` enthält den
  Client-Key des TVs und gehört nicht ins Repo.
- Seite ist eine einzelne statische HTML-Datei ohne Framework; Vercel braucht keinen Build-Befehl.
