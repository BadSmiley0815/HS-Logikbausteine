# 14770 Visu-Server V1.10 – Einbau

Stand 04.11.2026. Baustein: `14770_visuserver.hslz` (HSL3), Kategorie „Visualisierung“, Kontext `hsl3.visuserver` (gemeinsam mit 14771). Bis v1.6 lief er als **19107**.

## Was der Baustein macht
- Datenzentrale für die HTML5-Visu `homeserver-webapp`. Er speichert die Einrichtung (Kacheln, Räume, Favoriten, Titel) für alle Geräte.
- Liefert die Verläufe der Bausteine 14771 für die Diagramme.
- Der HomeServer leitet `https://<HS>/visu-daten/` an den Baustein weiter. Das ist dieselbe Adresse mit demselben Zertifikat wie die Visu.
- Übersichtsseite `https://<HS>/visu-daten/` bietet:
  - Auswahl von Verlauf und Ansicht
  - Wertetabelle mit Zeilennummern und CSV-Export
  - Sicherung herunterladen und einspielen (ergänzen oder überschreiben)

## Verdrahtung
| Eingang | Belegung | Hinweis |
|---|---|---|
| E1 Basis-Pfad | `visu-daten` | → `https://<HS>/visu-daten/` |
| E2 Port | `8092` | **muss eingetragen sein**, bei 0 kommt „503 Service Unavailable“ |
| E3 Schlüssel | eigenes Kennwort | wird in der Visu eingetragen. Leer = ohne Schutz |
| E4 Neustart/Auslöser | beliebiges KO | der Experte verlangt einen KO-belegten Eingang. 1 = Server neu starten |
| E5 Lese-Schlüssel | eigenes Kennwort, anders als E3 | nur Lesen der Verläufe (Diagrammseite). Leer = Lesen nur mit E3 |

| Ausgang | Bedeutung |
|---|---|
| A1 Instanz-ID | an **E5 aller 14771** |
| A2 Status | z. B. „Bereit: /visu-daten/ (Port 8092)“ |
| A3 / A4 / A5 | Abrufe / angemeldete Verläufe / Stand der Einrichtung |

## Diagrammseite zum Einbetten (ab v1.8)
`https://<HS>/visu-daten/chart?id=<Kennung>[,<Kennung>…]&key=<Lese-Schlüssel>` zeigt nur das Diagramm: Werte beim Überfahren mit der Maus, Legende mit aktuellem Wert, Knöpfe für 24 h / 7 Tage / 30 Tage / 1 Jahr / Monate.

| Parameter | Bedeutung |
|---|---|
| `id` | Kennungen der 14771 (E6), mehrere mit Komma |
| `u` / `n` | Ansicht (i, h, d, w, M, y) und Anzahl Werte |
| `title` | Überschrift |
| `refresh` | Aktualisierung in s (Standard 60) |
| `nav=0` | ohne Zeitraum-Knöpfe |
| `ymin` / `ymax` | feste y-Achse |
| `color` | Farben als Hex-Liste, z. B. `2b6cb0,d9480f` |

Einbetten in die Experten-Visu: Textelement, statischer Text
`<iframe src="/visu-daten/chart?id=…&key=…" width="600" height="260" style="border:0"></iframe>`
Den Lese-Schlüssel verwenden, nicht E3: Er steht im Projekt und im Browser lesbar, erlaubt aber nur das Lesen der Verläufe.

## Interaktives Diagramm in der Experten-Visu (ab v1.10) – empfohlen
Die Gira-Visu (`/hsvisu/`) hat eine undokumentierte Erweiterung: Mit `&extras=1` in der Visu-Adresse wird ein Textelement, dessen statischer Text mit `@iframe=` beginnt, als iFrame in Elementgröße angezeigt (`@link=URL,Text` ergibt einen Link).
1. Textelement in Diagrammgröße anlegen, statischer Text:
   `@iframe=/visu-daten/chart?id=test_temp,test_soll,test_stell&u=i&title=Raumtemperatur%20Test`
   (keine Anführungszeichen, Leerzeichen als `%20`).
2. Visu aufrufen mit `…/hsvisu/pages/V1?token=…&extras=1` (Lesezeichen/Kiosk-Adresse entsprechend anpassen). Ohne `extras=1` erscheint nur der Text.
3. Im Diagramm: Mausover zeigt alle Werte zum Zeitpunkt, Klick auf einen Legendeneintrag blendet ihn sofort ein/aus (Auswahl bleibt im Browser gespeichert), zweite Einheit (z. B. %) auf eigener rechter Achse, Knöpfe 1 h / 12 h / 24 h / 48 h / 7 Tage / 30 Tage / 1 Jahr / 2 Jahre / 3 Jahre – bei den Jahresansichten zeigt das Diagramm 3 Monate, ein Schieberegler darunter verschiebt den Ausschnitt, Kennzahlen Min/Max/Ø. Aktualisiert sich alle 60 s (`&refresh=`).
Weitere Parameter: `nav=0` (ohne Zeitraum-Knöpfe), `hide=<Kennung>` (anfangs ausgeblendet), `ymin`/`ymax`, `color`, `key` (Lese-Schlüssel E5).

## Diagramm als Bild für die Experten-Visu (ab v1.9)
Die Experten-Visu (`/hsvisu/`) zeigt HTML im statischen Text nur als Text an – der iFrame geht dort nicht. Der CSS-Stil eines Elements kommt aber unverändert an.
`https://<HS>/visu-daten/chart.svg?id=<Kennung>[,…]&u=i&w=940&h=420` liefert das Diagramm als SVG-Bild (Parameter wie `chart`, dazu `w`/`h` = Elementgröße in Pixel, `bg` Hintergrund-Hex oder `none`).

Einbau: Textelement in Größe des Diagramms anlegen, statischen Text leer lassen, Reiter CSS → CSS-Stil:
`background:url(/visu-daten/chart.svg?id=test_temp&u=i&w=940&h=420) no-repeat center/100% 100%;`
Keine Anführungszeichen verwenden (der Experte wandelt sie in „?“ um). Leerzeichen im Titel als `%20`.

Im Bild: Min/Max/Mittel unter dem Titel, Höchst- und Tiefstwert beschriftet, bei bis zu 31 Werten jeder Wert. Mit `&view=table` kommt eine Wertetabelle (Zeit | Wert, neueste zuerst). Da ein Hintergrundbild kein Mausover kann, ersetzt das die Detailwerte. Zeiträume und Tabelle als Popup-Seiten mit Knöpfen („Seite aufrufen“). Bei gesetztem Schlüssel `&key=<Lese-Schlüssel E5>` anhängen. Das Bild wird beim Öffnen der Seite geladen.

### Mehrere Werte in einem Diagramm (ab v1.10)
- `id=raum_ist,raum_soll,raum_stell` zeichnet alle drei in ein Bild.
- Die erste Einheit (°C) steht links, eine zweite Einheit (%) auf einer eigenen rechten Achse, Linie gestrichelt. `%` ist fest 0–100, sonst gelten `ymin2`/`ymax2`.
- Ein konstanter Wert (Sollwert) steht als „konstant 21,0 °C“ in der Kennzahlenzeile.
- **Ein-/Ausblenden:** am jeweiligen 14771 E11 ein 1-Bit-iKO anschließen (1 = anzeigen, 0 = aus). In der Visu je Wert einen Knopf, der das iKO umschaltet. Ausgeblendete Werte stehen grau mit „(aus)“ in der Legende und fehlen in der Tabelle; aufgezeichnet wird weiter. Fest ausblenden geht auch mit `&hide=<Kennung>` in der URL.

### Live-Diagramm über das Kamera-Element (ab v1.10)
- `chart.png` liefert dasselbe Diagramm als PNG, gleiche Parameter wie `chart.svg`.
- Stammdaten → Kameras: neue Kamera, URL `http://127.0.0.1:8092/chart.png?id=test_temp,test_soll,test_stell&u=i&w=940&h=420` (Port = E2).
- In der Visu ein Kamera-Element in derselben Größe; es lädt das Bild zyklisch neu. Ein-/Ausblenden über 14771 E11 wirkt so ohne Neuladen der Seite.
- Das Bild wird je URL 4 s zwischengespeichert. Ein PNG zu rechnen kostet auf dem HS deutlich mehr als ein SVG – nicht kürzer als alle 5 s abrufen.

## WebApp
Ordner `WebApp/homeserver-webapp` in den hsupload-Ordner des Projekts kopieren. Der Weg ist Projekteinstellungen → Oberfläche → „Projekt“. Danach mit „Alle“ übertragen und `https://<HS>/opt/homeserver-webapp/index.html` aufrufen. In der Visu unter Einstellungen → Visu-Server das Häkchen setzen und den Schlüssel eintragen. Die vollständige Anleitung liegt unter `Dokumentation/Anleitung_Visu_gesamt.html`.

## Umstieg von 19107
1. Übersichtsseite → „Sicherung herunterladen“.
2. 14770 einfügen und wie 19107 belegen. Die 19105 durch 14771 ersetzen (siehe dort).
3. 19107 löschen. Nicht parallel betreiben, beide nutzen denselben Port und Pfad.
4. Übertragen, dann die Sicherung mit „alles überschreiben“ einspielen.

## Quellen
`Quellen/` enthält `config.json`, `src/hsl3_14770_visuserver.py`, die gebaute `.hsl`, die Hilfeseiten DE/EN und `build.py`. `build.py` braucht den Gira-Generator `generator3.cpython-39.pyc` und Python 3.9, Pfade über die Umgebungsvariablen `HSL3_GEN` und `PY39`.
