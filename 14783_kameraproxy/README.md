# 14783 Kamera-Proxy – Version 0.1

**ID 14783 · Version 0.1 · HSL3**

Axis-Kameras per Digest für den QC-Client.

Der HomeServer leitet `https://<HS>/kamera/` an den Baustein (Port 8095) weiter – gleiche Adresse und gleiches Zertifikat wie der HS.

## Baustein

![Baustein](bilder/baustein.png)

## Beispiel

**Ergebnis: Prüfseite mit zwei Testkameras – Standbild schnell nachgeladen und MJPEG-Strom**

![Ergebnis: Prüfseite mit zwei Testkameras – Standbild schnell nachgeladen und MJPEG-Strom](bilder/beispiel_pruefseite.png)

## Eingänge

- E1 Basis-Pfad
- E2 Port
- E3 Schlüssel
- E4 Neustart / Auslöser (beliebiges KO)
- E5 Kamera 1 Name
- E6 Kamera 1 Adresse (IP oder URL)
- E7 Kamera 1 Benutzer
- E8 Kamera 1 Passwort
- E9 Kamera 2 Name
- E10 Kamera 2 Adresse (IP oder URL)
- E11 Kamera 2 Benutzer
- E12 Kamera 2 Passwort
- E13 Kamera 3 Name
- E14 Kamera 3 Adresse (IP oder URL)
- E15 Kamera 3 Benutzer
- E16 Kamera 3 Passwort

## Ausgänge

- A1 Status
- A2 Abrufe
- A3 Aktive Ströme
- A4 Letzte Prüfung

## Dateien

- `14783_kameraproxy.hslz` – Import im Experten: Logikbausteine → Importieren
- `Quellen/DE-log14783.html` – ausführliche Hilfe (im Experten über die Bausteinhilfe)
- `Quellen/src/…py`, `Quellen/config.json` – Quellcode; die `.hsl` erzeugt der Gira-Generator (HSL3 SDK, nicht enthalten)
- [`Anleitung_Einbau.md`](Anleitung_Einbau.md) – Einbau Schritt für Schritt

iKOs bei Bedarf per CSV-Import anlegen: Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren.

[← zur Übersicht](../README.md)
