## Wozu

Ein Browser kann sich an einer Netzwerkkamera nicht still anmelden, kann kein RTSP und stört sich am selbst ausgestellten Zertifikat der Kamera. Der Baustein holt die Bilder deshalb selbst von der Kamera und reicht sie über den HomeServer weiter:

- Der Browser spricht nur mit dem HomeServer (`https://<HS>/kamera/…`) und braucht nur einen Schlüssel.
- Benutzer und Passwort der Kamera stehen nur im Baustein und werden nie ausgegeben.
- Bis zu 6 Kameras je Baustein.

## Adresse der Kamera – drei Arten

Die Art ergibt sich aus dem Eintrag in „Adresse“ (E6, E10, E14, E18, E22, E26):

| Eintrag | Art | Verhalten |
|---|---|---|
| `<Kamera>` oder `https://<Kamera>` | Axis | Standbild `/axis-cgi/jpg/image.cgi`, Live-Bild `/axis-cgi/mjpg/video.cgi` (MJPEG der Kamera, unverändert durchgereicht). Braucht ein normales Axis-Konto. |
| `https://<Kamera>/pfad/bild.jpg?…` | Standbild-Adresse | Genau diese Adresse wird als Standbild abgerufen, alle Parameter bleiben erhalten. Live-Bild aus Standbildern. |
| `onvif://<Kamera>` | ONVIF | Der Baustein fragt die Kamera nach Profilen und Standbild-Adresse. Erst https, dann http. Live-Bild aus Standbildern. |

`<Kamera>` steht für IP-Adresse oder Name der Kamera, bei Bedarf mit Port (`<Kamera>:8080`).

### Beispiele für „Adresse“

| Eintrag | Wirkung |
|---|---|
| `https://<Kamera>` | Axis über https, Auflösung wie in der Kamera eingestellt |
| `https://<Kamera>?resolution=1280x720&compression=25` | Axis mit Vorgabe für Auflösung und Kompression |
| `https://<Kamera>?camera=2` | Axis-Mehrkanalgerät, zweiter Kanal |
| `https://<Kamera>/onvif-cgi/jpg/image.cgi?resolution=1280x720&compression=30` | Axis mit ONVIF-Konto, feste Standbild-Adresse |
| `http://<Kamera>/snapshot.jpg` | beliebige Kamera mit Bild-URL |
| `onvif://<Kamera>` | ONVIF, Standbild in etwa 1280×720 |
| `onvif://<Kamera>?resolution=960x540` | ONVIF mit kleinerem Bild (flüssiger) |

Axis führt ONVIF-Konten getrennt von den normalen Konten: Ein ONVIF-Konto gilt für `onvif://…` und `/onvif-cgi/…`, nicht für `/axis-cgi/…` (dort kommt „401“).

## Adressen für Browser und QC-Client

| Adresse | Inhalt |
|---|---|
| `https://<HS>/kamera/` | Prüfseite (Bild oben): Schlüssel eingeben, zeigt je Kamera Standbild mit Bildern/s und Live-Bild |
| `https://<HS>/kamera/einfahrt.jpg?k=<Schlüssel>` | Standbild der Kamera „einfahrt“ |
| `https://<HS>/kamera/einfahrt.mjpg?k=<Schlüssel>` | Live-Bild als MJPEG-Strom |
| `https://<HS>/kamera/einfahrt.jpg?k=<Schlüssel>&resolution=640x360` | Standbild in anderer Auflösung |
| `https://<HS>/kamera/einfahrt.mjpg?k=<Schlüssel>&fps=5` | Live-Bild mit 5 Bildern/s |
| `https://<HS>/kamera/list?k=<Schlüssel>` | Namen der Kameras: `{"version":"0.6","cams":["einfahrt","hof"]}` |
| `https://<HS>/kamera/test?k=<Schlüssel>` | Prüfung aller Kameras als JSON |

Zusatz-Parameter: `resolution`, `fps`, `compression`, `camera`. Lehnt die Kamera einen Parameter ab (HTTP 400), geht es mit der Vorgabe aus „Adresse“ weiter.

In eine Webseite eingebunden:

```html
<img src="https://<HS>/kamera/einfahrt.mjpg?k=<Schlüssel>" alt="Einfahrt">
```

## Live-Bild

- Bietet die Kamera einen MJPEG-Strom (Axis), wird er unverändert durchgereicht.
- Sonst baut der Baustein den Strom aus schnell nachgeladenen Standbildern: Vorgabe 8 Bilder/s, mit `&fps=…` 1 bis 15. Wie viele Bilder wirklich ankommen, hängt von Kamera, Auflösung und HomeServer ab; die Prüfseite zeigt den Wert.
- RTSP/H.264 wandelt der Baustein nicht um. Die RTSP-Adresse einer ONVIF-Kamera zeigt die Prüfseite nur an.
- Je Kamera höchstens 4 Zuschauer gleichzeitig.

## Prüfung lesen

`…/test?k=<Schlüssel>` (auch oben auf der Prüfseite) zeigt je Kamera, was der Baustein erreicht hat. Beispiel einer ONVIF-Kamera:

```json
{
 "name": "einfahrt",
 "ok": true,
 "http": 200,
 "bytes": 85183,
 "ms": 272,
 "art": "onvif",
 "profile": ["profile_1 h264 3840x2160 H264", "profile_1 jpeg 3840x2160 JPEG"],
 "profil": "profile_1 h264 3840x2160",
 "standbild": "/onvif-cgi/jpg/image.cgi?resolution=1280x720&compression=30",
 "strom": "rtsp://…/onvif-media/media.amp?profile=profile_1_h264",
 "uhr": "-130 s",
 "live": "Standbilder"
}
```

| Anzeige | Bedeutung |
|---|---|
| `art` | `axis`, `url` (Standbild-Adresse) oder `onvif` |
| `ms` | Zeit für ein Standbild mit gespeicherter Anmeldung |
| `profile` / `profil` | alle Profile der Kamera / das gewählte |
| `standbild` | die wirklich abgerufene Standbild-Adresse (ohne Host) |
| `strom` | RTSP-Adresse der Kamera, nur zur Auskunft (ohne Host und Zugangsdaten) |
| `uhr` | Abweichung der Kamera-Uhr vom HomeServer; der Baustein gleicht sie für die ONVIF-Anmeldung aus |
| `http: 401` | Benutzer oder Passwort falsch (bei Axis: ONVIF-Konto an Axis-Pfaden?) |
| `http: 400` | Kamera lehnt die Anfrage ab, Grund in `detail` |
| `http: 404` | Pfad gibt es nicht – ganze Standbild-Adresse oder `onvif://…` eintragen |
| Fehler ohne `http` | Kamera nicht erreichbar (Adresse, Port, http/https) |

## Im QC-Client

Im Experten bleibt das Kamera-Plugin, wie es ist. Im [QC-Client](https://github.com/BadSmiley0815/QC-Client) links unter **Kamera-Proxy** einmal `https://<HS>/kamera/` und den Schlüssel eintragen. Kameras, deren Name im Plugin zum Namen im Baustein passt („Einfahrt“ → `einfahrt`), laufen dann über den Proxy.

## Stand der Prüfung

- An echten Kameras geprüft (15.11.2026): zwei Axis-Kameras über die Axis-Pfade, eine Axis P1468-LE über `onvif://` (https, selbst ausgestelltes Zertifikat).
- Nur mit nachgebauten Kameras getestet: Standbild-Adresse mit Pfad, Kameras anderer Hersteller, Kameras ohne MJPEG an den Axis-Pfaden.
- Die Bilder auf dieser Seite stammen von Testkameras (gezeichnete Testbilder), nicht von einer echten Anlage.

## Sicherheit

Der Schlüssel steht in jeder Bild-Adresse und ist für jeden Benutzer der Visu sichtbar. An der Kamera deshalb einen eigenen Benutzer nur mit Zuschauer-Recht anlegen.
