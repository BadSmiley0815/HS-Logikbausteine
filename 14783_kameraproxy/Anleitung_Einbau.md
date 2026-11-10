# 14783 Kamera-Proxy V0.1 (Prüffassung) – Einbau

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
| E1 Basis-Pfad | `kamera` |
| E2 Port | `8095` (nie 0, nie doppelt) |
| E3 Schlüssel | eigenes Kennwort |
| E4 Neustart / Auslöser | beliebiges KO (Pflicht im Experten) |
| E5–E8 Kamera 1 | Name `einfahrt`, Adresse `192.168.x.x` (oder `https://…`), Benutzer, Passwort |
| E9–E12 Kamera 2 | Name `hof`, … |
| E13–E16 Kamera 3 | Name `hasen`, … |

3. Übertragen.

## Prüfen (Prüffassung 0.1)
1. A1 Status zeigt „Bereit: /kamera/ (Port 8095), 3 Kamera(s)“.
2. Im Browser `https://<HS>/kamera/` öffnen, Schlüssel eingeben, „Prüfen“.
   - Oben steht das Prüfergebnis je Kamera (OK / HTTP 401 = Anmeldung falsch / Fehler).
   - Links: Standbild, schnell nachgeladen, mit Bildern pro Sekunde.
   - Rechts: MJPEG-Strom über den HS. **Wichtigste Frage: läuft er flüssig oder bleibt er stehen?**
3. Debug-Seite des HS: Last bei 1 und bei 3 gleichzeitig geöffneten Strömen.
4. Dasselbe über S1-Fernzugriff.

## Danach im Kamera-Plugin (QC)
- Bild-Adresse: `https://<HS>/kamera/einfahrt.jpg?k=<Schlüssel>`
- MJPEG-Adresse: `https://<HS>/kamera/einfahrt.mjpg?k=<Schlüssel>`, Codec MJPEG
- Anmeldung „keine“, Benutzer/Passwort im Plugin leer lassen.

Der QC-Client (ab v0.9.2) zeigt dann in der Einzelansicht den Live-Strom.

## Sicherheit
Der Schlüssel steht in der Bild-Adresse und ist für jeden QC-Benutzer sichtbar. An der Kamera einen eigenen Benutzer nur mit Zuschauer-Recht anlegen.
