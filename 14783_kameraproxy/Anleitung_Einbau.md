# 14783 Kamera-Proxy V0.6 (Prüffassung) – Einbau

Stand 15.11.2026. Baustein: `14783_kameraproxy.hslz` (HSL3), Kategorie „Visualisierung“, Kontext `hsl3.kameraproxy`.

## Was der Baustein macht
- Holt Standbilder und MJPEG-Ströme von bis zu 6 Kameras (Axis, beliebige Standbild-Adresse oder ONVIF) mit Digest-/Basic-Anmeldung.
- Bietet eine Kamera keinen MJPEG-Strom, baut der Baustein ihn aus schnell nachgeladenen Standbildern.
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
| E5–E8 Kamera 1 (je Text) | Name `einfahrt`, Adresse (siehe unten), Benutzer, Passwort |
| E9–E12 Kamera 2 | Name `hof`, … |
| E13–E16 Kamera 3 | Name `hasen`, … |
| E17–E28 Kamera 4–6 | neu in 0.5, gleiche Reihenfolge |

3. Übertragen.

Beim Wechsel von 0.4: E1–E16 bleiben an ihrem Platz, E17–E28 kommen hinten dazu.

## Adresse der Kamera – drei Arten
| Eintrag | Art | Verhalten |
|---|---|---|
| `<Kamera>` oder `https://<Kamera>` | Axis | Standbild `/axis-cgi/jpg/image.cgi`, Strom `/axis-cgi/mjpg/video.cgi`. Braucht ein normales Axis-Konto. Mit `?resolution=1280x720&compression=25&camera=1` als Vorgabe. |
| `https://<Kamera>/pfad/bild.cgi?…` | Standbild-Adresse | Genau diese Adresse ist das Standbild, z. B. `https://<Kamera>/onvif-cgi/jpg/image.cgi?resolution=1280x720&compression=30`. Strom aus Standbildern. |
| `onvif://<Kamera>` | ONVIF | Der Baustein fragt Profile und Standbild-Adresse selbst ab (Benutzer = ONVIF-Konto). Erst https, dann http. Auflösung: `onvif://<Kamera>?resolution=1280x720` (ohne Angabe 1280x720). Strom aus Standbildern. |

- Selbst ausgestellte Zertifikate der Kamera werden angenommen.
- Axis führt ONVIF-Konten getrennt von normalen Konten: Ein ONVIF-Konto gilt für `onvif://…` und `/onvif-cgi/…`, nicht für `/axis-cgi/…`.
- Strom aus Standbildern: Vorgabe 8 Bilder/s, mit `&fps=…` 1 bis 15. RTSP/H.264 wird nicht umgewandelt, die RTSP-Adresse zeigt die Prüfseite nur an.

## Prüfen (Prüffassung 0.6)
1. A1 Status zeigt „Bereit: /kamera/ (Port 8095), n Kamera(s)“.
2. Im Browser `https://<HS>/kamera/` öffnen, Schlüssel eingeben, „Prüfen“.
   - Oben steht das Prüfergebnis je Kamera (OK / HTTP 401 = Anmeldung falsch / Fehler).
   - Links: Standbild, schnell nachgeladen, mit Bildern pro Sekunde.
   - Rechts: MJPEG-Strom über den HS. **Wichtigste Frage: läuft er flüssig oder bleibt er stehen?**
   - Bei ONVIF zeigt das Prüfergebnis `profile` (alle Profile der Kamera), `profil` (gewählt), `standbild`, `strom` (RTSP, nur Auskunft) und `uhr` (Abweichung der Kamera-Uhr).
3. Debug-Seite des HS: Last bei 1 und bei mehreren gleichzeitig geöffneten Strömen.
4. Dasselbe über S1-Fernzugriff.

## Fehlersuche
Die Prüfseite zeigt je Kamera `http` (Antwort der Kamera), `detail` (Fehlertext der Kamera) und `ziel`:
- **401** – Benutzer oder Passwort falsch
- **400** – Kamera lehnt die Anfrage ab, Grund steht in `detail`
- **404** – den Pfad gibt es nicht (keine Axis-Kamera? dann ganze Standbild-Adresse oder `onvif://…` eintragen)
- ONVIF: **400** mit „not authorized“ in `detail` – ONVIF-Konto oder Passwort falsch. Nach einem Fehler fragt der Baustein frühestens nach 15 s neu.
- Fehler ohne `http` – Kamera nicht erreichbar (IP, http/https)

## Änderungen
- 0.6: Prüfung zeigt bei ONVIF unter `standbild` die wirklich abgerufene Adresse (bisher die von der Kamera genannte)
- 0.5: Adresse mit Pfad wird als Standbild-Adresse übernommen (bisher wurde der Pfad verworfen) · ONVIF (`onvif://…`) mit wählbarer Auflösung · MJPEG-Strom aus Standbildern, wenn die Kamera keinen anbietet · 6 statt 3 Kameras · abgelehnte Parameter werden gemerkt
- 0.4: Weiterleitungen der Kamera (z. B. http → https) werden befolgt
- 0.3: Verbindung zur Kamera bleibt offen, Anmeldung wird gespeichert (Standbilder etwa doppelt so schnell) · `…/list` für den QC-Client
- 0.2: Datentyp in jedem Ein-/Ausgang · keine feste Auflösung mehr · bei HTTP 400 automatisch ohne Zusatz-Parameter · ganze Kamera-URL als Adresse möglich (resolution/compression/camera als Vorgabe) · Fehlertext der Kamera auf der Prüfseite
- 0.1: erste Prüffassung

## Im QC-Client (ab v0.9.3)
Im Experten bleibt das Kamera-Plugin unverändert. Im QC-Client links unter **Kamera-Proxy** einmal Adresse
(`https://<HS>/kamera/`) und Schlüssel eintragen. Kameras, deren Name im Plugin zum Namen im Baustein passt
(„Einfahrt“ → `einfahrt`), laufen dann über den Proxy: Übersicht mit Standbildern, Einzelansicht mit Live-Strom.

Direkte Adressen, z. B. für einen Browser oder ein anderes Programm:
- Standbild: `https://<HS>/kamera/einfahrt.jpg?k=<Schlüssel>`
- Live (MJPEG): `https://<HS>/kamera/einfahrt.mjpg?k=<Schlüssel>`

## Sicherheit
Der Schlüssel steht in der Bild-Adresse und ist für jeden QC-Benutzer sichtbar. An der Kamera einen eigenen Benutzer nur mit Zuschauer-Recht anlegen.
