# 14777 Kompressor-Klappensteuerung – Version 1.2

**ID 14777 · Version 1.2 · HSL 1.0 (Formelbaustein)**

Klappen eines Kompressorraums (Sommer/Winter).

## Beschreibung (aus dem Baustein)

```
BadSmiley0815 · GPL-3.0

Ersetzt eine Klappen- und Raumtemperatursteuerung aus Einzelbausteinen
(Sommer/Winter 19830, 2x PID 19211, Sperren, Telegrammgeneratoren).

Sommer/Winter: Mittelwert der Außentemperatur wie 19830 aus den Werten um
  7, 14 und 22 Uhr: (T7 + T14 + 2*T22)/4, remanent. Mittel >= E4 -> Sommer.
Sommer: M1..M7 = Sommer-Vorgaben E14..E20 (gesendet bei Verdichter EIN,
  Umschaltung, Auto EIN oder Änderung einer Vorgabe). A11/A12 = 0.
Winter: M3 Kanal 2 außen und M5 Lager = Winter-Vorgaben E23/E25 (M5 Standard 50 %)
  (Abwärme geht in den Nebenraum).
  PI-Regler Kompressorraum (Fühler T1): M4 Umluft = y1, M6 = M7 = 100 - y1.
  PI-Regler Halle 1.OG (Fühler T4):     M2 innen  = y4, M1     = 100 - y4.
  Die Regler laufen im Winter immer (auch bei Verdichter AUS), Start stoßfrei
  ab Winter-Vorgabe M4 bzw. M2. Integrator auf 0..100 begrenzt.
  Fühler außerhalb -30..80 °C: Regler hält den letzten Wert.
Betriebsart E2<>1: Baustein sendet keine Klappenwerte (Hand), Status 0.
Ausgänge M1..M7 senden ganzzahlig und nur bei Änderung (bzw. erzwungen).
A13 Status: 0 = Hand, 1 = Sommer, 2 = Winter.
V1.2: Kühlregler (E28..E30, A14) entfernt; A11/A12 im Sommer 0;
      Pin-Namen Regler Kompressorraum (T1) / Halle 1.OG (T4).
V1.1: Kühlregler T1 (M3/M5 gegenläufig).  V1.0: erste Version.
## 14777 Kompressor-Klappensteuerung.End
```

Import im Experten: Logikbausteine → Importieren → `14777_Kompressor_Klappensteuerung.hsl`.

iKOs bei Bedarf per CSV-Import anlegen: Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren.
