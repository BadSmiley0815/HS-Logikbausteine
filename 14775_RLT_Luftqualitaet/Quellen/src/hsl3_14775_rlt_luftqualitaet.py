# ---------------------------------------------------------------------------
# 14775 RLT Luftqualitaetsregelung  -  Gira HomeServer HSL3
# (c) BadSmiley0815 · GPL-3.0
#
# Luftqualitaetsabhaengiger Betrieb einer RLT-Anlage mit Kreuzstrom-
# Waermetauscher ohne Bypass:
#   1. Zeitprogramm = reine Betriebsfreigabe (AUS: Ventilatoren 0 %,
#      Aussen- und Fortluftklappe zu)
#   2. Klappen (Umluft / Aussenluft / Fortluft) linear (LINEA) zwischen
#      "gute" und "schlechte" Luftqualitaet
#   2.1 Uebertemperatur (Raum > Soll + 1 K, Hysterese) -> 100 % Aussenluft
#   3. Zu- und Abluftventilator linear nach Luftqualitaet (Min/Max)
#   4. Freecooling: bei Soll < Raum und Grenze < Aussen < Raum wird nur die
#      Zuluft ueber eine LINEA-Kennlinie aus dT = Raum - Soll reduziert
#   5. Ampel Luftqualitaet als 8-Bit-Wert (DPT 5.010): 0 gruen, 1 gelb, 2 rot
# ---------------------------------------------------------------------------

BLOCK_ID = 14775
BLOCK_VERSION = "1.6"


def _f(v, default=0.0):
    """Eingangswert -> float (Zahl oder Text mit Komma/Punkt)."""
    try:
        if isinstance(v, bytes):
            v = v.decode("iso-8859-15", errors="ignore")
        if isinstance(v, str):
            v = v.strip().replace(",", ".")
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _clamp(v, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    return max(lo, min(hi, v))


def linea(x, x0, x1, y0, y1):
    """Lineare Kennlinie durch (x0|y0) und (x1|y1), ausserhalb begrenzt.
    Funktioniert auch fallend (x1 < x0), z. B. Luftqualitaet in %."""
    if x1 == x0:
        return y0 if x < x0 else y1
    r = (x - x0) / (x1 - x0)
    r = max(0.0, min(1.0, r))
    return y0 + (y1 - y0) * r


# Eingaenge in Reihenfolge (identifier, Init, Label DE, Label EN)
INPUTS = [
    ("enable", 0, "E1 Freigabe Zeitprogramm (1=EIN)", "I1 Enable time schedule (1=ON)"),
    ("aq", 0, "E2 Luftqualitaet Istwert [ppm]", "I2 Air quality actual [ppm]"),
    ("t_room", 20, "E3 Raumtemperatur [degC]", "I3 Room temperature [degC]"),
    ("t_set", 20, "E4 Raumsolltemperatur [degC]", "I4 Room setpoint [degC]"),
    ("t_out", 10, "E5 Aussentemperatur [degC]", "I5 Outdoor temperature [degC]"),
    ("aq_good", 800, "E6 Grenze gute Luftqualitaet [ppm]", "I6 Limit good air quality [ppm]"),
    ("aq_bad", 1400, "E7 Grenze schlechte Luftqualitaet [ppm]", "I7 Limit bad air quality [ppm]"),
    ("rec_good", 80, "E8 Umluftklappe bei gut [%]", "I8 Recirc damper at good [%]"),
    ("rec_bad", 0, "E9 Umluftklappe bei schlecht [%]", "I9 Recirc damper at bad [%]"),
    ("oa_good", 20, "E10 Aussenluftklappe bei gut [%]", "I10 Outdoor air damper at good [%]"),
    ("oa_bad", 100, "E11 Aussenluftklappe bei schlecht [%]", "I11 Outdoor air damper at bad [%]"),
    ("ex_good", 20, "E12 Fortluftklappe bei gut [%]", "I12 Exhaust damper at good [%]"),
    ("ex_bad", 100, "E13 Fortluftklappe bei schlecht [%]", "I13 Exhaust damper at bad [%]"),
    ("ot_on", 1.0, "E14 Uebertemperatur EIN ab [K]", "I14 Overtemperature ON above [K]"),
    ("ot_off", 0.5, "E15 Uebertemperatur AUS unter [K]", "I15 Overtemperature OFF below [K]"),
    ("fan_min", 30, "E16 Ventilator Mindestdrehzahl [%]", "I16 Fan minimum speed [%]"),
    ("fan_max", 100, "E17 Ventilator Maximaldrehzahl [%]", "I17 Fan maximum speed [%]"),
    ("fc_t_out_min", 12, "E18 Freecooling Aussentemp. mind. [degC]", "I18 Free cooling min. outdoor temp. [degC]"),
    ("fc_dt0", 0, "E19 Freecooling dT Beginn [K]", "I19 Free cooling dT start [K]"),
    ("fc_dt1", 5, "E20 Freecooling dT Ende [K]", "I20 Free cooling dT end [K]"),
    ("fc_corr_max", 100, "E21 Freecooling Korrektur bei dT Ende [%]", "I21 Free cooling correction at dT end [%]"),
    ("fc_supply_min", 0, "E22 Zuluft Untergrenze bei Freecooling [%]", "I22 Supply min. during free cooling [%]"),
    ("rec_off", 0, "E23 Umluftklappe bei Anlage AUS [%]", "I23 Recirc damper when plant OFF [%]"),
    ("amp_yellow", 1000, "E24 Ampel gelb ab [ppm]", "I24 Traffic light yellow from [ppm]"),
    ("amp_red", 1400, "E25 Ampel rot ab [ppm]", "I25 Traffic light red from [ppm]"),
    ("amp_hyst", 50, "E26 Ampel Hysterese [ppm]", "I26 Traffic light hysteresis [ppm]"),
]

OUTPUTS = [
    ("supply", 0, "A1 Zuluftventilator [%]", "O1 Supply fan [%]"),
    ("exhaust", 0, "A2 Abluftventilator [%]", "O2 Exhaust fan [%]"),
    ("rec", 0, "A3 Umluftklappe [%]", "O3 Recirculation damper [%]"),
    ("oa", 0, "A4 Aussenluftklappe [%]", "O4 Outdoor air damper [%]"),
    ("ex", 0, "A5 Fortluftklappe [%]", "O5 Exhaust air damper [%]"),
    ("on", 0, "A6 Anlage EIN / Freigabe Temperaturregelung", "O6 Plant ON / enable temperature control"),
    ("ot", 0, "A7 Uebertemperatur aktiv", "O7 Overtemperature active"),
    ("fc", 0, "A8 Freecooling aktiv", "O8 Free cooling active"),
    ("fc_corr", 0, "A9 Freecooling Zuluftkorrektur [%]", "O9 Free cooling supply correction [%]"),
    ("aq_level", 0, "A10 Luftqualitaet Anteil schlecht [%]", "O10 Air quality share bad [%]"),
    ("status", "", "A11 Status", "O11 Status"),
    ("amp", 0, "A12 Ampel Luftqualitaet (0=gruen 1=gelb 2=rot)", "O12 Air quality traffic light (0=green 1=yellow 2=red)"),
]

AMP_NAMES = ("gruen", "gelb", "rot")


def traffic_light(p, prev):
    """Ampel 0=gruen, 1=gelb, 2=rot mit Hysterese beim Zuruckschalten.
    Richtung folgt der Kennlinie: ist E7 (schlecht) < E6 (gut), gilt
    "kleiner = schlechter" (z. B. Luftqualitaet in %)."""
    d = 1.0 if p["aq_bad"] >= p["aq_good"] else -1.0
    v = p["aq"] * d
    y, r = p["amp_yellow"] * d, p["amp_red"] * d
    if r < y:
        r = y
    h = abs(p["amp_hyst"])

    def level(off):
        if v >= r - off:
            return 2
        if v >= y - off:
            return 1
        return 0

    new = level(0.0)
    if new < prev:
        new = min(prev, level(h))
    return new


def compute(p, st=None):
    """Reine Rechnung. p = dict der Eingangswerte (float).
    st = Zustand {"ot": Uebertemperatur, "amp": Ampel} fuer die Hysteresen.
    Rueckgabe: (dict Ausgaenge, neuer Zustand)."""
    st = dict(st or {})
    amp = traffic_light(p, int(st.get("amp", 0)))
    o, ot = _compute(p, bool(st.get("ot", False)))
    o["amp"] = amp
    o["status"] += " | Ampel " + AMP_NAMES[amp]
    return o, {"ot": ot, "amp": amp}


def _compute(p, ot_state):
    o = {}
    if p["enable"] == 0:
        o.update(supply=0.0, exhaust=0.0, rec=_clamp(p["rec_off"], 0, 100),
                 oa=0.0, ex=0.0, on=0, ot=0, fc=0, fc_corr=0.0)
        o["aq_level"] = round(linea(p["aq"], p["aq_good"], p["aq_bad"], 0.0, 100.0), 1)
        o["status"] = "Anlage AUS"
        return o, False

    dt = p["t_room"] - p["t_set"]

    # 2.1 Uebertemperatur mit Hysterese
    ot_on = p["ot_on"]
    ot_off = min(p["ot_off"], ot_on)
    if dt > ot_on:
        ot_state = True
    elif dt < ot_off:
        ot_state = False

    # Luftqualitaet als Anteil 0 (gut) .. 100 (schlecht)
    level = linea(p["aq"], p["aq_good"], p["aq_bad"], 0.0, 100.0)

    def by_aq(good, bad):
        return _clamp(good + (bad - good) * level / 100.0, 0, 100)

    # 2. Klappen
    if ot_state:
        rec, oa, ex = 0.0, 100.0, 100.0
    else:
        rec = by_aq(p["rec_good"], p["rec_bad"])
        oa = by_aq(p["oa_good"], p["oa_bad"])
        ex = by_aq(p["ex_good"], p["ex_bad"])

    # 3. Ventilatoren
    fmin = _clamp(p["fan_min"], 0, 100)
    fmax = _clamp(p["fan_max"], 0, 100)
    base = _clamp(fmin + (fmax - fmin) * level / 100.0, 0, 100)
    supply = exhaust = base

    # 4. Freecooling: Grenze < Aussen < Raum und Raum > Soll
    fc = p["fc_t_out_min"] < p["t_out"] < p["t_room"] and p["t_room"] > p["t_set"]
    corr = 0.0
    if fc:
        corr = _clamp(linea(dt, p["fc_dt0"], p["fc_dt1"], 0.0, p["fc_corr_max"]), 0, 100)
        supply = base * (1.0 - corr / 100.0)
        floor = min(_clamp(p["fc_supply_min"], 0, 100), base)
        supply = max(supply, floor)

    o.update(supply=round(supply, 1), exhaust=round(exhaust, 1), rec=round(rec, 1),
             oa=round(oa, 1), ex=round(ex, 1), on=1, ot=1 if ot_state else 0,
             fc=1 if fc else 0, fc_corr=round(corr, 1), aq_level=round(level, 1))
    st = "EIN | LQ %.0f %% schlecht | ZU %.0f %% AB %.0f %% | UM %.0f AU %.0f FO %.0f %%" % (
        level, o["supply"], o["exhaust"], o["rec"], o["oa"], o["ex"])
    if ot_state:
        st += " | Uebertemp."
    if fc:
        st += " | Freecooling -%.0f %%" % corr
    o["status"] = st
    return o, ot_state


class LogicModule:

    def __init__(self, hsl3):
        self.fw = hsl3
        self.debug = self.fw.create_debug_section()
        self.p = {}
        self.st = None
        self.last = {}

    def on_init(self, inputs, store):
        self.debug.set("Baustein", "%d v%s" % (BLOCK_ID, BLOCK_VERSION))
        self._read(inputs)
        self._run()

    def on_calc(self, inputs):
        self._read(inputs)
        self._run()

    def on_timer(self, timer):
        pass

    def _read(self, inputs):
        for ident, init, _de, _en in INPUTS:
            self.p[ident] = _f(inputs.value(ident), init)

    def _run(self):
        out, self.st = compute(self.p, self.st)
        for ident, _init, _de, _en in OUTPUTS:
            v = out[ident]
            if ident == "status":
                v = v.encode("iso-8859-15", errors="replace")
            else:
                v = float(v)
            if self.last.get(ident) != v:      # nur bei Aenderung senden
                self.last[ident] = v
                self.fw.set_output(ident, v)
        self.debug.set("Status", out["status"])
        self.debug.set("dT Raum-Soll", "%.2f K" % (self.p["t_room"] - self.p["t_set"]))
