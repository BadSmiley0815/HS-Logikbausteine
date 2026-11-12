"""Hilfe-Seiten DE/EN fuer 14785 (Ein-/Ausgangstabellen aus dem Quelltext)."""
import html
import os

CSS = ("body{font:14px/1.5 Arial,sans-serif;margin:16px;max-width:900px}table{border-collapse:collapse;width:100%}"
       "td,th{border:1px solid #ccc;padding:4px 6px;text-align:left;vertical-align:top}th{background:#eef}"
       "code{background:#f3f3f3;padding:0 3px}.b{display:inline-block;background:#e8eefc;border-radius:10px;"
       "padding:1px 8px;margin-right:6px}.w{background:#fff6e0;border-left:4px solid #e0a000;padding:6px 10px}")

INFO_DE = {
    "mode": "0 = Master (erster Baustein), 1 = Folge. Folge-Bausteine bekommen alle allgemeinen Werte über die Kaskade; ihre E5–E31 bleiben frei.",
    "first": "Nummer des ersten Kreises dieses Bausteins für Status und Anzeige (Master 1, Folge 1 = 6, Folge 2 = 11 …).",
    "cin": "Nur Folge: A19 des Vorgängers anschließen (Text-iKO).",
    "fbin": "A20 des nächsten Folge-Bausteins anschließen (Text-iKO). Leer = keine Folge.",
    "auto": "Tagesfreigabe für den automatischen Start, z. B. von einer Zeitschaltuhr nur Mo/Mi/Fr. Ein laufender Lauf wird nicht abgebrochen.",
    "start": "1 startet Lauf 1 sofort (alle Kreise mit Laufzeit).",
    "stop": "1 schließt alle Ventile der ganzen Kette und verwirft Warteschlange und Handanforderungen.",
    "end": "Uhrzeit, zu der Lauf 1 fertig sein soll. Lauf 2 endet 12 h später. Text „06:00“, Zahl ≤ 24 = Stunden (6.5 = 06:30), Zahl > 24 = Sekunden ab Mitternacht.",
    "wf": "Skaliert alle Laufzeiten (100 = wie eingestellt).",
    "rain_on": "So lange muss der Regensensor ununterbrochen 1 melden, bevor die Sperre greift.",
    "rain_after": "So lange bleibt die Sperre nach dem Regen noch aktiv (0 = sofort aus).",
    "t_out": "Ohne Anschluss bleibt der Startwert 20 °C (keine Frostsperre).",
    "frost": "Unter dieser Temperatur Frostsperre für alle Kreise, aus erst wieder ab Grenze + 1 K.",
    "hand_ok": "1 = Handstart einzelner Kreise auch bei Regen- oder Frostsperre (z. B. zum Entleeren).",
    "max_par": "Wie viele Kreise mit „Parallel erlaubt“ in diesem Baustein gleichzeitig laufen dürfen.",
    "pause": "Wartezeit nach dem Schließen eines Ventils. Ist eine Pause eingestellt, gilt die Überlappung nicht und die Pumpe geht in der Pause aus.",
    "overlap": "Das nächste Ventil öffnet so viele Sekunden, bevor das vorige schließt; die Pumpe läuft durch. Empfehlung bei Kaskade: 2–5 s.",
    "wd": "Sicherheitsgrenze: kein Ventil bleibt länger offen. Laufzeiten darüber werden gekappt.",
    "psu_mode": "0 = nur während des Laufs, 1 = dauerhaft an, 2 = Lauf + Nachspeisefenster (E23).",
    "window": "Modus 2: So lange bleibt das Netzteil nach einem Lauf noch an, damit ein autarker Schwimmer (24-V-Ventil am selben Netzteil) nachfüllen kann.",
    "pump_delay": "Erst öffnet das Ventil, dann läuft die Pumpe an.",
    "relief": "Die Pumpe geht so viele Sekunden vor dem letzten Ventil aus (Druck ablassen).",
    "lmin": "Nur bei Schwimmer am KNX: 1 = Zisterne leer. Startet die Nachspeisung; während eines Laufs nach E30 Trockenlaufschutz.",
    "lmax": "Optional: 1 = voll, beendet die Nachspeisung. Wurde nie eine 1 empfangen, beendet die Max-Zeit die Nachspeisung ohne Störung.",
    "refill_run": "1 = nachspeisen nur während eines Laufs.",
    "refill_max": "Watchdog Nachspeisung. Mit Max-Schwimmer → Störung bei Überschreitung.",
    "dry": "Zisterne länger leer → Pumpe aus, Ventile zu, Lauf pausiert; Restzeiten bleiben erhalten.",
    "fb": "Status-KO des Aktorkanals. Angeschlossen: die Laufzeit zählt ab Rückmeldung 1 – auch wenn der Kanal am Taster/Aktor eingeschaltet wurde. Rückmeldung 0 beendet den Kreis. Kommt 10 s nach dem Einschalten keine Rückmeldung, läuft die Zeit trotzdem und es gibt eine Störung. Nicht angeschlossen: Zeit ab Schaltbefehl.",
    "ack": "1 löscht gespeicherte Störungen (Watchdog, Nachspeisung).",
}
INFO_OUT_DE = {
    "psu": "Nur Master. Mit Vor- und Nachlauf.",
    "pump": "Nur Master. Gilt für die ganze Kette.",
    "refill": "Nur Master.",
    "active": "Kreisnummern aller offenen Ventile der Kette, z. B. „3,4,5“.",
    "rest": "Restzeit des laufenden Laufs über die ganze Kette.",
    "dur1": "Geplante Dauer Lauf 1 der ganzen Kette inkl. Netzteil-Vorlauf, mit Wetterfaktor, Pausen, Überlappung, Parallelität. Kreise mit Regensperre sind immer mitgerechnet.",
    "dur2": "Wie A8, nur Kreise mit Zyklus 2.",
    "st1": "Startzeit = Ende − Gesamtlaufzeit; der Master startet zu dieser Zeit selbst (wenn E5 = 1).",
    "st2": "Wie A10 für Lauf 2 (Ende + 12 h).",
    "fault": "Watchdog, Nachspeisung zu lang, Trockenlauf oder Störung in einer Folge.",
    "status": "Max. 14 Zeichen, z. B. „L1 K3 12m“, „Start 05:36“, „Regensperre“.",
    "status_l": "Ausführlicher Status mit letzter Meldung (für Visu, nicht für KNX).",
    "cout": "An E3 des nächsten Folge-Bausteins.",
    "fbout": "Nur Folge: an E4 des Vorgängers.",
}

T = {
    "de": dict(
        title="Bewässerung 5 Kreise (kaskadierbar)",
        intro="Gartenbewässerung mit 5 Kreisen je Baustein. Über die Kaskade lassen sich beliebig viele Bausteine "
              "hintereinanderschalten (Master → Folge 1 → Folge 2 …), z. B. 2 Bausteine für 10 Kreise.",
        sections=[
            ("Funktion", [
                "<b>Laufzeit 0 = Kreis wird übersprungen.</b> Wetterfaktor (E9) skaliert alle Laufzeiten.",
                "<b>Lauf 1</b> = alle Kreise mit Laufzeit. <b>Lauf 2</b> (12 h später) = nur Kreise mit Zyklus 2. Die Laufzeit gilt je Lauf.",
                "<b>Endzeit statt Startzeit:</b> In E8 steht, wann Lauf 1 fertig sein soll. Der Master rechnet die Gesamtlaufzeit der ganzen Kette aus "
                "(A8/A9) und startet selbst zur empfohlenen Startzeit (A10–A13). Ändern sich Laufzeiten oder Wetterfaktor, verschiebt sich der Start automatisch. "
                "Die Zeitschaltuhr im QC braucht es nur noch für die <b>Tage</b>: sie schaltet E5 Automatik.",
                "<b>Reihenfolge:</b> Kreise laufen in Nummernreihenfolge. „Parallel erlaubt“ = 0: Kreis läuft allein (Regner). "
                "= 1: läuft neben anderen Parallel-Kreisen, bis E16 erreicht ist (Tropfschläuche). Parallel nur innerhalb eines Bausteins – Tropfer-Kreise in denselben Baustein legen.",
                "<b>Handstart</b> (Kreis-Eingang „Hand“ = 1): läuft kein Programm, startet ein Hand-Lauf (A5 = 3) mit Netzteil und Pumpe. "
                "Läuft gerade ein Programm, wird der Kreis hinten angehängt bzw. nach dem Programm gestartet. „Hand“ = 0 bricht ab.",
                "<b>Ventil-Rückmeldung (ab 1.1):</b> Die Zeit eines Kreises startet mit der Rückmeldung des Aktors, egal von wo der Kanal eingeschaltet wird. "
                "<b>Extern eingeschaltet ohne Programm:</b> nur dieser Kreis läuft seine Laufzeit (mit Netzteil und Pumpe), danach aus – kein weiterer Kreis. "
                "<b>Extern ausgeschaltet:</b> Kreis beendet; läuft ein Programm, geht es mit dem nächsten Kreis weiter. "
                "<b>Während eines Programms extern eingeschaltet:</b> läuft einzeln mit seiner Zeit daneben, das Programm läuft unverändert weiter (der Kreis entfällt im Programm).",
                "<b>Regensperre</b> je Kreis wählbar. Erst nach E11 Sekunden Dauerregen aktiv, danach noch E12 Minuten. "
                "Ein laufender Kreis mit Regensperre wird abgebrochen, wartende werden übersprungen, Kreise ohne Regensperre laufen weiter. Nicht nachgeholt.",
                "<b>Frostsperre</b> für alle Kreise (Hysterese 1 K). Automatikstart entfällt; Handstart je nach E15.",
                "<b>Watchdog:</b> kein Ventil länger offen als E19.",
                "<b>HS-Neustart:</b> alle Ventile zu, ein unterbrochener Lauf wird nicht fortgesetzt.",
            ]),
            ("Versorgung (nur Master)", [
                "<b>Netzteil 24 V (A1):</b> E20 Modus 0 = nur während des Laufs (Vorlauf E21, Nachlauf E22), 1 = dauerhaft, "
                "2 = zusätzlich E23 Minuten nach jedem Lauf an.",
                "<b>Pumpe (A2):</b> Einschaltverzögerung nach dem Ventil (E24), Druckentlastung vor dem letzten Ventil (E25). "
                "Bei Überlappung läuft sie durch, bei Pause geht sie zwischen den Kreisen aus.",
                "<b>Fall A – Nachbefüllung autark</b> (Schwimmer schaltet ein 24-V-Ventil direkt, der HS weiß davon nichts): E26/E27 frei lassen, "
                "E20 = 2 (oder 1), damit der Schwimmer auch nach dem Lauf Spannung hat. <b>Kein Trockenlaufschutz durch den Baustein</b> – "
                "die Pumpe braucht ihren eigenen (Druckschalter/Trockenlaufschutz an der Pumpe).",
                "<b>Fall B – Schwimmer am KNX:</b> E26 (min, 1 = leer) startet A3 Nachspeisung, E27 (max, 1 = voll) beendet sie, sonst nach E29. "
                "Mit E28 = 1 nur während eines Laufs. Bleibt die Zisterne während eines Laufs länger als E30 leer, pausiert der Lauf "
                "(Pumpe aus, Ventile zu, Restzeiten bleiben) und läuft weiter, sobald wieder Wasser da ist.",
            ]),
            ("Kaskade", [
                "Erster Baustein: E1 = 0 (Master), alle allgemeinen Eingänge hier. Weitere Bausteine: E1 = 1 (Folge), E2 = erste Kreisnummer (6, 11 …).",
                "Verbindung je über ein <b>Text-iKO</b> pro Richtung: <code>A19 Master → E3 Folge 1</code>, <code>A20 Folge 1 → E4 Master</code>, "
                "dann <code>A19 Folge 1 → E3 Folge 2</code>, <code>A20 Folge 2 → E4 Folge 1</code> usw.",
                "Der Master arbeitet seine Kreise ab und gibt dann an Folge 1 weiter. Netzteil, Pumpe, Nachspeisung, Regen/Frost und Start/Stopp "
                "steuert nur der Master; die Folge meldet offene Ventile, Restzeiten, Handanforderungen und Störungen zurück.",
                "Empfehlung: E18 Überlappung 2–5 s, damit die Pumpe bei der Übergabe zwischen den Bausteinen nicht kurz gegen geschlossene Ventile läuft.",
            ]),
            ("iKOs anlegen", [
                "Am schnellsten per CSV-Import im Experten: <i>Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren</i>.",
                "Einstellwerte (Laufzeiten, Zyklus, Endzeit …) als <b>remanente</b> iKOs anlegen, damit sie einen Neustart überstehen.",
            ]),
        ],
        warn="Am HS noch zu prüfen: Uhrzeit-KO (DPT 10) an E8/A10/A12 – falls der HS die Uhrzeit anders übergibt, an E8 einen 14-Byte-Text „06:00“ "
             "verwenden und A11/A13 (Text) anzeigen. Lange Texte (A18–A20) über Text-iKOs.",
        th_in=("Nr.", "Eingang", "Start", "Hinweis"), th_out=("Nr.", "Ausgang", "Hinweis"),
        h_in="Eingänge", h_out="Ausgänge", h_ver="Versionen",
        versions=[("1.1", "Ventil-Rückmeldung je Kreis (E37, E43, E49, E55, E61): Zeit ab Rückmeldung, extern geschaltete Kreise laufen ihre Zeit und werden abgeschaltet, Störung bei fehlender Rückmeldung. Die Kreis-Eingänge sind dadurch neu nummeriert (E32–E61)."),
                  ("1.0", "erste Version: 5 Kreise, Kaskade, Lauf 1/2 mit Endzeit, Regen/Frost, Netzteil/Pumpe/Nachspeisung, Trockenlauf")],
    ),
    "en": dict(
        title="Irrigation 5 circuits (cascadable)",
        intro="Garden irrigation with 5 circuits per block. Any number of blocks can be chained (master → follower 1 → follower 2 …), "
              "e.g. 2 blocks for 10 circuits.",
        sections=[
            ("Function", [
                "<b>Run time 0 = circuit skipped.</b> The weather factor (I9) scales all run times.",
                "<b>Run 1</b> = all circuits with a run time. <b>Run 2</b> (12 h later) = only circuits with cycle 2.",
                "<b>End time instead of start time:</b> I8 sets when run 1 shall be finished. The master calculates the total run time of the whole chain "
                "(O8/O9) and starts by itself at the recommended start time (O10–O13). A time switch is only needed for the <b>days</b> (I5 automatic).",
                "<b>Order:</b> circuits run in number order. Parallel allowed = 0: runs alone (sprinklers); = 1: runs with other parallel circuits up to I16 (drip lines). "
                "Parallel only within one block.",
                "<b>Manual start</b> (circuit input = 1): without a running program a manual run (O5 = 3) starts incl. PSU and pump; during a program the circuit is appended or started afterwards. 0 stops it.",
                "<b>Rain lock</b> per circuit, active after I11 s of continuous rain, held for I12 min. Running circuits with rain lock are stopped, waiting ones skipped.",
                "<b>Valve feedback (from 1.1):</b> a circuit's time starts with the actuator feedback, no matter where the channel was switched on. Switched on externally without a program: only this circuit runs its time, then off. Switched off externally: circuit finished; a running program continues with the next circuit.",
                "<b>Frost lock</b> for all circuits (1 K hysteresis). <b>Watchdog</b> I19. After a HS restart all valves are closed.",
            ]),
            ("Supply (master only)", [
                "<b>24 V PSU (O1):</b> mode 0 = during runs, 1 = permanent, 2 = run + refill window I23.",
                "<b>Pump (O2):</b> on-delay after valve (I24), pressure relief before last valve (I25).",
                "<b>Case A – autonomous refill</b> (float switches a 24 V valve directly): leave I26/I27 free, use PSU mode 2 or 1. No dry-run protection by the block.",
                "<b>Case B – float on KNX:</b> I26 (1 = empty) starts O3, I27 (1 = full) stops it, otherwise I29. Empty longer than I30 during a run → run paused until water is back.",
            ]),
            ("Cascade", [
                "First block I1 = 0 (master), further blocks I1 = 1 (follower), I2 = first circuit number (6, 11 …).",
                "One text iKO per direction: <code>O19 → I3</code> of the next block, <code>O20 → I4</code> of the previous block.",
                "Recommendation: overlap I18 = 2–5 s.",
            ]),
            ("Creating iKOs", [
                "Fastest via Experte CSV import: <i>Communication objects → Extras → Data synchronisation → synchronise/import CSV file</i>. "
                "Create setting iKOs as retentive.",
            ]),
        ],
        warn="To be verified on the HS: time object (DPT 10) at I8/O10/O12 – otherwise use a 14 byte text \"06:00\" at I8 and O11/O13.",
        th_in=("No.", "Input", "Init", "Note"), th_out=("No.", "Output", "Note"),
        h_in="Inputs", h_out="Outputs", h_ver="Versions",
        versions=[("1.1", "valve feedback per circuit; circuit inputs renumbered (I32–I61)"), ("1.0", "first version")],
    ),
}


def page(M, de, lang, version):
    t = T[lang]
    e = html.escape
    bid = M.BLOCK_ID
    h = ['<!doctype html><html lang="%s"><head><meta charset="utf-8"><title>%d %s (v%s)</title><style>%s</style></head><body>'
         % (lang, bid, e(t["title"]), version, CSS)]
    h.append("<h2>%d – %s (v%s)</h2>" % (bid, e(t["title"]), version))
    h.append('<p><span class="b">%s %d</span><span class="b">Version %s</span><span class="b">HSL 3.0</span></p>'
             % ("Baustein-ID" if lang == "de" else "Block ID", bid, version))
    h.append("<p>%s</p>" % t["intro"])
    for title, items in t["sections"]:
        h.append("<h3>%s</h3><ul>%s</ul>" % (e(title), "".join("<li>%s</li>" % i for i in items)))
    h.append('<p class="w">%s</p>' % t["warn"])
    h.append("<h3>%s</h3><table><tr>%s</tr>" % (t["h_in"], "".join("<th>%s</th>" % x for x in t["th_in"])))
    for ident, init, lde, len_ in M.INPUTS:
        label = de(lde) if lang == "de" else len_
        no, rest = label.split(" ", 1)
        base = ident.split("_", 1)[1] if ident.startswith("k") and ident[1].isdigit() else ident
        note = INFO_DE.get(base, "") if lang == "de" else ""
        h.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (no, e(rest), e(str(init)), note))
    h.append("</table><h3>%s</h3><table><tr>%s</tr>" % (t["h_out"], "".join("<th>%s</th>" % x for x in t["th_out"])))
    for ident, init, lde, len_ in M.OUTPUTS:
        label = de(lde) if lang == "de" else len_
        no, rest = label.split(" ", 1)
        note = INFO_OUT_DE.get(ident, "") if lang == "de" else ""
        h.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (no, e(rest), note))
    h.append("</table><h3>%s</h3><ul>%s</ul>" % (t["h_ver"], "".join("<li><b>%s</b> – %s</li>" % v for v in t["versions"])))
    h.append("<p>© BadSmiley0815 · GPL-3.0 · github.com/BadSmiley0815/HS-Logikbausteine</p></body></html>")
    return "\n".join(h)


def write(M, de, outdir, version):
    for lang in ("de", "en"):
        with open(os.path.join(outdir, "%s-log%d.html" % (lang.upper(), M.BLOCK_ID)), "w", encoding="utf-8") as f:
            f.write(page(M, de, lang, version))
