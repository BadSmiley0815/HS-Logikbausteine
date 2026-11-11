# HS-Logikbausteine

Freie Logikbausteine (HSL3 und HSL 1.0) für den Gira HomeServer / FacilityServer – mit Quellcode, Hilfe, Bild und Beispiel.
Jeder Ordner enthält die importierbare `.hslz` bzw. `.hsl` und eine README.

Passend dazu: [QC-Client](https://github.com/BadSmiley0815/QC-Client) – der QuadClient im Browser.

Alle Versionen aller Bausteine: [CHANGELOG.md](CHANGELOG.md)

Stand 11.11.2026 · ID-Bereich 14770–14789 · nächste freie ID **14785**

## Bausteine

| ID | Baustein | Version | Port / Pfad |
|---|---|---|---|
| 14770 | [Visu-Server](14770_visuserver/) | 1.11 | 8092 `/visu-daten/` |
| 14771 | [Verlaufsspeicher für Diagramme](14771_verlauf/) | 2.7 |  |
| 14772 | KNX-Tunnel Senden – noch nicht veröffentlicht | ? |  |
| 14773 | KNX-Tunnel Empfangen – noch nicht veröffentlicht | ? |  |
| 14774 | KNX-Tunnel Gateway-Server – noch nicht veröffentlicht | ? |  |
| 14775 | [RLT Luftqualitätsregelung](14775_RLT_Luftqualitaet/) | 1.6 |  |
| 14776 | [WRG-Pumpenregelung](14776_WRG_Pumpenregelung/) | 1.0 |  |
| 14777 | [Kompressor-Klappensteuerung](14777_Kompressor_Klappensteuerung/) | 1.2 |  |
| 14778 | [Szenen-Server](14778_szenenserver/) | 4.2.2 | 8093 `/szenen/` |
| 14779 | Zeitschaltuhr + Aufzeichnung – geplant | – | 8094 (reserviert) |
| 14780 | (verworfene Parallelfassung KNX-Tunnel) – nicht verwenden | – |  |
| 14781 | (verworfene Parallelfassung KNX-Tunnel) – nicht verwenden | – |  |
| 14782 | (verworfene Parallelfassung KNX-Tunnel) – nicht verwenden | – |  |
| 14783 | [Kamera-Proxy](14783_kameraproxy/) | 0.4 (Prüffassung) | 8095 `/kamera/` |
| 14784 | [Meldungsspeicher](14784_meldungsspeicher/) | 1.0 |  |

## Auf einen Blick

### [14770 Visu-Server](14770_visuserver/)

homeserver-webapp, Diagramme.

<img src="14770_visuserver/bilder/beispiel_diagramm.jpg" width="640" alt="Visu-Server">

### [14771 Verlaufsspeicher für Diagramme](14771_verlauf/)

zusammen mit 14770.

<img src="14771_verlauf/bilder/beispiel_diagramm.jpg" width="640" alt="Verlaufsspeicher für Diagramme">

### [14775 RLT Luftqualitätsregelung](14775_RLT_Luftqualitaet/)

Lüftungsanlage (RLT) mit Luftqualitätsregelung.

<img src="14775_RLT_Luftqualitaet/bilder/beispiel_funktionsprinzip.png" width="640" alt="RLT Luftqualitätsregelung">

### [14776 WRG-Pumpenregelung](14776_WRG_Pumpenregelung/)

WRG-Pumpe an einem Druckluft-Kompressor.

<img src="14776_WRG_Pumpenregelung/bilder/beispiel_simulation.png" width="640" alt="WRG-Pumpenregelung">

### [14777 Kompressor-Klappensteuerung](14777_Kompressor_Klappensteuerung/)

Klappen eines Kompressorraums (Sommer/Winter).

<img src="14777_Kompressor_Klappensteuerung/bilder/beispiel_klappen.png" width="640" alt="Kompressor-Klappensteuerung">

### [14778 Szenen-Server](14778_szenenserver/)

Szenensteuerung über eigene Webseite.

<img src="14778_szenenserver/bilder/beispiel_szenen.png" width="640" alt="Szenen-Server">

### [14783 Kamera-Proxy](14783_kameraproxy/)

Axis-Kameras per Digest für den QC-Client.

<img src="14783_kameraproxy/bilder/beispiel_pruefseite.png" width="640" alt="Kamera-Proxy">

### [14784 Meldungsspeicher](14784_meldungsspeicher/)

Eigenes Meldungsarchiv (z. B. Wetterstation, Alarmanlage) – 16 Melder mit Texten, Freitext, Quittieren; Abruf über den Visu-Server 14770.

## Regeln

- ID steht im Namen (alle Sprachen), ID und Version stehen in der Hilfe.
- Neue Bausteine bekommen die nächste freie ID aus 14770–14789.
- HTTP-Bausteine: der HS leitet https://<HS>/<Basis-Pfad>/ an den Port weiter – gleiche Adresse und gleiches Zertifikat wie der HS. Port nie 0 (sonst 503) und nie doppelt.
- iKOs per Experte-CSV-Import anlegen (Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren).
- HTTP-Bausteine: E1/E2 in config.json mit Typ "base_path" bzw. "destination_port" deklarieren (nicht string/number) – sonst fehlt die Kennung in der .hsl (5000-Zeile endet auf |0|0) und der HS legt keine Weiterleitung an (404, obwohl der Baustein „Bereit“ meldet).
- Jede Änderung an einem Baustein (neu, Version, Port, Pfad) in CHANGELOG.md eintragen.

## Lizenz

GPL-3.0, siehe [LICENSE](LICENSE). Entwickelt mit Claude (Anthropic). Gira, HomeServer und QuadClient sind Marken der Gira Giersiepen GmbH & Co. KG; dieses Projekt ist kein Produkt von Gira. Der Gira-Generator (HSL3 SDK) ist nicht enthalten.

Bilder neu erzeugen: `python3 tools/blockbild.py <Ordner>` (Baustein), `python3 tools/prinzipbilder.py` (14776/14777), danach `python3 tools/readmes.py`.
