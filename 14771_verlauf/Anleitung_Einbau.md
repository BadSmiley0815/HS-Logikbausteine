# 14771 Verlaufsspeicher für Diagramme V2.7 – Einbau

Stand 04.11.2026. Baustein: `14771_verlauf.hslz` (HSL3), Kategorie „Visualisierung“, Kontext `hsl3.visuserver` (gemeinsam mit 14770). Bis v2.5 lief er als **19105**.

## Was der Baustein macht
- Zeichnet je Baustein einen Messwert auf, z. B. Temperatur, Leistung oder Zählerstand.
- Speichert die Werte in diesen Ansichten:

| Ansicht | Zeitraum |
|---|---|
| Minute | 24 h |
| Stunde | 1 Jahr |
| Tag und Woche | je 10 Jahre |
| Monat | 20 Jahre |
| Jahr | 50 Jahre |

- Die Werte liegen komprimiert in 20 remanenten Speichervariablen und werden alle 10 Minuten gesichert.
- Meldet sich beim Visu-Server 14770 an. In der Visu ist er dann als Quelle `VS@<Kennung>` verfügbar.

## Verdrahtung
| Eingang | Belegung | Hinweis |
|---|---|---|
| E1 Wert | KO des Messwerts | |
| E2 Nachkommastellen | 0–4 | gilt in der Visu bei „automatisch“ |
| E3 Modus | 0 Mittel · 1 Letzter · 2 Differenz (Zähler → Verbrauch) · 3 Max | ein Wechsel behält die Werte |
| E4 Reset | 1 = ganzen Verlauf löschen | |
| E5 Visu-Server | **A1 von 14770** | |
| E6 Kennung | eindeutig, ohne Leerzeichen, z. B. `pool_temp` | muss beim Umstieg gleich bleiben |
| E7 Name / E8 Einheit | Anzeige | Umlaute und °C möglich |
| E9 A1 an | 1 = Text für 14-Byte-KO an A1 | nur ohne Visu-Server nötig |
| E10 Zeile löschen | Nummer von der Übersichtsseite (1xxxx Minute … 6xxxx Jahr), **-1 = alle** | KO mit 4 Byte und Vorzeichen oder Gleitkomma |
| E11 Im Diagramm anzeigen | 1 = ja (Standard), 0 = ausblenden | für chart.svg von 14770 ab v1.10; 1-Bit-iKO für einen Visu-Knopf; Aufzeichnung läuft weiter |

| Ausgang | Bedeutung |
|---|---|
| A1 | Verlauf als Text (optional) |
| A2 | Anzahl Werte |
| A3 | Status, z. B. „Angemeldet am Visu-Server (Instanz 7)“ |

## Neu in V2.7
E11 „Im Diagramm anzeigen“. Bestehende Instanzen: Baustein im Experten aktualisieren, E11 bleibt unbelegt = 1 (wird angezeigt). Die gespeicherten Werte bleiben erhalten.

## Umstieg von 19105
Den neuen 14771 mit **denselben Eingängen** wie den alten 19105 belegen, vor allem mit derselben Kennung an E6, und E5 an A1 von 14770 anschließen. Dann 19105 löschen, übertragen und die Sicherung des Visu-Servers mit „alles überschreiben“ einspielen. Die Werte kommen damit zurück.

## Quellen
`Quellen/` enthält `config.json`, `src/hsl3_14771_verlauf.py`, die gebaute `.hsl`, die Hilfeseiten DE/EN und `build.py`. `build.py` braucht den Gira-Generator und Python 3.9, Pfade über `HSL3_GEN` und `PY39`.
