# 14783 Kamera-Proxy V0.2 (Prüffassung) – Einbau

Stand 10.11.2026. Baustein: `14783_kameraproxy.hslz` (HSL3), Kategorie „Visualisierung“, Kontext `hsl3.kameraproxy`.

## Was der Baustein macht
- Holt Standbilder und MJPEG-Ströme von bis zu 3 Kameras (Axis) mit Digest-/Basic-Anmeldung.
- Der HomeServer leitet `https://<HS>/kamera/` an den Baustein (Port 8095) weiter – gleiche Adresse und gleiches Zertifikat wie der HS.
- Der Browser muss sich nicht an der Kamera anmelden. Zugangsdaten stehen nur im Baustein.

## Einbau
1. Logikbausteine → Importieren → `14783_kameraproxy.hslz`.
2. Baustein auf ein Logikblatt ziehen und verdrahten:

| Eingang | Belegung |
|---|---|
| E1 Basis-Pfad (Text) | `kamera` |
| E2 Port (Zahl) | `8095` (nie 0, nie doppelt) |
| E3 Schlüssel (Text) | eigenes Kennwort |
| E4 Neustart / Auslöser (1 Bit) | beliebiges KO (Pflicht im Experten) |
| E5–E8 Kamera 1 (je Text) | Name `einfahrt`, Adresse `https://192.168.x.x` oder die ganze Bild-URL, z. B. `https://192.168.1.96/axis-cgi/jpg/image.cgi?resolution=1280x720&compression=25&camera=1` (resolution/compression/camera gelten dann als Vorgabe), Benutzer, Passwort |
| E9–E12 Kamera 2 | Name `hof`, … |
| E13–E16 Kamera 3 | Name `hasen`, … |

3. Übertragen.

## Prüfen (Prüffassung 0.2)
1. A1 Status zeigt „Bereit: /kamera/ (Port 8095), 3 Kamera(s)“.
2. Im Browser `https://<HS>/kamera/` öffnen, Schlüssel eingeben, „Prüfen“.
   - Oben steht das Prüfergebnis je Kamera (OK / HTTP 401 = Anmeldung falsch / Fehler).
   - Links: Standbild, schnell nachgeladen, mit Bildern pro Sekunde.
   - Rechts: MJPEG-Strom über den HS. **Wichtigste Frage: läuft er flüssig oder bleibt er stehen?**
3. Debug-Seite des HS: Last bei 1 und bei 3 gleichzeitig geöffneten Strömen.
4. Dasselbe über S1-Fernzugriff.

## Fehlersuche
Die Prüfseite zeigt je Kamera `http` (Antwort der Kamera), `detail` (Fehlertext der Kamera) und `ziel`:
- **401** – Benutzer oder Passwort falsch
- **400** – Kamera lehnt die Anfrage ab, Grund steht in `detail`
- **404** – den Pfad `/axis-cgi/jpg/image.cgi` gibt es nicht (keine Axis-Kamera?)
- Fehler ohne `http` – Kamera nicht erreichbar (IP, http/https)

## Änderungen
- 0.2: Datentyp in jedem Ein-/Ausgang · keine feste Auflösung mehr · bei HTTP 400 automatisch ohne Zusatz-Parameter · ganze Kamera-URL als Adresse möglich (resolution/compression/camera als Vorgabe) · Fehlertext der Kamera auf der Prüfseite
- 0.1: erste Prüffassung

## Danach im Kamera-Plugin (QC)
- Bild-Adresse: `https://<HS>/kamera/einfahrt.jpg?k=<Schlüssel>`
- MJPEG-Adresse: `https://<HS>/kamera/einfahrt.mjpg?k=<Schlüssel>`, Codec MJPEG
- Anmeldung „keine“, Benutzer/Passwort im Plugin leer lassen.

Der QC-Client (ab v0.9.2) zeigt dann in der Einzelansicht den Live-Strom.

## Sicherheit
Der Schlüssel steht in der Bild-Adresse und ist für jeden QC-Benutzer sichtbar. An der Kamera einen eigenen Benutzer nur mit Zuschauer-Recht anlegen.
