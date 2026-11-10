"""Hilfeseiten DE/EN für 14775 im Aufbau der Gira-Hilfevorlage (log55555.html),
mit eingebetteten Grafiken und Beispieltabelle (aus der Bausteinlogik gerechnet)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graphics  # noqa: E402

ID = "14775"

EXTRA_CSS = """
.fig { margin: 14px 0 18px 0; }
.fig img { max-width: 100%; height: auto; border: 1px solid #dfe4e8; }
.fig .cap { font-size: 0.9em; color: #555; margin-top: 4px; }
.lead { font-size: 1.05em; margin: 6px 0 12px 0; }
.step { margin: 4px 0; }
.ex td, .ex th { padding: 4px 7px; text-align: center; white-space: nowrap; }
.ex td.l, .ex th.l { white-space: normal; }
.ex td.l, .ex th.l { text-align: left; }
.ex td.hl { font-weight: bold; }
.kv td { padding: 3px 10px 3px 0; vertical-align: top; }
table.io { border-collapse: collapse; width: 100%; margin: 8px 0 14px 0; font-size: 0.95em; }
table.io th { background: #3c4a57; color: #fff; text-align: left; padding: 7px 9px; font-weight: bold; }
table.io td { padding: 6px 9px; border-bottom: 1px solid #e3e7ea; vertical-align: top; }
table.io tr:nth-child(even) td { background: #f7f9fa; }
table.io .c { text-align: center; white-space: nowrap; }
table.io tr.grp td { background: #e9eef2; color: #2b3640; font-weight: bold; padding: 5px 9px;
                     border-left: 4px solid #8aa6c1; border-bottom: 1px solid #cfd8df; }
table.io-out tr.grp td { border-left-color: #d08a80; }
table.io td.nm { font-weight: bold; color: #1f2a33; }
table.io td.std { font-family: Consolas, monospace; }
table.io td.dpt { font-family: Consolas, monospace; font-weight: bold; }
table.io td.dpt span { font-family: Arial, sans-serif; font-weight: normal; font-size: 0.85em; color: #6b7782; }
.badge { display: inline-block; min-width: 30px; padding: 2px 6px; border-radius: 10px; font-weight: bold;
         font-size: 0.9em; text-align: center; color: #fff; }
.b-in { background: #3f8f5a; }
.b-out { background: #c0533f; }
table.mx { width: auto; }
.amp { font-size: 1.3em; line-height: 1em; vertical-align: -2px; }
.amp.a0 { color: #2e9a5a; } .amp.a1 { color: #e0b000; } .amp.a2 { color: #d0392b; }
table.mx td, table.mx th { padding: 6px 16px; }
"""

TXT = {
 "DE": dict(
  title="14775 RLT Luftqualitätsregelung", back="Zurück", fwd="Vor", search="Suchen", help="Hilfe",
  logic="Logik", content="Inhalt", nr="Nr.", name="Name", init="Init", descr="Beschreibung",
  warn="Achtung", hint="Hinweis", note="Tipp",
  chapters=["Beschreibung", "Funktionsweise", "Beispiele", "Eingänge", "Ausgänge", "Inbetriebnahme", "Sonstiges"],
  lead="""Bedarfsgerechter Betrieb einer RLT-Anlage mit Kreuzstrom-Wärmetauscher <b>ohne Bypassklappe</b>
nach der Raumluftqualität. Bei guter Luft läuft die Anlage mit viel Umluft und niedriger Drehzahl und spart
Heizenergie. Bei schlechter Luft wird mit Außenluft und hoher Drehzahl gelüftet. Im Sommer hilft ein
leichter Abluftüberschuss („Freecooling“), Wärme aus der Halle abzuführen. Eine Instanz je Anlage.""",
  ov_cap="Bild 1: Funktionsprinzip – was aus welchen Eingängen berechnet wird.",
  s1="1. Betriebsfreigabe", t1="""Das Zeitprogramm an E1 ist nur noch eine <b>Freigabe</b>, es gibt keine
Drehzahlen mehr vor.<br>
<b>E1 = 1 (EIN):</b> Klappen-, Ventilator-, Freecooling- und Temperaturregelung arbeiten. A6 = 1 gibt die
Temperaturregelung frei.<br>
<b>E1 = 0 (AUS):</b> Zu- und Abluftventilator 0 %, Außen- und Fortluftklappe 0 % (zu), Umluftklappe auf E23, A6 = 0.""",
  s2="2. Klappen nach Luftqualität", t2="""Der Luftqualitätswert (E2) wird auf eine Kennlinie zwischen
„gut“ (E6) und „schlecht“ (E7) gelegt und ergibt einen Anteil von 0–100 % (Ausgang A10). Daraus werden
die drei Klappen linear (LINEA) zwischen ihren Werten für gut und schlecht gestellt. Unterhalb von „gut“
und oberhalb von „schlecht“ bleiben die Klappen auf ihren Endwerten.""",
  cap_d="Bild 2: Klappenstellung über der Luftqualität (Standardwerte). In der Mitte zwischen E6 und E7: Umluft 40 %, Außen- und Fortluft 60 %.",
  s21="2.1 Übertemperatur", t21="""Liegt die Raumtemperatur mehr als E14 (1,0 K) über dem Sollwert, wird die
Klappenautomatik übersteuert: <b>Umluft 0 %, Außenluft 100 %, Fortluft 100 %</b>. Erst wenn die
Übertemperatur unter E15 (0,5 K) gefallen ist, regelt der Baustein wieder nach Luftqualität. So pendelt
die Anlage nicht um die Schaltschwelle. A7 zeigt den Zustand.""",
  cap_ot="Bild 3: Hysterese. Rot: bei steigender Temperatur ab +1,0 K auf 100 % Außenluft. Blau gestrichelt: bei fallender Temperatur erst unter +0,5 K zurück.",
  s3="3. Ventilatoren nach Luftqualität", t3="""Zu- und Abluft erhalten dieselbe Grunddrehzahl, linear
zwischen der Mindestdrehzahl E16 (gute Luft) und der Maximaldrehzahl E17 (schlechte Luft). Die Zuluft
wird danach nur noch vom Freecooling korrigiert.""",
  cap_f="Bild 4: Grunddrehzahl über der Luftqualität.",
  s4="4. Freecooling (Zuluftreduzierung)", t4="""Weil der Wärmetauscher keinen Bypass hat, wird bei
Übertemperatur und kühler Außenluft nur die <b>Zuluft</b> reduziert. Die Abluft bleibt, dadurch entsteht
ein leichter Unterdruck. Kühlere Außenluft strömt über Tore, Fenster und Undichtigkeiten nach und nimmt
die Wärme mit.<br><br>
<b>Aktiv, wenn:</b> E18 (12 °C) &lt; Außentemperatur &lt; Raumtemperatur <b>und</b> Raumtemperatur &gt; Sollwert.<br>
<b>Korrektur:</b> aus ΔT = Raum − Soll linear zwischen E19 (0 K → 0 %) und E20 (5 K → E21 = 100 %).<br>
<b>Zuluft</b> = Grunddrehzahl × (1 − Korrektur). Mit E22 lässt sich eine Untergrenze für die Zuluft
setzen (0 = keine, die Zuluft kann dann bis 0 % gehen).""",
  cap_fc="Bild 5: Links die Korrektur-Kennlinie, rechts das Beispiel: ΔT = 2,5 K ergibt 50 % Korrektur, aus 60/60 % wird Zuluft 30 % / Abluft 60 %.",
  s5="5. Ampel Luftqualität", t5="""A12 zeigt die Luftqualität als Ampel für Visu, Displays oder Meldungen:
<b>0 = grün</b>, <b>1 = gelb</b> ab E24, <b>2 = rot</b> ab E25. Beim Zurückschalten wirkt die Hysterese E26: Rot
wird erst unter E25 − E26 wieder gelb, Gelb erst unter E24 − E26 wieder grün. So flackert die Ampel nicht, wenn
der Messwert um eine Schwelle schwankt. Die Ampel wird auch bei Anlage AUS berechnet. Ist die Kennlinie fallend
eingestellt (E7 &lt; E6, z. B. Luftqualität in %), schaltet auch die Ampel in diese Richtung: kleiner = schlechter.<br>
<b>Visu-Tipp:</b> Im Experten den Wert von A12 über eine Werte-Liste in ein grünes, gelbes oder rotes Symbol umsetzen.""",
  cap_amp="Bild 6: Ampel mit Standardwerten (gelb ab 1000 ppm, rot ab 1400 ppm, Hysterese 50 ppm).",
  ex_intro="Die Werte sind mit der Logik des Bausteins und den Standardeinstellungen gerechnet (CO₂-Sensor, gut = 800 ppm, schlecht = 1400 ppm, Soll 20 °C).",
  ex_head=["Situation", "E1", "E2 LQ", "E3 Raum", "E5 Außen", "A1 Zuluft", "A2 Abluft", "A3 UM", "A4 AU", "A5 FO", "A12 Ampel", "Wirkung"],
  ex_rows=[
   ("Nacht, Anlage AUS", dict(enable=0, aq=600, t_room=18, t_out=3), "alles aus, Klappen zu"),
   ("Gute Luft, Winter", dict(enable=1, aq=750, t_room=20, t_out=2), "Mindestdrehzahl, viel Umluft"),
   ("Mittlere Luft", dict(enable=1, aq=1100, t_room=20.2, t_out=2), "Kennlinie Mitte"),
   ("Schlechte Luft", dict(enable=1, aq=1600, t_room=20, t_out=2), "volle Außenluft, Maximaldrehzahl"),
   ("Warm, außen wärmer", dict(enable=1, aq=900, t_room=21.5, t_out=26), "Übertemperatur, kein Freecooling"),
   ("Warm, außen kühl", dict(enable=1, aq=1100, t_room=22.5, t_out=15), "Übertemperatur + Freecooling −50 %"),
   ("Leicht warm, außen kühl", dict(enable=1, aq=900, t_room=20.8, t_out=14), "nur Freecooling −16 %"),
   ("Sehr warm, außen 12 °C", dict(enable=1, aq=1100, t_room=24, t_out=12), "Außen nicht über 12 °C → kein Freecooling"),
  ],
  set_title="Einstellbeispiele",
  sets=[("CO₂-Sensor (ppm)", "E6 = 800, E7 = 1400. Höhere Werte bedeuten schlechtere Luft."),
        ("Luftqualität in % (100 = gut)", "E6 = 80, E7 = 30. Die Kennlinie darf fallen, der Baustein rechnet richtig herum."),
        ("Zuluft nie ganz aus", "E22 = 20: Beim Freecooling geht die Zuluft nicht unter 20 %."),
        ("Weniger aggressives Freecooling", "E21 = 60: Auch bei großem ΔT wird die Zuluft höchstens um 60 % reduziert."),
        ("Umluftklappe bei AUS offen", "E23 = 100: Bei Anlage AUS steht die Umluftklappe offen."),
        ("Ampel für Luftqualität in %", "E24 = 50, E25 = 30, E26 = 3 (bei E6 = 80, E7 = 30): unter 50 % gelb, unter 30 % rot.")],
  warn_t="Die alten Zeitprogramme für Zu- und Abluft (% Drehzahl) entfallen. A1/A2 direkt auf die Drehzahl-Sollwerte legen und das Zeitprogramm nur noch an E1 anschließen.",
  hint_t="Kein Fühler-Ausfallschutz: Der Baustein rechnet mit dem letzten Wert an E2–E5. Bei Bedarf eine Fühlerüberwachung vorschalten.",
  steps=["<b>Import:</b> Experte → Logikbausteine → Importieren → <i>14775_RLT_Luftqualitaet.hslz</i>.",
         "<b>iKOs anlegen:</b> am schnellsten per CSV-Import: <b>Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren</b>. Der Import übernimmt die Endpunkt-IDs (CO@…). Nicht über ESF/OPC, dort müssen die Endpunkte von Hand nachgetragen werden.",
         "<b>Verdrahten:</b> E1 Zeitprogramm, E2 Luftqualitätssensor, E3 Raumtemperatur, E4 Raumsoll, E5 Außentemperatur; A1/A2 auf die Ventilatoren, A3–A5 auf die Klappen, A6 auf die Freigabe der Temperaturregelung. Passende DPTs stehen in Kapitel 4 und 5.",
         "<b>Parameter</b> E6–E23 als Festwert im Logikeditor eintragen oder ein iKO anschließen, wenn sie in der Visu einstellbar sein sollen.",
         "<b>Prüfen:</b> In der Debug-Seite zeigt der Baustein Status und ΔT. A11 enthält denselben Klartext."],
  misc=[("Baustein-ID:", ID), ("Version:", "{v}"), ("Kategorie:", "Lüftung"),
        ("Neuberechnung bei Start:", "Ja"), ("Baustein ist remanent:", "Nein"),
        ("Ausgänge:", "senden nur bei Änderung (sbc)")],
  sbc="sbc = send by change"),
 "EN": dict(
  title="14775 AHU air quality control", back="Back", fwd="Forward", search="Search", help="Help",
  logic="Logic", content="Contents", nr="No.", name="Name", init="Init", descr="Description",
  warn="Warning", hint="Note", note="Tip",
  chapters=["Description", "Operation", "Examples", "Inputs", "Outputs", "Commissioning", "Miscellaneous"],
  lead="""Demand-controlled operation of an air handling unit with cross-flow heat exchanger <b>without
bypass</b>, based on indoor air quality. Good air: lots of recirculation and low fan speed to save heating
energy. Bad air: outdoor air and high speed. In summer a slight exhaust surplus (“free cooling”) helps to
remove heat from the hall. One instance per unit.""",
  ov_cap="Figure 1: principle of operation.",
  s1="1. Enable", t1="""The time schedule on I1 only <b>enables</b> the unit.<br>
<b>I1 = 1:</b> damper, fan, free cooling and temperature control active, O6 = 1.<br>
<b>I1 = 0:</b> fans 0 %, outdoor and exhaust dampers 0 % (closed), recirculation damper at I23, O6 = 0.""",
  s2="2. Dampers by air quality", t2="""The air quality (I2) is mapped between “good” (I6) and “bad” (I7)
to 0–100 % (output O10). The three dampers move linearly between their good and bad values and are
limited outside the range.""",
  cap_d="Figure 2: damper position vs. air quality (defaults).",
  s21="2.1 Overtemperature", t21="""If the room is more than I14 (1.0 K) above setpoint the dampers are
overridden: <b>recirculation 0 %, outdoor 100 %, exhaust 100 %</b>. Back to automatic below I15 (0.5 K).
O7 shows the state.""",
  cap_ot="Figure 3: hysteresis.",
  s3="3. Fans by air quality", t3="""Supply and exhaust get the same base speed, linear between I16 (good)
and I17 (bad). Only the supply is then corrected by free cooling.""",
  cap_f="Figure 4: base fan speed vs. air quality.",
  s4="4. Free cooling (supply reduction)", t4="""Without bypass, only the <b>supply</b> fan is reduced when
the hall is too warm and outdoor air is cool. Exhaust stays, creating slight negative pressure; cooler outdoor
air flows in through gates and leaks.<br><br>
<b>Active if:</b> I18 (12 °C) &lt; outdoor &lt; room <b>and</b> room &gt; setpoint.<br>
<b>Correction:</b> from ΔT = room − setpoint, linear between I19 (0 K → 0 %) and I20 (5 K → I21 = 100 %).<br>
<b>Supply</b> = base × (1 − correction). I22 sets a lower supply limit (0 = none).""",
  cap_fc="Figure 5: correction curve and example (ΔT = 2.5 K → 50 %, 60/60 % becomes 30/60 %).",
  s5="5. Air quality traffic light", t5="""O12 shows the air quality as a traffic light: <b>0 = green</b>,
<b>1 = yellow</b> from I24, <b>2 = red</b> from I25. Switching back uses hysteresis I26. Also calculated when the plant
is OFF. With a falling curve (I7 &lt; I6) the traffic light follows: lower = worse.""",
  cap_amp="Figure 6: traffic light with defaults (yellow from 1000 ppm, red from 1400 ppm, hysteresis 50 ppm).",
  ex_intro="Calculated with the module logic and default settings (CO₂ sensor, good = 800 ppm, bad = 1400 ppm, setpoint 20 °C).",
  ex_head=["Situation", "I1", "I2 AQ", "I3 room", "I5 outd.", "O1 supply", "O2 exhaust", "O3 REC", "O4 OA", "O5 EA", "O12 light", "Effect"],
  ex_rows=[
   ("Night, plant OFF", dict(enable=0, aq=600, t_room=18, t_out=3), "all off, dampers closed"),
   ("Good air, winter", dict(enable=1, aq=750, t_room=20, t_out=2), "min. speed, high recirculation"),
   ("Medium air", dict(enable=1, aq=1100, t_room=20.2, t_out=2), "middle of curve"),
   ("Bad air", dict(enable=1, aq=1600, t_room=20, t_out=2), "full outdoor air, max. speed"),
   ("Warm, outdoor warmer", dict(enable=1, aq=900, t_room=21.5, t_out=26), "overtemperature, no free cooling"),
   ("Warm, outdoor cool", dict(enable=1, aq=1100, t_room=22.5, t_out=15), "overtemperature + free cooling −50 %"),
   ("Slightly warm, outdoor cool", dict(enable=1, aq=900, t_room=20.8, t_out=14), "free cooling −16 % only"),
   ("Very warm, outdoor 12 °C", dict(enable=1, aq=1100, t_room=24, t_out=12), "outdoor not above 12 °C"),
  ],
  set_title="Setting examples",
  sets=[("CO₂ sensor (ppm)", "I6 = 800, I7 = 1400."),
        ("Air quality in % (100 = good)", "I6 = 80, I7 = 30 – falling curves are supported."),
        ("Supply never fully off", "I22 = 20."),
        ("Gentler free cooling", "I21 = 60."),
        ("Recirculation open when OFF", "I23 = 100."),
        ("Traffic light for air quality in %", "I24 = 50, I25 = 30, I26 = 3 (with I6 = 80, I7 = 30).")],
  warn_t="The old time schedules for supply/exhaust speeds are obsolete. Connect O1/O2 to the fan setpoints and the schedule to I1 only.",
  hint_t="No sensor failure protection: the module uses the last value on I2–I5.",
  steps=["<b>Import:</b> Experte → Logic modules → Import → <i>14775_RLT_Luftqualitaet.hslz</i>.",
         "<b>Create iKOs</b> via CSV import: <b>Communication objects → Extras → Data synchronisation → Synchronise/import CSV file</b> (carries the endpoint IDs CO@…; do not use ESF/OPC).",
         "<b>Wire</b> I1–I5 and O1–O6.",
         "<b>Parameters</b> I6–I23 as fixed values or via iKOs for adjustment in the visualisation.",
         "<b>Check</b> the debug page (status, ΔT); O11 shows the same text."],
  misc=[("Module ID:", ID), ("Version:", "{v}"), ("Category:", "Ventilation"),
        ("Recalculation on start:", "Yes"), ("Module is remanent:", "No"),
        ("Outputs:", "send by change (sbc)")],
  sbc="sbc = send by change"),
}

IN_DESCR = {
 "DE": ["0 = Anlage AUS, ≠ 0 = Anlage EIN (Zeitprogramm, nur Freigabe).",
        "Istwert Luftqualitätssensor (z. B. CO₂ in ppm oder VOC).",
        "Raumtemperatur in °C.", "Raumsolltemperatur in °C.", "Außentemperatur in °C.",
        "Wert für „gute Luftqualität“ (Kennlinienbeginn).", "Wert für „schlechte Luftqualität“ (Kennlinienende).",
        "Umluftklappe bei guter Luftqualität.", "Umluftklappe bei schlechter Luftqualität.",
        "Außenluftklappe bei guter Luftqualität.", "Außenluftklappe bei schlechter Luftqualität.",
        "Fortluftklappe bei guter Luftqualität.", "Fortluftklappe bei schlechter Luftqualität.",
        "Übertemperatur EIN, wenn Raum − Soll größer als dieser Wert.",
        "Übertemperatur AUS, wenn Raum − Soll kleiner als dieser Wert (Hysterese).",
        "Ventilatordrehzahl bei guter Luftqualität.", "Ventilatordrehzahl bei schlechter Luftqualität.",
        "Freecooling nur, wenn die Außentemperatur über diesem Wert liegt.",
        "ΔT (Raum − Soll), bei dem die Korrektur beginnt (0 %).",
        "ΔT, bei dem die Korrektur den Wert E21 erreicht.",
        "Zuluftkorrektur bei ΔT = E20 (100 % = Zuluft aus).",
        "Untergrenze der Zuluft bei aktivem Freecooling (0 = keine).",
        "Stellung der Umluftklappe bei Anlage AUS.",
        "Ab diesem Luftqualitätswert zeigt die Ampel gelb.",
        "Ab diesem Luftqualitätswert zeigt die Ampel rot.",
        "Hysterese beim Zurückschalten (rot → gelb erst unter E25 − E26, gelb → grün erst unter E24 − E26)."],
 "EN": ["0 = plant OFF, ≠ 0 = plant ON (time schedule, enable only).",
        "Air quality sensor value (e.g. CO₂ ppm or VOC).", "Room temperature °C.", "Room setpoint °C.",
        "Outdoor temperature °C.", "Value for “good” air quality.", "Value for “bad” air quality.",
        "Recirculation damper at good.", "Recirculation damper at bad.", "Outdoor damper at good.",
        "Outdoor damper at bad.", "Exhaust damper at good.", "Exhaust damper at bad.",
        "Overtemperature ON above room − setpoint.", "Overtemperature OFF below (hysteresis).",
        "Fan speed at good air quality.", "Fan speed at bad air quality.",
        "Free cooling only above this outdoor temperature.", "ΔT where correction starts (0 %).",
        "ΔT where correction reaches I21.", "Supply correction at ΔT = I20.",
        "Lower supply limit during free cooling (0 = none).", "Recirculation damper when plant OFF.",
        "Traffic light turns yellow from this value.", "Traffic light turns red from this value.",
        "Hysteresis when switching back (red → yellow below I25 − I26, yellow → green below I24 − I26)."],
}
OUT_DESCR = {
 "DE": ["Drehzahlsollwert Zuluftventilator (inkl. Freecooling-Korrektur).", "Drehzahlsollwert Abluftventilator.",
        "Stellung Umluftklappe.", "Stellung Außenluftklappe.", "Stellung Fortluftklappe.",
        "1 = Anlage freigegeben (Freigabe für Temperaturregelung).", "1 = Übertemperatur, 100 % Außenluft.",
        "1 = Freecooling aktiv.", "Aktuelle Zuluftreduzierung durch Freecooling.",
        "Luftqualität auf der Kennlinie: 0 % = gut, 100 % = schlecht (für die Visu).", "Klartext-Zustand.",
        "Ampel Luftqualität: <b>0 = grün, 1 = gelb, 2 = rot</b>. Wird auch bei Anlage AUS berechnet."],
 "EN": ["Supply fan speed setpoint (incl. free cooling).", "Exhaust fan speed setpoint.",
        "Recirculation damper.", "Outdoor air damper.", "Exhaust damper.", "1 = plant enabled.",
        "1 = overtemperature.", "1 = free cooling active.", "Current supply reduction.",
        "Air quality on curve: 0 % good, 100 % bad.", "Plain-text status.",
        "Air quality traffic light: <b>0 = green, 1 = yellow, 2 = red</b>. Also calculated when the plant is OFF."],
}


IN_DPT = ["1.001", "9.008", "9.001", "9.001", "9.001", "9.008", "9.008",
          "5.001", "5.001", "5.001", "5.001", "5.001", "5.001", "9.002", "9.002",
          "5.001", "5.001", "9.001", "9.002", "9.002", "5.001", "5.001", "5.001",
          "9.008", "9.008", "9.008"]
OUT_DPT = ["9.xxx", "9.xxx", "9.xxx", "9.xxx", "9.xxx", "1.001", "1.001", "1.001", "5.001", "5.001", "16.000", "5.010"]
DPT_NAME = {
 "DE": {"1.001": "Schalten", "5.001": "Prozent (0–100 %)", "9.001": "Temperatur (°C)",
        "9.002": "Temperaturdifferenz (K)", "9.008": "Luftqualität (ppm)", "16.000": "Text",
        "5.010": "Zählwert 8 Bit (0–255)", "9.xxx": "2-Byte-Gleitkomma, 0–100 (alternativ 5.001)"},
 "EN": {"1.001": "Switch", "5.001": "Percentage (0–100 %)", "9.001": "Temperature (°C)",
        "9.002": "Temperature difference (K)", "9.008": "Air quality (ppm)", "16.000": "Text",
        "5.010": "Counter 8 bit (0–255)", "9.xxx": "2-byte float, 0–100 (alternatively 5.001)"},
}
DPT_NOTE = {
 "DE": """Die DPTs sind Empfehlungen für die angeschlossenen KOs. Der Baustein rechnet nur mit Zahlen und kennt
keinen DPT. Liefert der Luftqualitätssensor einen anderen Typ (z. B. Prozent 5.001 oder VOC-Index als 2-Byte-Zahl),
E2, E6 und E7 auf denselben DPT legen und die Grenzen passend einstellen.<br>
A11 (Status) ist länger als 14 Zeichen. An einem 14-Byte-KO (DPT 16.000) wird er abgeschnitten, deshalb für die Visu
ein Text-iKO ohne Längenbegrenzung verwenden.<br>
<b>A1–A5</b> geben immer 0–100 % aus. Die 0–10-V-Ausgänge für Klappen und Ventilatoren sind meist
2-Byte-Gleitkomma-GAs (im Experten Format „EIS5 / 2 Byte Gleitkomma“), die den Prozentwert direkt bekommen (100 = 10 V).
An einem 1-Byte-KO (DPT 5.001) funktioniert der Ausgang genauso, der HomeServer wandelt den Wert selbst um.<br>
Für eine Ampel gibt es im KNX-Standard keinen eigenen Datenpunkttyp. A12 ist deshalb ein 8-Bit-Wert (DPT 5.010) mit
0 = grün, 1 = gelb, 2 = rot. E24–E26 haben dieselbe Einheit wie E2.""",
 "EN": """DPTs are recommendations for the connected objects; the module only calculates with numbers. If the air
quality sensor uses another type (e.g. 5.001 or a VOC index), set I2, I6 and I7 to the same DPT and adjust the limits.<br>
O1–O5 always output 0–100 %; 2-byte float objects (0–10 V outputs) get the percentage directly, 5.001 works as well.<br>
O11 (status) is longer than 14 characters and is truncated on a 14-byte object (DPT 16.000).<br>
KNX has no dedicated traffic-light DPT; O12 is an 8-bit value (DPT 5.010): 0 = green, 1 = yellow, 2 = red.""",
}


AMP_TXT = {"DE": ("grün", "gelb", "rot"), "EN": ("green", "yellow", "red")}

UNIT = {"1.001": "0 / 1", "5.001": "%", "9.001": "°C", "9.002": "K", "9.008": "ppm", "16.000": "Text", "5.010": "0 / 1 / 2", "9.xxx": "%"}

IN_GROUPS = {
 "DE": [("Messwerte und Freigabe", 1, 5), ("Kennlinie Luftqualität", 6, 7), ("Klappen", 8, 13),
        ("Übertemperatur", 14, 15), ("Ventilatoren", 16, 17), ("Freecooling", 18, 22), ("Anlage AUS", 23, 23),
        ("Ampel Luftqualität", 24, 26)],
 "EN": [("Measured values and enable", 1, 5), ("Air quality curve", 6, 7), ("Dampers", 8, 13),
        ("Overtemperature", 14, 15), ("Fans", 16, 17), ("Free cooling", 18, 22), ("Plant OFF", 23, 23),
        ("Air quality traffic light", 24, 26)],
}
OUT_GROUPS = {
 "DE": [("Ventilatoren", 1, 2), ("Klappen", 3, 5), ("Zustände", 6, 8), ("Visu und Diagnose", 9, 12)],
 "EN": [("Fans", 1, 2), ("Dampers", 3, 5), ("States", 6, 8), ("Visualisation and diagnostics", 9, 12)],
}
IN_NAMES = {
 "DE": ["Freigabe Zeitprogramm", "Luftqualität Istwert", "Raumtemperatur", "Raumsolltemperatur", "Außentemperatur",
        "Grenze gute Luftqualität", "Grenze schlechte Luftqualität",
        "Umluftklappe bei gut", "Umluftklappe bei schlecht", "Außenluftklappe bei gut", "Außenluftklappe bei schlecht",
        "Fortluftklappe bei gut", "Fortluftklappe bei schlecht",
        "Übertemperatur EIN ab", "Übertemperatur AUS unter",
        "Mindestdrehzahl", "Maximaldrehzahl",
        "Außentemperatur mindestens", "ΔT Beginn Korrektur", "ΔT Ende Korrektur", "Korrektur bei ΔT Ende",
        "Zuluft-Untergrenze", "Umluftklappe bei AUS", "Ampel gelb ab", "Ampel rot ab", "Ampel Hysterese"],
 "EN": ["Enable time schedule", "Air quality actual", "Room temperature", "Room setpoint", "Outdoor temperature",
        "Limit good air quality", "Limit bad air quality",
        "Recirc. damper at good", "Recirc. damper at bad", "Outdoor damper at good", "Outdoor damper at bad",
        "Exhaust damper at good", "Exhaust damper at bad",
        "Overtemperature ON above", "Overtemperature OFF below",
        "Minimum speed", "Maximum speed",
        "Outdoor temperature minimum", "ΔT correction start", "ΔT correction end", "Correction at ΔT end",
        "Supply lower limit", "Recirc. damper when OFF", "Traffic light yellow from", "Traffic light red from",
        "Traffic light hysteresis"],
}
OUT_NAMES = {
 "DE": ["Zuluftventilator", "Abluftventilator", "Umluftklappe", "Außenluftklappe", "Fortluftklappe",
        "Anlage EIN / Freigabe Temperaturregelung", "Übertemperatur aktiv", "Freecooling aktiv",
        "Freecooling-Zuluftkorrektur", "Luftqualität Anteil schlecht", "Status", "Ampel Luftqualität"],
 "EN": ["Supply fan", "Exhaust fan", "Recirculation damper", "Outdoor air damper", "Exhaust air damper",
        "Plant ON / enable temperature control", "Overtemperature active", "Free cooling active",
        "Free cooling supply correction", "Air quality share bad", "Status", "Air quality traffic light"],
}
IO_TXT = {
 "DE": dict(std="Standard", unit="Einheit", empty="leer", sbc_all="Alle Ausgänge senden nur bei Änderung (sbc = send by change).",
            mx_title="Klappen auf einen Blick", mx_damper="Klappe", mx_good="bei guter Luft", mx_bad="bei schlechter Luft",
            mx_rows=[("Umluftklappe", 8, 9), ("Außenluftklappe", 10, 11), ("Fortluftklappe", 12, 13)],
            mx_ot="Bei Übertemperatur", mx_ot_val="Umluft 0 % · Außenluft 100 % · Fortluft 100 % (fest)"),
 "EN": dict(std="Default", unit="Unit", empty="empty", sbc_all="All outputs send on change only (sbc).",
            mx_title="Dampers at a glance", mx_damper="Damper", mx_good="good air", mx_bad="bad air",
            mx_rows=[("Recirculation", 8, 9), ("Outdoor air", 10, 11), ("Exhaust air", 12, 13)],
            mx_ot="On overtemperature", mx_ot_val="recirculation 0 % · outdoor 100 % · exhaust 100 % (fixed)"),
}


def _dpt(code, lang):
    return '<b>%s</b><br><span class="small">%s</span>' % (code, DPT_NAME[lang][code])


def _num(v, lang):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s.replace(".", ",") if lang == "DE" else s


def page(M, de, lang, version, figs):
    t = TXT[lang]
    h = []
    a = h.append

    def fig(name, cap):
        uri, w, _n = figs[lang][name]
        a('<div class="fig"><img src="%s" width="%d" alt=""><div class="cap">%s</div></div>' % (uri, w, cap))

    a('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">\n<html>\n<head>\n<link rel="stylesheet" href="style.css">')
    a('<title>%s - %s</title>\n<style>body { background: none; }%s</style>' % (t["logic"], t["title"], EXTRA_CSS))
    a('<meta http-equiv="Content-Type" content="text/html;charset=UTF-8">\n</head>\n<body>')
    a('<div class="top-title">%s</div>' % t["title"])
    a('<div class="nav"><a href="javascript:history.back()">%s</a> / <a href="javascript:history.forward()">%s</a> | '
      '<a href="hlpsearch.html">%s</a> | <a href="index.html">%s</a> / <a href="logic.html">%s</a> / %s</div>'
      % (t["back"], t["fwd"], t["search"], t["help"], t["logic"], t["title"]))
    a('<div class="index"><div class="index-title"><a id="doc_index_1_"></a>%s</div>' % t["content"])
    for i, c in enumerate(t["chapters"], 1):
        a('<div class="t-line"><div class="t-chapter"><a href="#auto_index_anchor_%d_">%d.</a></div>'
          '<div class="t-text"><a href="#auto_index_anchor_%d_">%s</a></div></div>' % (i, i, i, c))
    a('</div>\n<div class="content">')

    def head(n):
        a('<h2 class="t-line"><a id="auto_index_anchor_%d_"></a><span class="t-chapter">%d.</span>'
          '<span class="t-text">%s</span></h2>' % (n, n, t["chapters"][n - 1]))

    def box(cls, title, txt):
        a('<div class="alert-box %s"><div class="box-title">%s</div><div class="box-text"><div class="descr">%s</div></div></div>'
          % (cls, title, txt))

    # 1 Beschreibung
    a('<div class="topic">')
    head(1)
    a('<div class="descr lead">%s</div>' % t["lead"])
    a('<div class="descr">ID %s · Version %s</div>' % (ID, version))
    fig("overview", t["ov_cap"])
    box("ibox-warn", t["warn"], t["warn_t"])
    box("ibox-hint", t["hint"], t["hint_t"])
    a('</div>')

    # 2 Funktionsweise
    a('<div class="topic">')
    head(2)
    for key_s, key_t, f in (("s1", "t1", None), ("s2", "t2", ("dampers", "cap_d")), ("s21", "t21", ("ot", "cap_ot")),
                            ("s3", "t3", ("fans", "cap_f")), ("s4", "t4", ("fc", "cap_fc")), ("s5", "t5", ("amp", "cap_amp"))):
        a('<h3>%s</h3><div class="descr">%s</div>' % (t[key_s], t[key_t]))
        if f:
            fig(f[0], t[f[1]])
    a('</div>')

    # 3 Beispiele
    a('<div class="topic">')
    head(3)
    a('<div class="descr">%s</div>' % t["ex_intro"])
    a('<div class="xhtml"><table class="ex"><tr>%s</tr>' % "".join(
        '<th class="%s">%s</th>' % ("l" if i in (0, 11) else "", x) for i, x in enumerate(t["ex_head"])))
    for label, kw, effect in t["ex_rows"]:
        p = {i[0]: float(i[1]) for i in M.INPUTS}
        p.update({k: float(v) for k, v in kw.items()})
        o, _ = M.compute(p, False)
        cells = [label, "%d" % p["enable"], "%d ppm" % p["aq"], _num(p["t_room"], lang) + " °C",
                 _num(p["t_out"], lang) + " °C"]
        cells += ["%s %%" % _num(o[k], lang) for k in ("supply", "exhaust", "rec", "oa", "ex")]
        cells.append('<span class="amp a%d">&#9679;</span> %s' % (o["amp"], AMP_TXT[lang][o["amp"]]))
        cells.append(effect)
        a('<tr>%s</tr>' % "".join('<td class="%s">%s</td>' % (
            "l" if i in (0, 11) else ("hl" if i in (5, 6) else ""), c) for i, c in enumerate(cells)))
    a('</table></div>')
    a('<h3>%s</h3><table class="kv">%s</table>' % (t["set_title"], "".join(
        "<tr><td><b>%s</b></td><td>%s</td></tr>" % kv for kv in t["sets"])))
    a('</div>')

    io = IO_TXT[lang]
    pre_in, pre_out = ("E", "A") if lang == "DE" else ("I", "O")

    def io_table(kind, items, descr, dpts, groups, names):
        pre = pre_in if kind == "in" else pre_out
        a('<table class="io io-%s"><tr><th class="c">%s</th><th>%s</th><th class="c">%s</th>'
          '<th class="c">%s</th><th class="c">DPT</th><th>%s</th></tr>'
          % (kind, t["nr"], t["name"], io["std"], io["unit"], t["descr"]))
        for gname, first, last in groups[lang]:
            a('<tr class="grp"><td colspan="6">%s</td></tr>' % gname)
            for i in range(first, last + 1):
                it, d, dpt = items[i - 1], descr[i - 1], dpts[i - 1]
                std = io["empty"] if isinstance(it[1], str) else _num(it[1], lang)
                a('<tr><td class="c"><span class="badge b-%s">%s%d</span></td><td class="nm">%s</td>'
                  '<td class="c std">%s</td><td class="c">%s</td><td class="c dpt">%s<br><span>%s</span></td>'
                  '<td>%s</td></tr>' % (kind, pre, i, names[lang][i - 1], std, UNIT[dpt], dpt,
                                        DPT_NAME[lang][dpt], d))
        a('</table>')

    # 4 Eingänge
    a('<div class="topic">')
    head(4)
    io_table("in", M.INPUTS, IN_DESCR[lang], IN_DPT, IN_GROUPS, IN_NAMES)
    # Klappen-Matrix
    a('<h3>%s</h3><table class="io mx"><tr><th>%s</th><th class="c">%s</th><th class="c">%s</th></tr>'
      % (io["mx_title"], io["mx_damper"], io["mx_good"], io["mx_bad"]))
    for (nm, g, b) in io["mx_rows"]:
        a('<tr><td class="nm">%s</td><td class="c"><span class="badge b-in">%s%d</span> %s %%</td>'
          '<td class="c"><span class="badge b-in">%s%d</span> %s %%</td></tr>'
          % (nm, pre_in, g, _num(M.INPUTS[g - 1][1], lang), pre_in, b, _num(M.INPUTS[b - 1][1], lang)))
    a('<tr><td class="nm">%s</td><td class="c" colspan="2">%s</td></tr></table>' % (io["mx_ot"], io["mx_ot_val"]))
    a('</div>')

    # 5 Ausgänge
    a('<div class="topic">')
    head(5)
    io_table("out", M.OUTPUTS, OUT_DESCR[lang], OUT_DPT, OUT_GROUPS, OUT_NAMES)
    a('<div class="small">%s</div>' % io["sbc_all"])
    box("ibox-hint", t["hint"], DPT_NOTE[lang])
    a('</div>')

    # 6 Inbetriebnahme
    head(6)
    a('<div class="descr"><ol>%s</ol></div>' % "".join('<li class="step">%s</li>' % s for s in t["steps"]))

    # 7 Sonstiges
    head(7)
    a('<table class="table-logic-info">%s</table>' % "".join(
        "<tr><th>%s</th><td>%s</td></tr>" % (k, v.format(v=version)) for k, v in t["misc"]))
    a('</div>\n</body>\n</html>\n')
    return "\n".join(h)


def write(M, de, outdir, version):
    figs = graphics.render_all()
    for lang in ("DE", "EN"):
        with open(os.path.join(outdir, "%s-log%s.html" % (lang, ID)), "w", encoding="utf-8") as f:
            f.write(page(M, de, lang, version, figs))
