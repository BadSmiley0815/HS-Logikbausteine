# 14784 Meldungsspeicher – Version 1.1

**ID 14784 · Version 1.1 · HSL3**

Eigenes Meldungsarchiv (z. B. Wetterstation, Alarmanlage) – 16 Melder mit Texten, Freitext, Quittieren; Abruf über den Visu-Server 14770.

**Neu in 1.1:** Freigabe (E42–E45) – Melder nur aufzeichnen, solange z. B. die Alarmanlage scharf ist (Alarmverfolgung); Quellen (E46–E72) – bis zu 12 Quellen mit Namen, die an die Meldung gehängt werden („Alarmanlage scharf – Schlüsselschalter Eingang“).

## Baustein

![Baustein](bilder/baustein.png)

## Eingänge

- E1 Visu-Server Instanz-ID (A1 von 14770) [Zahl]
- E2 Kennung (z. B. wetter) [Text]
- E3 Name [Text]
- E4 Stufe Freitext 0=Info 1=Warnung 2=Alarm [Zahl]
- E5 Jedes Telegramm melden (1) / nur Wechsel (0) [1 Bit]
- E6 Freitext [14 Byte Text]
- E7 Melder 1 [1 Bit]
- E8 Melder 2 [1 Bit]
- E9 Melder 3 [1 Bit]
- E10 Melder 4 [1 Bit]
- E11 Melder 5 [1 Bit]
- E12 Melder 6 [1 Bit]
- E13 Melder 7 [1 Bit]
- E14 Melder 8 [1 Bit]
- E15 Melder 9 [1 Bit]
- E16 Melder 10 [1 Bit]
- E17 Melder 11 [1 Bit]
- E18 Melder 12 [1 Bit]
- E19 Melder 13 [1 Bit]
- E20 Melder 14 [1 Bit]
- E21 Melder 15 [1 Bit]
- E22 Melder 16 [1 Bit]
- E23 Text Melder 1: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E24 Text Melder 2: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E25 Text Melder 3: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E26 Text Melder 4: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E27 Text Melder 5: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E28 Text Melder 6: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E29 Text Melder 7: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E30 Text Melder 8: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E31 Text Melder 9: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E32 Text Melder 10: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E33 Text Melder 11: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E34 Text Melder 12: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E35 Text Melder 13: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E36 Text Melder 14: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E37 Text Melder 15: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E38 Text Melder 16: EIN;AUS;Stufe EIN;Stufe AUS [Text]
- E39 Max. Einträge (50-10000) [Zahl]
- E40 Alle quittieren (1) [1 Bit]
- E41 Alle löschen (1) [1 Bit]
- E42 Melder nur bei Freigabe aufzeichnen (1=ja) [1 Bit]
- E43 Freigabe 1 (z. B. extern scharf) [1 Bit]
- E44 Freigabe 2 (z. B. intern scharf) [1 Bit]
- E45 Nachlauf nach Ende der Freigabe (s) [Zahl]
- E46 Quelle: Zeitfenster (s) [Zahl]
- E47 Quelle nur an Melder (z. B. 1,2; leer=alle) [Text]
- E48 Text ohne erkannte Quelle (z. B. Visu/QC) [Text]
- E49 Quelle 1 (jedes Telegramm <>0) [1 Bit/Text]
- E50 Quelle 2 (jedes Telegramm <>0) [1 Bit/Text]
- E51 Quelle 3 (jedes Telegramm <>0) [1 Bit/Text]
- E52 Quelle 4 (jedes Telegramm <>0) [1 Bit/Text]
- E53 Quelle 5 (jedes Telegramm <>0) [1 Bit/Text]
- E54 Quelle 6 (jedes Telegramm <>0) [1 Bit/Text]
- E55 Quelle 7 (jedes Telegramm <>0) [1 Bit/Text]
- E56 Quelle 8 (jedes Telegramm <>0) [1 Bit/Text]
- E57 Quelle 9 (jedes Telegramm <>0) [1 Bit/Text]
- E58 Quelle 10 (jedes Telegramm <>0) [1 Bit/Text]
- E59 Quelle 11 (jedes Telegramm <>0) [1 Bit/Text]
- E60 Quelle 12 (jedes Telegramm <>0) [1 Bit/Text]
- E61 Quelle 1 Name [Text]
- E62 Quelle 2 Name [Text]
- E63 Quelle 3 Name [Text]
- E64 Quelle 4 Name [Text]
- E65 Quelle 5 Name [Text]
- E66 Quelle 6 Name [Text]
- E67 Quelle 7 Name [Text]
- E68 Quelle 8 Name [Text]
- E69 Quelle 9 Name [Text]
- E70 Quelle 10 Name [Text]
- E71 Quelle 11 Name [Text]
- E72 Quelle 12 Name [Text]

## Ausgänge

- A1 Letzte Meldung [Text]
- A2 Anzahl Einträge [Zahl]
- A3 Offene Meldungen (unquittiert) [Zahl]
- A4 Offener Alarm [1 Bit]
- A5 Status [Text]

## Versionen

- **1.1** (2026-11-12) – Freigabe für Alarmverfolgung, Quellen an der Meldung.
- **1.0** (2026-11-11) – erste Version.

## Dateien

- `14784_meldungsspeicher.hslz` – Import im Experten: Logikbausteine → Importieren
- `Quellen/DE-log14784.html` – ausführliche Hilfe (im Experten über die Bausteinhilfe)
- `Quellen/src/…py`, `Quellen/config.json` – Quellcode; die `.hsl` erzeugt der Gira-Generator (HSL3 SDK, nicht enthalten)

iKOs bei Bedarf per CSV-Import anlegen: Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren.

[← zur Übersicht](../README.md)
