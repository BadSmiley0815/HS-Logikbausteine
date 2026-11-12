# Changelog – HS-Logikbausteine

Alle Versionen aller Bausteine, je Baustein neueste oben. Datum = Veröffentlichung auf GitHub (Repo seit 10.11.2026); ältere Versionen ohne Datum stammen aus der Hilfe der Bausteine.
Wird bei jeder Änderung an einem Baustein fortgeschrieben.

| ID | Baustein | aktuell |
|---|---|---|
| [14770](#14770-visu-server) | Visu-Server | 1.13 |
| [14771](#14771-verlaufsspeicher-für-diagramme) | Verlaufsspeicher für Diagramme | 2.7 |
| [14775](#14775-rlt-luftqualitätsregelung) | RLT Luftqualitätsregelung | 1.6 |
| [14776](#14776-wrg-pumpenregelung) | WRG-Pumpenregelung | 1.0 |
| [14777](#14777-kompressor-klappensteuerung) | Kompressor-Klappensteuerung | 1.2 |
| [14778](#14778-szenen-server) | Szenen-Server | 4.3 |
| [14783](#14783-kamera-proxy) | Kamera-Proxy | 0.4 |
| [14784](#14784-meldungsspeicher) | Meldungsspeicher | 1.1 |
| [14785](#14785-bewässerung-5-kreise-kaskadierbar) | Bewässerung 5 Kreise (kaskadierbar) | 1.1 |

---

## 14770 Visu-Server
- **1.13** (2026-11-12) – Meldungsseite: Meldungsspeicher mit gleichem Namen erscheinen als ein Reiter, Einträge zeitlich gemischt (z. B. zwei Instanzen „Alarmverfolgung“); „Alle quittieren“ gilt für alle Archive des Reiters.
- **1.12** (2026-11-11) – neue Seiten `meldungen` (Meldungsliste der 14784 mit Filter, Suche, Quittieren) und `verlaeufe` (alle Verläufe nach Raum gruppiert in einem Diagramm). Schlüssel per `?key=` oder aus dem Browser, sonst Abfrage; `chart` nimmt den Schlüssel ebenfalls aus dem Browser. Skala links automatisch oder fest (von/bis, je Raum gemerkt), `ymin2/ymax2` für die rechte Achse, `span` = Mindest-Spanne (Temperatur standardmäßig 4 K).
- **1.11** (2026-11-11) – Meldungen: nimmt Meldungsspeicher 14784 an und liefert sie unter `api/messages` (Liste bzw. `?id=&n=&since=`), Quittieren über `POST api/messages/ack`; Sicherung/Einspielen enthält die Meldungen. Diagramme unverändert.
- **1.10** (veröffentlicht 2026-11-10) – Diagrammseite: Legende klickbar (ein/aus), zweite Achse, Kennzahlen, Zeiträume 1 h bis 3 Jahre mit Schieberegler, Zoom per Aufziehen, Zeitachse immer über den ganzen Zeitraum. Einbau in die Gira-Visu über `@iframe=` und `extras=1`. `chart.svg` mit zweiter Achse und `hide=`; neu `chart.png`.
- **1.9** – Diagramm als SVG-Bild (für die Experten-Visu).
- **1.8** – Diagrammseite `chart` zum Einbetten, E5 Lese-Schlüssel.
- **1.7** – offizielle ID 14770 (bisher 19107), Funktion unverändert.
- **1.6** – Aufruf aus dem Diagramm mit „Zurück“.
- **1.5** – Zeilennummern, Sicherung einspielen: ergänzen oder überschreiben.
- **1.4** – Texteingänge als UTF-8.
- **1.3** – Übersichtsseite mit Tabelle, CSV-Export, Sicherung.
- **1.2** – Port-Rückfall auf 8092.
- **1.1** – Eingang E4.
- **1.0** – erste Version (als 19107).

## 14771 Verlaufsspeicher für Diagramme
- **2.7** (veröffentlicht 2026-11-10) – E11 „Im Diagramm anzeigen“ (Ein-/Ausblenden in `chart.svg` von 14770).
- **2.6** – offizielle ID 14771 (bisher 19105), Funktion unverändert.
- **2.5** – Verlauf bleibt nach Neustart erhalten, auch wenn E3 beim Start noch nicht belegt ist (bisher wurde dann gelöscht); Sicherung alle 10 Minuten statt stündlich.
- **2.4** – E10 löscht per Zeilennummer (-1 = alle); Sicherung wahlweise ergänzen statt überschreiben.
- **2.3** – Texte an E6–E8 als UTF-8 (°C wurde zu Â°C).
- **2.2** – E10 Zeilen löschen.
- **2.1** – Status ohne Umlaute (Anzeige im Experten-Monitor).
- **2.0** – Anbindung an den Visu-Server, Kalenderansichten (als 19105).

## 14775 RLT Luftqualitätsregelung
- **1.6** (2026-11-10) – Einheit bzw. Datentyp in jeder Ein- und Ausgangsbezeichnung (z. B. `[ppm]`, `[degC]`, `[%]`); Regelung unverändert.
- **1.5** – erste veröffentlichte Version: Ventilatoren und Klappen nach Luftqualität, Übertemperatur, Freecooling, Ampel.

## 14776 WRG-Pumpenregelung
- **1.0** (veröffentlicht 2026-11-10) – erste Version: WRG-Pumpe an einem Druckluft-Kompressor (Formelbaustein HSL 1.0).

## 14777 Kompressor-Klappensteuerung
- **1.2** (veröffentlicht 2026-11-10) – Kühlregler (E28–E30, A14) entfernt; A11/A12 im Sommer 0; Pin-Namen Regler Kompressorraum (T1) / Halle 1.OG (T4).
- **1.1** – Kühlregler T1 (M3/M5 gegenläufig).
- **1.0** – erste Version (Formelbaustein HSL 1.0).

## 14778 Szenen-Server
- **4.3** (2026-11-12) – Buslast einstellbar: höchstens n Telegramme am Stück (Standard 5), dann Pause (Standard 1 s), 0 = ohne Begrenzung. Einstellung auf der Seite unter „Gruppe bearbeiten → Senden – Buslast“. Wartende Werte desselben KO werden durch den neuesten ersetzt.
- **4.2.2** (2026-11-11) – Status-Ausgänge (aktive Szene, Szene 1–8 aktiv, Gateway, Einrichtung) senden nur noch bei Änderung bzw. bei jedem Szenenaufruf. Vorher gingen bei jeder Bedienung auf der Seite alle Status-Telegramme erneut auf den Bus und lösten daran hängende Logiken aus. Beim Start und über E14 werden alle einmal gesendet.
- **4.2.1** (2026-11-11) – Fehler behoben: E1/E2 sind wieder als Eingangstyp „Basis-Pfad“/„Ziel-Port“ deklariert. In 4.1/4.2 fehlte dadurch die Kennung in der `.hsl` (5000-Zeile endete auf `|0|0`), der HomeServer legte keine Weiterleitung an und `https://<HS>/szenen/` lieferte 404, obwohl der Baustein „Bereit“ meldete.
- **4.2** – Bedingung Außentemperatur je Funktion (Grenzwert in °C; Öffnen/Einschalten aus einer Szene nur oberhalb, bei unbekannter Temperatur nicht). Position invertiert für Aktoren mit 0 % = offen (z. B. Dachluken über Rollladenkanal); die Seite zeigt weiter 0 % = zu.
- **4.1** – Einzelheiten nicht dokumentiert.
- **4.0** – offizielle ID 14778 (bisher 19108).

## 14783 Kamera-Proxy
- **0.4** (2026-11-10) – Weiterleitungen der Kamera werden befolgt (http → https).
- **0.3** (2026-11-10) – Verbindungen bleiben offen, Anmeldung wird gemerkt, `/list` für den QC-Client.
- **0.2** (2026-11-10) – Datentyp an jedem Ein-/Ausgang; ganze Kamera-URL als Adresse, `resolution`/`compression`/`camera` als Vorgabe; HTTP 400 wird ohne Zusatz-Parameter wiederholt; Fehlertext der Kamera wird angezeigt.
- **0.1** (2026-11-10) – Prüffassung: bis zu 3 Axis-Kameras per Digest, Weiterleitung `https://<HS>/kamera/` auf Port 8095.

## 14784 Meldungsspeicher
- **1.1** (2026-11-12) – Freigabe (E42–E45): Melder nur aufzeichnen, solange z. B. die Alarmanlage scharf ist, plus Nachlauf – für eine Alarmverfolgung mit Bewegungsmeldern und Türkontakten. Quellen (E46–E72): bis zu 12 Quellen mit Namen; ändert sich ein Melder kurz danach, wird die Quelle an die Meldung gehängt („Alarmanlage extern scharf – Schlüsselschalter Eingang“), sonst ein einstellbarer Text (z. B. „Visu/QC/Zeitschaltuhr“).
- **1.0** (2026-11-11) – erste Version: eigenes Meldungsarchiv je Instanz, 16 Melder mit Text `EIN;AUS;Stufe EIN;Stufe AUS`, Freitext-Eingang, Quittieren, Löschen, remanent; Abruf über Visu-Server 14770 ab v1.11.

## 14785 Bewässerung 5 Kreise (kaskadierbar)
- **1.1** (2026-11-12) – Ventil-Rückmeldung je Kreis (E37, E43, E49, E55, E61): Laufzeit zählt ab Rückmeldung, egal von wo der Kanal eingeschaltet wird; extern eingeschaltet ohne Programm → nur dieser Kreis läuft seine Zeit (mit Netzteil/Pumpe); extern ausgeschaltet → Kreis beendet, ein laufendes Programm geht zum nächsten Kreis; fehlt die Rückmeldung 10 s → Zeit läuft trotzdem + Störung. Kreis-Eingänge neu nummeriert (E32–E61).
- **1.0** (2026-11-12) – erste Version: 5 Kreise je Baustein, Kaskade Master/Folge über Text-iKOs, Endzeit statt Startzeit (Lauf 1, Lauf 2 = +12 h für Kreise mit Zyklus 2), Laufzeit 0 = überspringen, Wetterfaktor, Parallel je Kreis + max. gleichzeitig, Pause/Überlappung, Regensperre je Kreis mit Einschaltverzögerung/Nachwirkzeit, Frostsperre, Watchdog, Netzteil 24 V (3 Modi), Pumpe mit Verzögerung/Druckentlastung, Nachspeisung mit Schwimmer min/max, Trockenlaufschutz.
