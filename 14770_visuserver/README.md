# 14770 Visu-Server – Version 1.10

**ID 14770 · Version 1.10 · HSL3 · Kategorie Visualisierung**

homeserver-webapp, Diagramme.

Der HomeServer leitet `https://<HS>/visu-daten/` an den Baustein (Port 8092) weiter.

## Eingänge

- E1 Basis-Pfad
- E2 Port
- E3 Schlüssel
- E4 Neustart / Auslöser (beliebiges KO)
- E5 Lese-Schlüssel (Diagrammseite)

## Ausgänge

- A1 Instanz-ID (an E5 von 14771)
- A2 Status
- A3 Abrufe
- A4 Verläufe
- A5 Stand Einrichtung

## Dateien

- `14770_visuserver.hslz` – zum Import im Experten (Logikbausteine → Importieren)
- `Quellen/DE-log14770.html` – ausführliche Hilfe (im Experten über die Bausteinhilfe)
- `Quellen/src/…py`, `Quellen/config.json` – Quellcode; die `.hsl` erzeugt der Gira-Generator (HSL3 SDK, nicht enthalten)
- `Anleitung_Einbau.md` – Einbau Schritt für Schritt

iKOs bei Bedarf per CSV-Import anlegen: Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren.
