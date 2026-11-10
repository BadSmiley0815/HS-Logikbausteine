# Gira HomeServer – KO-Gateway (WebSocket): Referenz für Claude

Diese Zusammenfassung stammt aus einem funktionierenden Projekt: eigene HTML5-Visu „homeserver-webapp“ auf einem Gira HomeServer (HS 4.x, Experte). Alle Angaben sind dort im Betrieb getestet. Nutze sie als Grundlage, wenn eine Webseite oder ein Skript KOs des HomeServers lesen oder schalten soll.

## 1. Voraussetzungen im Experten
- Projekteinstellungen → **KO-Gateway**: aktivieren, einen Benutzer mit Passwort anlegen.
- Die gewünschten KOs in eine **WebSocket-Gruppe** mit Lesen und/oder Schreiben aufnehmen, dazu die Benutzergruppe mit Endpunkt-Rechten.
- Für einen KO-Import: „**XML-Struktur der K.-Objekte auf Gerät laden**“ anhaken. Danach liegt die Liste unter `https://<HS>/hscl?sys/cobjects.xml`.
- Projekt übertragen.

## 2. Verbindung
```
wss://<HS-IP>/endpoints/ws?authorization=<base64("benutzer:passwort")>
```
- Anmeldung als Query-Parameter, **nicht** als Header. Base64 aus UTF-8: `btoa(unescape(encodeURIComponent(user + ":" + pass)))`, danach `encodeURIComponent`.
- Der HS spricht praktisch nur **wss://** (443). Das Zertifikat ist selbstsigniert, deshalb im Browser einmal `https://<HS-IP>` öffnen und akzeptieren. Sonst kommt Close-Code **1006** ohne Handshake.
- Close-Code 1006 nach geöffneter Verbindung oder 1008 heißt meist: Benutzer/Passwort oder Endpunkt-Rechte falsch.
- Beim Reconnect einen Backoff von 1 s → 30 s nutzen. Danach neu abonnieren, offene Anfragen verwerfen.
- Liegt die Seite selbst auf dem HS (hsupload → `https://<HS>/opt/<ordner>/index.html`), sind Origin und Zertifikat identisch. Das ist die unproblematischste Variante.

## 3. Schlüssel (Keys)
| Präfix | Bedeutung | Beispiel |
|---|---|---|
| `CO@` | Kommunikationsobjekt: Gruppenadresse mit `_` statt `/` **oder** Endpunkt-ID / KO-ID | `CO@1_2_3`, `CO@VISU_CONFIG`, `CO@12345` |
| `DA@` | Datenarchiv | `DA@Temperaturen` |
| `SC@` | Szene | `SC@WOHNEN` |
| `SQ@` | Sequenz | `SQ@...` |

Welche Form (GA oder ID) ein HS akzeptiert, hängt von der Gateway-Einstellung ab. Im Zweifel beide mit `subscribe` testen und die Antwort-Codes prüfen.

## 4. Nachrichten (JSON)
**Abonnieren** (liefert Anfangswerte, danach Push bei Änderung). In Paketen zu höchstens 100 Keys senden:
```json
{"type":"subscribe","param":{"keys":["CO@1_2_3","CO@1_2_4"]}}
```
Antwort: `{"data":{"items":[{"key":"CO@1_2_3","code":0,"data":{"value":"1"}}, ...]}}`. Ein `code` ungleich 0 heißt: KO nicht vorhanden oder nicht freigegeben.

**Push bei Wertänderung:**
```json
{"subscription":{"key":"CO@1_2_3"},"data":{"value":"1"}}
```

**Aufruf (call)**. Das `tag` ist frei wählbar und kommt in der Antwort zurück; darüber wird die Antwort zugeordnet:
```json
{"type":"call","param":{"key":"CO@1_2_3","method":"set","value":"1"},"tag":"t42"}
```
| method | Zweck | Hinweis |
|---|---|---|
| `set` | Wert schreiben | Wert als **String** senden (`"1"`, `"21.5"`) |
| `toggle` | 1-Bit umschalten | `value:"1"` |
| `get` | Wert lesen | bei `DA@` mit Parametern, siehe unten |
| `meta` | Metadaten | bei `DA@`: Spalten, `stat.last` usw. |
| `call` / `learn` | Szene `SC@` abrufen / lernen | |
| `start` / `stop` | Sequenz `SQ@` | |

**Fehler:** Die Antwort enthält `code` ≠ 0, dazu optional `message` und `request` (mit `key`). Kommt die Antwort ohne `tag`, über `request.key` + `request.method` zuordnen.

## 5. Datentypen
- Zahlen und Bits kommen als String oder Zahl, `Number()` verwenden, Komma tolerieren.
- **Text-KOs (14 Byte) sind Base64-kodiert.** Beim Lesen `atob` → UTF-8 dekodieren (`TextDecoder`). Beim Schreiben Base64 senden.
- Ein 14-Byte-KO fasst im HS bis ca. 30.000 Zeichen, **remanent nur 10.000**. Größere Daten auf mehrere KOs aufteilen oder per HSL3-Baustein speichern.

## 6. Datenarchiv (DA@)
```json
{"type":"call","param":{"key":"DA@Name","method":"get","startat":"2609301200","cnt":168,"size":60},"tag":"q1"}
```
- `startat` = **YYMMDDhhmm** (Ortszeit), `cnt` = Anzahl Werte, `size` = Raster in Minuten. Optional `cols:[…]`.
- Vorher `meta` abfragen: `stat.last` liefert den letzten Zeitstempel (Sekunden oder Millisekunden, beides abfangen).

## 7. KO-Struktur (cobjects.xml)
`https://<HS>/hscl?sys/cobjects.xml` enthält je KO einen Knoten mit diesen Attributen:
- `id`, `ga`, `name`, `path` (Ordner mit `\` getrennt)
- `type`, `fmt`, `fmtex`, `min`, `max`
- `used` (`"0"` = unbenutzt)

Die Namen folgen oft dem Schema „Raum - Funktion“ und lassen sich daran in Raum und Funktion aufteilen. Kann der Browser die Datei nicht direkt laden (andere Origin), die XML speichern und als Datei einlesen.

## 8. Eigene Daten neben dem Gateway (HSL3-Baustein)
Für Daten, die nicht in KOs passen (Einrichtung, Verläufe), hat sich ein HSL3-Baustein mit eigenem HTTP-Server bewährt:
- **Eingänge:** `base_path` (z. B. `visu-daten`) und `destination_port` (z. B. 8092).
- **Weiterleitung:** Der HS leitet `https://<HS>/<base_path>/…` an den Baustein weiter. Dadurch gelten dieselbe Origin und dasselbe Zertifikat wie für die Webseite.
- **Port muss im Experten eingetragen sein.** Steht er auf 0, antwortet der HS mit „503 Service Unavailable“.
- **Anmeldung:** Das HS-Login wird nicht weitergereicht, deshalb ein eigener Schlüssel per Header (`X-Visu-Key`).
- **Referenz:** Bausteine 19107 Visu-Server und 19105 Verlaufsspeicher.

## 9. Praxis-Tipps
- Nach dem Senden auf den Push-Rückwert warten, nicht optimistisch umschalten, dabei einen Busy-Zustand anzeigen.
- Status-KO und Schalt-KO getrennt behandeln (z. B. Dimmer: Schalten, Wert, Rückmeldung).
- Ein Debug-Log mit allen ⇒/⇐-Nachrichten und dem Close-Code spart die meiste Fehlersuche.
- Texte aus HSL3-Eingängen kommen als UTF-8-Bytes. Als latin-1 gelesen wird aus „°C“ „Â°C“.
