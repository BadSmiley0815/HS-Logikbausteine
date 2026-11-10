# HS-Logikbausteine – eigene Logikbausteine für den Gira HomeServer

Freie Logikbausteine (HSL3 und HSL 1.0) für den Gira HomeServer / FacilityServer – mit Quellcode, Hilfe und Einbauanleitung. Jeder Ordner enthält die importierbare `.hslz` bzw. `.hsl` und eine README.

Passend dazu: [QC-Client](https://github.com/BadSmiley0815/QC-Client) – der QuadClient im Browser.

## Übersicht – Stand 10.11.2026

Eigener ID-Bereich: **14770–14789** · nächste freie ID: **14784**

## Bausteine

| ID | Name | Version | Art | Port | Basis-Pfad | ex | Einsatz | Status |
|---|---|---|---|---|---|---|---|---|
| 14770 | Visu-Server | 1.10 | HSL3 | 8092 | visu-daten | 19107 | homeserver-webapp, Diagramme | in Betrieb |
| 14771 | Verlaufsspeicher für Diagramme | 2.7 | HSL3 |  | (über 14770) | 19105 | zusammen mit 14770 | in Betrieb |
| 14772 | KNX-Tunnel Senden | ? | HSL3 |  |  | 19101 | KNXnet/IP-Tunnel, Port 3671 an der fremden Linie | Ablage im Ordner Logikbausteine fehlt · ID auch von LOGIQ-Testbaustein genutzt (ignorieren) |
| 14773 | KNX-Tunnel Empfangen | ? | HSL3 |  |  | 19102 | KNXnet/IP-Tunnel | Ablage im Ordner Logikbausteine fehlt |
| 14774 | KNX-Tunnel Gateway-Server | ? | HSL3 | ? | ? | 19109 | Webseite GA → DPT → iKO | Ablage fehlt · Port unbekannt, beim nächsten Bearbeiten nachtragen |
| 14775 | RLT Luftqualitätsregelung | 1.5 | HSL3 |  |  |  | Lüftungsanlage (RLT) mit Luftqualitätsregelung | in Betrieb |
| 14776 | WRG-Pumpenregelung | 1.0 | HSL 1.0 (Formel) |  |  |  | WRG-Pumpe an einem Druckluft-Kompressor | in Betrieb |
| 14777 | Kompressor-Klappensteuerung | 1.2 | HSL 1.0 (Formel) |  |  |  | Klappen eines Kompressorraums (Sommer/Winter) | in Betrieb |
| 14778 | Szenen-Server | 4.2 | HSL3 | 8093 | szenen | 19108 | Szenensteuerung über eigene Webseite | in Betrieb |
| 14779 | Zeitschaltuhr + Aufzeichnung | – | HSL3 | 8094 (reserviert) |  |  | Zeitschaltuhren und Werteaufzeichnung je KO | geplant |
| 14780 | (verworfene Parallelfassung KNX-Tunnel) | – |  |  |  |  |  | nicht verwenden |
| 14781 | (verworfene Parallelfassung KNX-Tunnel) | – |  |  |  |  |  | nicht verwenden |
| 14782 | (verworfene Parallelfassung KNX-Tunnel) | – |  |  |  |  |  | nicht verwenden |
| 14783 | Kamera-Proxy | 0.1 (Prüffassung) | HSL3 | 8095 | kamera |  | Axis-Kameras per Digest für den QC-Client | in Arbeit |

## Ports

| Port | Baustein | Adresse |
|---|---|---|
| 8092 | 14770 Visu-Server | https://<HS>/visu-daten/ |
| 8093 | 14778 Szenen-Server | https://<HS>/szenen/ |
| 8094 (reserviert) | 14779 Zeitschaltuhr + Aufzeichnung |  |
| 8095 | 14783 Kamera-Proxy | https://<HS>/kamera/ |
| ? | 14774 KNX-Tunnel Gateway-Server |  |

## Freie IDs

14784, 14785, 14786, 14787, 14788, 14789

## Regeln

- ID steht im Namen (alle Sprachen), ID und Version stehen in der Hilfe.
- Neue Bausteine bekommen die nächste freie ID aus 14770–14789.
- HTTP-Bausteine: der HS leitet https://<HS>/<Basis-Pfad>/ an den Port weiter – gleiche Adresse und gleiches Zertifikat wie der HS. Port nie 0 (sonst 503) und nie doppelt.
- iKOs per Experte-CSV-Import anlegen (Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren).

## Lizenz

GPL-3.0, siehe [LICENSE](LICENSE). Entwickelt mit Claude (Anthropic). Gira, HomeServer und QuadClient sind Marken der Gira Giersiepen GmbH & Co. KG; dieses Projekt ist kein Produkt von Gira. Der Gira-Generator (HSL3 SDK) ist nicht enthalten.
