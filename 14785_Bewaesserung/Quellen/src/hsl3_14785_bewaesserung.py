# ---------------------------------------------------------------------------
# 14785 Bewaesserung 5 Kreise (kaskadierbar)  -  Gira HomeServer HSL3
# (c) BadSmiley0815 / Elektro Rausch · GPL-3.0
#
# Gartenbewaesserung mit 5 Kreisen je Baustein, beliebig per Kaskade
# erweiterbar (Master -> Folge 1 -> Folge 2 ...):
#   - Warteschlange, Kreise nacheinander oder parallel (je Kreis waehlbar,
#     max. gleichzeitig je Baustein), Pause oder Ueberlappung beim Wechsel
#   - Laufzeit 0 = Kreis wird uebersprungen; Wetterfaktor in %
#   - Lauf 1 (alle Kreise) und Lauf 2 (+12 h, nur Kreise mit Zyklus 2)
#   - Endzeit statt Startzeit: der Master rechnet die Startzeit der ganzen
#     Kette selbst aus und startet automatisch (Automatik = Tagesfreigabe)
#   - Regensperre je Kreis waehlbar, mit Einschaltverzoegerung/Nachwirkzeit
#   - Frostsperre (alle Kreise), Watchdog je Ventil
#   - Versorgung: 24-V-Netzteil (3 Modi), Pumpe (Verzoegerung, Druck-
#     entlastung), Nachspeisung mit Schwimmer min/max, Trockenlaufschutz
# Code bewusst ASCII; Umlaute nur in den Labels (build.py).
# ---------------------------------------------------------------------------
import json
import math
import time

BLOCK_ID = 14785
BLOCK_VERSION = "1.0"
N = 5                       # Kreise je Baustein
DAY = 86400
HALF = 43200
LAUF_NAMES = {0: "-", 1: "Lauf 1", 2: "Lauf 2", 3: "Hand"}

# (identifier, Init, Label DE (ASCII, build.py setzt Umlaute), Label EN)
GENERAL_INPUTS = [
    ("mode", 0, "E1 Modus (0=Master 1=Folge) [Zahl]", "I1 Mode (0=master 1=follower) [number]"),
    ("first", 1, "E2 Erste Kreisnummer [Zahl]", "I2 First circuit number [number]"),
    ("cin", "", "E3 Kaskade von Vorgaenger (A19) [Text]", "I3 Cascade from predecessor (O19) [text]"),
    ("fbin", "", "E4 Rueckmeldung von Folge (A20) [Text]", "I4 Feedback from follower (O20) [text]"),
    ("auto", 1, "E5 Automatik Ein/Aus [1 Bit]", "I5 Automatic on/off [1 bit]"),
    ("start", 0, "E6 Programm starten (Lauf 1) [1 Bit]", "I6 Start program (run 1) [1 bit]"),
    ("stop", 0, "E7 Alles stoppen [1 Bit]", "I7 Stop all [1 bit]"),
    ("end", "06:00", "E8 Gewuenschtes Ende Lauf 1, Lauf 2 = +12 h [Uhrzeit/Text hh:mm]",
     "I8 Desired end run 1, run 2 = +12 h [time/text hh:mm]"),
    ("wf", 100, "E9 Wetterfaktor [% Zahl]", "I9 Weather factor [% number]"),
    ("rain", 0, "E10 Regensensor [1 Bit]", "I10 Rain sensor [1 bit]"),
    ("rain_on", 300, "E11 Regen Einschaltverzoegerung [s Zahl]", "I11 Rain on-delay [s number]"),
    ("rain_after", 120, "E12 Regen Nachwirkzeit [min Zahl]", "I12 Rain hold time after rain [min number]"),
    ("t_out", 20, "E13 Aussentemperatur [2 Byte Gleitkomma]", "I13 Outdoor temperature [2 byte float]"),
    ("frost", 3, "E14 Frostgrenze [degC Zahl]", "I14 Frost limit [degC number]"),
    ("hand_ok", 1, "E15 Handstart bei Regen/Frost erlaubt [1 Bit]", "I15 Manual start allowed at rain/frost [1 bit]"),
    ("max_par", 1, "E16 Max. Kreise gleichzeitig je Baustein [Zahl]", "I16 Max. circuits at once per block [number]"),
    ("pause", 0, "E17 Pause zwischen Kreisen [s Zahl]", "I17 Pause between circuits [s number]"),
    ("overlap", 0, "E18 Ueberlappung Kreiswechsel [s Zahl]", "I18 Overlap at circuit change [s number]"),
    ("wd", 120, "E19 Max. Laufzeit je Ventil, Watchdog [min Zahl]", "I19 Max. run time per valve, watchdog [min number]"),
    ("psu_mode", 2, "E20 Netzteil-Modus 0=Lauf 1=dauerhaft 2=Lauf+Fenster [Zahl]",
     "I20 PSU mode 0=run 1=permanent 2=run+window [number]"),
    ("psu_pre", 2, "E21 Netzteil Vorlauf [s Zahl]", "I21 PSU lead time [s number]"),
    ("psu_post", 5, "E22 Netzteil Nachlauf [s Zahl]", "I22 PSU run-on [s number]"),
    ("window", 60, "E23 Nachspeisefenster nach Lauf [min Zahl]", "I23 Refill window after run [min number]"),
    ("pump_delay", 3, "E24 Pumpe Einschaltverzoegerung nach Ventil [s Zahl]", "I24 Pump on-delay after valve [s number]"),
    ("relief", 3, "E25 Pumpe Druckentlastung [s Zahl]", "I25 Pump pressure relief [s number]"),
    ("lmin", 0, "E26 Fuellstand min, 1=leer [1 Bit]", "I26 Level min, 1=empty [1 bit]"),
    ("lmax", 0, "E27 Fuellstand max, 1=voll [1 Bit]", "I27 Level max, 1=full [1 bit]"),
    ("refill_run", 0, "E28 Nachspeisung nur waehrend Lauf [1 Bit]", "I28 Refill only during run [1 bit]"),
    ("refill_max", 60, "E29 Nachspeisung Max-Zeit [min Zahl]", "I29 Refill max. time [min number]"),
    ("dry", 30, "E30 Trockenlauf Verzoegerung [s Zahl]", "I30 Dry-run delay [s number]"),
    ("ack", 0, "E31 Stoerung quittieren [1 Bit]", "I31 Acknowledge fault [1 bit]"),
]

CIRCUIT_INPUTS = [   # je Kreis n
    ("t", 0, "Laufzeit, 0=ueberspringen [min Zahl]", "run time, 0=skip [min number]"),
    ("cyc", 1, "Zyklus 1=1x 2=2x taeglich [Zahl]", "cycle 1=1x 2=2x daily [number]"),
    ("rain", 1, "Regensperre beachten [1 Bit]", "observe rain lock [1 bit]"),
    ("par", 0, "Parallel erlaubt [1 Bit]", "parallel allowed [1 bit]"),
    ("hand", 0, "Hand Start/Stopp [1 Bit]", "manual start/stop [1 bit]"),
]

GENERAL_OUTPUTS = [
    ("psu", 0, "A1 Versorgung 24 V [1 Bit]", "O1 Supply 24 V [1 bit]"),
    ("pump", 0, "A2 Pumpe [1 Bit]", "O2 Pump [1 bit]"),
    ("refill", 0, "A3 Nachspeisung [1 Bit]", "O3 Refill [1 bit]"),
    ("running", 0, "A4 Programm laeuft [1 Bit]", "O4 Program running [1 bit]"),
    ("run_no", 0, "A5 Aktiver Lauf 0=keiner 1 2 3=Hand [Zahl]", "O5 Active run 0=none 1 2 3=manual [number]"),
    ("active", "", "A6 Aktive Kreise [14 Byte Text]", "O6 Active circuits [14 byte text]"),
    ("rest", 0, "A7 Restzeit gesamt [min Zahl]", "O7 Remaining time total [min number]"),
    ("dur1", 0, "A8 Gesamtlaufzeit Lauf 1 [min Zahl]", "O8 Total run time run 1 [min number]"),
    ("dur2", 0, "A9 Gesamtlaufzeit Lauf 2 [min Zahl]", "O9 Total run time run 2 [min number]"),
    ("st1", 0, "A10 Startzeit Lauf 1 [Uhrzeit, s ab 0 Uhr]", "O10 Start time run 1 [time, s from midnight]"),
    ("st1t", "", "A11 Startzeit Lauf 1 [14 Byte Text]", "O11 Start time run 1 [14 byte text]"),
    ("st2", 0, "A12 Startzeit Lauf 2 [Uhrzeit, s ab 0 Uhr]", "O12 Start time run 2 [time, s from midnight]"),
    ("st2t", "", "A13 Startzeit Lauf 2 [14 Byte Text]", "O13 Start time run 2 [14 byte text]"),
    ("rainlock", 0, "A14 Regensperre aktiv [1 Bit]", "O14 Rain lock active [1 bit]"),
    ("frostlock", 0, "A15 Frostsperre aktiv [1 Bit]", "O15 Frost lock active [1 bit]"),
    ("fault", 0, "A16 Stoerung [1 Bit]", "O16 Fault [1 bit]"),
    ("status", "", "A17 Status kurz [14 Byte Text]", "O17 Status short [14 byte text]"),
    ("status_l", "", "A18 Status ausfuehrlich [Text]", "O18 Status detailed [text]"),
    ("cout", "", "A19 Kaskade an Folge (E3) [Text]", "O19 Cascade to follower (I3) [text]"),
    ("fbout", "", "A20 Rueckmeldung an Vorgaenger (E4) [Text]", "O20 Feedback to predecessor (I4) [text]"),
]

CIRCUIT_OUTPUTS = [
    ("valve", 0, "Ventil [1 Bit]", "valve [1 bit]"),
    ("rest", 0, "Restzeit [min Zahl]", "remaining time [min number]"),
]


def _build_lists():
    ins = list(GENERAL_INPUTS)
    e = len(ins)
    for n in range(1, N + 1):
        for ident, init, lde, len_ in CIRCUIT_INPUTS:
            e += 1
            ins.append(("k%d_%s" % (n, ident), init, "E%d Kreis %d %s" % (e, n, lde),
                        "I%d Circuit %d %s" % (e, n, len_)))
    outs = list(GENERAL_OUTPUTS)
    a = len(outs)
    for n in range(1, N + 1):
        for ident, init, lde, len_ in CIRCUIT_OUTPUTS:
            a += 1
            outs.append(("k%d_%s" % (n, ident), init, "A%d Kreis %d %s" % (a, n, lde),
                         "O%d Circuit %d %s" % (a, n, len_)))
    return ins, outs


INPUTS, OUTPUTS = _build_lists()
TEXT_OUTPUTS = ("active", "st1t", "st2t", "status", "status_l", "cout", "fbout")


# ------------------------------------------------------------------ Helfer
def _text(v):
    if v is None:
        return ""
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except UnicodeDecodeError:
            return v.decode("iso-8859-15", errors="replace")
    return str(v)


def _f(v, default=0.0):
    try:
        if isinstance(v, bytes):
            v = v.decode("iso-8859-15", errors="ignore")
        if isinstance(v, str):
            v = v.strip().replace(",", ".")
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _bit(v):
    return 1 if _f(v, 0) >= 0.5 else 0


def parse_tod(v, default=6 * 3600):
    """Uhrzeit -> Sekunden ab Mitternacht.
    Text "06:00" / "6:30:15"; Zahl <= 24 = Stunden (6.5 = 06:30);
    Zahl > 24 = Sekunden ab Mitternacht."""
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        s = _text(v).strip()
        if not s:
            return default
        if ":" in s:
            try:
                parts = [int(float(p)) for p in s.split(":")]
                while len(parts) < 3:
                    parts.append(0)
                return (parts[0] * 3600 + parts[1] * 60 + parts[2]) % DAY
            except ValueError:
                return default
        try:
            x = float(s.replace(",", "."))
        except ValueError:
            return default
    if x < 0:
        return default
    if x <= 24:
        return int(round(x * 3600)) % DAY
    return int(x) % DAY


def fmt_tod(sec):
    sec = int(sec) % DAY
    return "%02d:%02d" % (sec // 3600, (sec % 3600) // 60)


def _ceil_min(sec):
    return int(math.ceil(max(0.0, sec) / 60.0 - 1e-9))


# ----------------------------------------------------- Ablaufregeln (rein)
def can_start(par, running, now, last_close, P):
    """Darf ein Kreis (par = parallel erlaubt) jetzt oeffnen?
    running: Liste von (end, par). Gleiche Regel fuer Lauf und Planung."""
    pause = P["pause"]
    if pause > 0 and last_close is not None and now < last_close + pause - 1e-9:
        return False
    ov = P["ov"] if pause <= 0 else 0.0
    busy = [p for (end, p) in running if end - now > ov + 1e-9]
    if not par:
        return not busy
    if any(not p for p in busy):
        return False
    return len(busy) < max(1, int(P["mp"]))


def simulate(queue, running=(), P=None, last_close=None):
    """Dauer (s) bis alle Kreise zu sind. queue: Liste (dauer, par),
    running: Liste (restzeit, par); Zeit 0 = jetzt. last_close relativ."""
    t = 0.0
    q = [(float(d), bool(p)) for d, p in queue if d > 0]
    run = [(float(e), bool(p)) for e, p in running]
    end_all = max([e for e, _ in run] + [0.0])
    pause = P["pause"]
    ov = P["ov"] if pause <= 0 else 0.0
    for _guard in range(10000):
        closed = [e for e, _ in run if e <= t + 1e-9]
        if closed:
            last_close = max(closed)
            run = [(e, p) for e, p in run if e > t + 1e-9]
        while q and can_start(q[0][1], run, t, last_close, P):
            d, p = q.pop(0)
            run.append((t + d, p))
            end_all = max(end_all, t + d)
        if not q and not run:
            break
        cand = [e for e, _ in run]
        cand += [e - ov for e, _ in run if e - ov > t + 1e-9]
        if pause > 0 and last_close is not None:
            cand.append(last_close + pause)
        cand = [c for c in cand if c > t + 1e-9]
        if not cand:
            break
        t = min(cand)
    return end_all


# ------------------------------------------------------------------ Engine
class Engine(object):
    """Ein Baustein (Master oder Folge). Zeit wird von aussen uebergeben."""

    def __init__(self):
        self.p = {i[0]: i[1] for i in INPUTS}
        self.prev_bits = {}
        self.events = []
        self.queue = []          # [{"k","d","par","rain","hand"}]
        self.running = {}        # k -> {"end","start","par","rain","hand"}
        self.last_close = None
        self.hand_pending = []   # Kreisindizes 0..N-1
        self.phase = "idle"      # idle | prep | own | down
        self.lauf = 0
        self.run_id = 0
        self.tok_sent = 0        # an Folge uebergebener Lauf (Kaskade)
        self.cur_tok = 0         # Folge: gerade bearbeiteter Lauf
        self.last_tok = None
        self.done_id = 0
        self.stop_cnt = 0
        self.last_stop_seen = None
        self.fb = {}
        self.cin = {}
        # Master-Zustaende
        self.rainlock = False
        self.rain_since = None
        self.rain_until = None
        self.frostlock = False
        self.psu = 0
        self.psu_since = None
        self.psu_off_at = None
        self.pump = 0
        self.pump_want_since = None
        self.refill = 0
        self.refill_since = None
        self.refill_block = False
        self.max_used = False
        self.dry_since = None
        self.hold = False
        self.faults = []         # quittierpflichtig
        self.prev_sod = None
        self.note = ""           # letzte Ereignismeldung
        self.note_t = 0
        self.out = {}

    # ---------------------------------------------------------- Eingaenge
    def set_inputs(self, values, changed):
        for k, v in values.items():
            self.p[k] = v
        for k in changed:
            self.events.append((k, values.get(k, self.p.get(k))))

    def is_master(self):
        return int(_f(self.p["mode"], 0)) != 1

    def first(self):
        return int(_f(self.p["first"], 1)) or 1

    def cn(self, k):
        return "K%d" % (self.first() + k)

    def params(self):
        """Ablaufparameter: Master aus eigenen Eingaengen, Folge aus Kaskade."""
        if self.is_master():
            return {"wf": max(0.0, _f(self.p["wf"], 100)),
                    "pause": max(0.0, _f(self.p["pause"], 0)),
                    "ov": max(0.0, _f(self.p["overlap"], 0)),
                    "wd": max(0.0, _f(self.p["wd"], 120)),
                    "mp": max(1, int(_f(self.p["max_par"], 1))),
                    "hok": _bit(self.p["hand_ok"])}
        c = self.cin
        return {"wf": float(c.get("wf", 100)), "pause": float(c.get("pz", 0)),
                "ov": float(c.get("ov", 0)), "wd": float(c.get("wd", 120)),
                "mp": int(c.get("mp", 1)), "hok": int(c.get("hok", 1))}

    def circuit(self, k):
        n = k + 1
        return {"t": max(0.0, _f(self.p["k%d_t" % n], 0)),
                "cyc": int(_f(self.p["k%d_cyc" % n], 1)),
                "rain": _bit(self.p["k%d_rain" % n]),
                "par": _bit(self.p["k%d_par" % n])}

    def dur(self, k, P):
        c = self.circuit(k)
        d = c["t"] * 60.0 * P["wf"] / 100.0
        if P["wd"] > 0:
            d = min(d, P["wd"] * 60.0)
        return round(d)

    # ------------------------------------------------------- Planung
    def own_items(self, lauf, P):
        items = []
        for k in range(N):
            c = self.circuit(k)
            if c["t"] <= 0:
                continue
            if lauf == 2 and c["cyc"] != 2:
                continue
            if lauf == 3 and k not in self.hand_pending:
                continue
            items.append((self.dur(k, P), bool(c["par"])))
        return items

    def has_down(self):
        return bool(self.fb.get("ok"))

    def chain_plan(self, lauf, P):
        """Dauer dieses Bausteins + Folge (s), Folge wie ein exklusiver Kreis."""
        items = self.own_items(lauf, P)
        dd = float(self.fb.get("d%d" % lauf, 0)) if self.has_down() else 0.0
        if dd > 0:
            items.append((dd, False))
        return simulate(items, (), P)

    def remaining(self, now, P):
        q = [(it["d"], it["par"]) for it in self.queue]
        run = [(r["end"] - now, r["par"]) for r in self.running.values()]
        lc = (self.last_close - now) if self.last_close is not None else None
        if self.has_down() and self.phase in ("prep", "own"):
            dd = float(self.fb.get("d%d" % self.lauf, 0))
            if dd > 0:
                q.append((dd, False))
            return simulate(q, run, P, lc)
        own = simulate(q, run, P, lc) if (q or run) else 0.0
        if self.has_down() and self.phase == "down":
            own += float(self.fb.get("rest", 0))
        return own

    # ------------------------------------------------------- Ablauf
    def _open(self, it, now):
        self.running[it["k"]] = {"end": now + it["d"], "start": now, "par": it["par"],
                                 "rain": it["rain"], "hand": it["hand"]}

    def _close(self, k, now):
        if k in self.running:
            del self.running[k]
            self.last_close = now

    def _item(self, k, hand, P):
        c = self.circuit(k)
        return {"k": k, "d": self.dur(k, P), "par": bool(c["par"]), "rain": bool(c["rain"]),
                "hand": hand}

    def _locked(self, it, rain, frost, P):
        if it["hand"] and P["hok"]:
            return False
        return bool(frost or (rain and it["rain"]))

    def build_queue(self, lauf, rain, frost, P):
        self.queue = []
        skipped = []
        if lauf == 3:
            ks = sorted(self.hand_pending)
            self.hand_pending = []
            for k in ks:
                it = self._item(k, True, P)
                if it["d"] <= 0:
                    continue
                if self._locked(it, rain, frost, P):
                    skipped.append(self.cn(k))
                    continue
                self.queue.append(it)
        else:
            for k in range(N):
                c = self.circuit(k)
                if c["t"] <= 0 or (lauf == 2 and c["cyc"] != 2):
                    continue
                it = self._item(k, False, P)
                if self._locked(it, rain, frost, P):
                    skipped.append(self.cn(k))
                    continue
                self.queue.append(it)
        return skipped

    def abort_all(self, now):
        for k in list(self.running):
            self._close(k, now)
        self.queue = []

    def apply_locks(self, now, rain, frost, P):
        for k in list(self.running):
            if self._locked(self.running[k], rain, frost, P):
                self._close(k, now)
                self._note(now, "%s abgebrochen (%s)" % (self.cn(k), "Frost" if frost else "Regen"))
        before = len(self.queue)
        self.queue = [it for it in self.queue if not self._locked(it, rain, frost, P)]
        if len(self.queue) != before:
            self._note(now, "%d Kreis(e) uebersprungen (%s)" % (before - len(self.queue),
                                                               "Frost" if frost else "Regen"))

    def do_hold(self, now):
        """Trockenlauf: offene Kreise schliessen, Restzeit vorne einreihen."""
        back = []
        for k in sorted(self.running):
            r = self.running[k]
            rest = round(r["end"] - now)
            if rest > 0:
                back.append({"k": k, "d": rest, "par": r["par"], "rain": r["rain"], "hand": r["hand"]})
            self._close(k, now)
        self.queue = back + self.queue

    def schedule(self, now, P):
        """Ventile schliessen/oeffnen. Rueckgabe True, wenn eigener Teil fertig."""
        wd = P["wd"] * 60.0
        for k in list(self.running):
            r = self.running[k]
            if now >= r["end"] - 1e-9:
                self._close(k, now)
            elif wd > 0 and now - r["start"] > wd + 1:
                self._close(k, now)
                self._fault(now, "Watchdog %s" % self.cn(k))
        run = [(r["end"], r["par"]) for r in self.running.values()]
        while self.queue and can_start(self.queue[0]["par"], run, now, self.last_close, P):
            it = self.queue.pop(0)
            if it["d"] <= 0:
                continue
            self._open(it, now)
            run.append((now + it["d"], it["par"]))
        return not self.queue and can_start(False, run, now, self.last_close, P)

    def hand_event(self, k, on, now, rain, frost, P):
        c = self.circuit(k)
        if not on:
            if k in self.running:
                self._close(k, now)
                self._note(now, "%s Hand-Stopp" % self.cn(k))
            self.queue = [it for it in self.queue if it["k"] != k]
            if k in self.hand_pending:
                self.hand_pending.remove(k)
            return
        if c["t"] <= 0:
            self._note(now, "%s keine Laufzeit" % self.cn(k))
            return
        if k in self.running or any(it["k"] == k for it in self.queue) or k in self.hand_pending:
            return
        it = self._item(k, True, P)
        if self._locked(it, rain, frost, P):
            self._note(now, "%s gesperrt (%s)" % (self.cn(k), "Frost" if frost else "Regen"))
            return
        if self.phase in ("prep", "own"):
            self.queue.append(it)
        else:
            self.hand_pending.append(k)
        self._note(now, "%s Handstart" % self.cn(k))

    # ------------------------------------------------------- Meldungen
    def _note(self, now, text):
        self.note = text
        self.note_t = now

    def _fault(self, now, text):
        if text not in self.faults:
            self.faults.append(text)
        self._note(now, "Stoerung: " + text)

    # ------------------------------------------------------- Takt
    def tick(self, now):
        events, self.events = self.events, []
        master = self.is_master()
        if master:
            return self._tick_master(now, events)
        return self._tick_follower(now, events)

    def _read_json(self, key):
        s = _text(self.p.get(key, "")).strip()
        if not s:
            return {}
        try:
            d = json.loads(s)
            return d if isinstance(d, dict) else {}
        except ValueError:
            return {}

    def _common_events(self, events, now, rain, frost, P):
        stop = False
        for key, val in events:
            if key == "stop" and _bit(val):
                stop = True
            elif key.startswith("k") and key.endswith("_hand"):
                k = int(key[1:key.index("_")]) - 1
                if 0 <= k < N:
                    self.hand_event(k, _bit(val), now, rain, frost, P)
        return stop

    # ................................................................ Master
    def _tick_master(self, now, events):
        self.fb = self._read_json("fbin")
        P = self.params()
        p = self.p
        # Regen mit Einschaltverzoegerung / Nachwirkzeit
        raw = _bit(p["rain"])
        if raw:
            if self.rain_since is None:
                self.rain_since = now
            if self.rainlock:
                self.rain_until = None
            elif now - self.rain_since >= max(0.0, _f(p["rain_on"], 300)):
                self.rainlock = True
                self.rain_until = None
                self._note(now, "Regen erkannt")
        else:
            self.rain_since = None
            if self.rainlock:
                if self.rain_until is None:
                    self.rain_until = now + max(0.0, _f(p["rain_after"], 120)) * 60.0
                if now >= self.rain_until:
                    self.rainlock = False
                    self.rain_until = None
        # Frost mit 1 K Hysterese
        t_out, flim = _f(p["t_out"], 20), _f(p["frost"], 3)
        if t_out < flim:
            self.frostlock = True
        elif t_out >= flim + 1.0:
            self.frostlock = False
        rain, frost = self.rainlock, self.frostlock

        # Ereignisse
        start_req = 0
        for key, val in events:
            if key == "start" and _bit(val):
                start_req = 1
            elif key == "ack" and _bit(val):
                self.faults = []
                self.refill_block = False
                self._note(now, "Stoerung quittiert")
        stop = self._common_events(events, now, rain, frost, P)
        if stop:
            self.abort_all(now)
            self.hand_pending = []
            self.stop_cnt += 1
            if self.phase != "idle":
                self._end_session(now)
            self._note(now, "Gestoppt")

        # Planung
        mode = int(_f(p["psu_mode"], 2))
        pre = 0.0 if mode == 1 else max(0.0, _f(p["psu_pre"], 2))
        d1 = self.chain_plan(1, P)
        d2 = self.chain_plan(2, P)
        end1 = parse_tod(p["end"])
        st1 = (end1 - int(round(d1 + pre))) % DAY if d1 > 0 else None
        st2 = (end1 + HALF - int(round(d2 + pre))) % DAY if d2 > 0 else None

        # Automatikstart
        lt = time.localtime(now)
        sod = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
        auto = _bit(p["auto"])
        if self.prev_sod is not None:
            for lauf, st in ((1, st1), (2, st2)):
                if st is None or not self._crossed(self.prev_sod, sod, st):
                    continue
                if not auto:
                    continue
                if self.phase != "idle":
                    self._note(now, "%s uebersprungen (laeuft noch)" % LAUF_NAMES[lauf])
                elif frost:
                    self._note(now, "%s uebersprungen (Frost)" % LAUF_NAMES[lauf])
                else:
                    self._start_session(lauf, now, rain, frost, P)
        self.prev_sod = sod
        if start_req:
            if self.phase != "idle":
                self._note(now, "Start ignoriert (laeuft schon)")
            elif frost and not P["hok"]:
                self._note(now, "Start gesperrt (Frost)")
            else:
                self._start_session(1, now, rain, frost, P)
        # Handanforderung ohne laufendes Programm -> Hand-Lauf
        if self.phase == "idle" and (self.hand_pending or self.fb.get("req")):
            self._start_session(3, now, rain, frost, P)

        # Trockenlauf (nur wenn Schwimmer min belegt)
        lmin, lmax = _bit(p["lmin"]), _bit(p["lmax"])
        if lmax:
            self.max_used = True
        session = self.phase != "idle"
        if session and lmin:
            if self.dry_since is None:
                self.dry_since = now
            if not self.hold and now - self.dry_since >= max(0.0, _f(p["dry"], 30)):
                self.hold = True
                self.do_hold(now)
                self._note(now, "Trockenlauf - Pause bis Wasser da")
        else:
            self.dry_since = None
            if self.hold:
                self.hold = False
                self._note(now, "Wasser wieder da - weiter")

        # Nachspeisung
        self._refill_logic(now, lmin, lmax, session)

        # Netzteil
        ready = self._psu(now, session or self.refill, mode, pre)

        # Ablauf
        if self.phase != "idle":
            if not self.hold:
                self.apply_locks(now, rain, frost, P)
            if self.phase == "prep" and ready:
                self.phase = "own"
            if self.phase == "own" and not self.hold:
                if self.schedule(now, P):
                    if self.has_down():
                        self.phase = "down"
                        self.tok_sent = self.run_id
                    else:
                        self._end_session(now)
            elif self.phase == "own" and self.hold:
                pass
            if self.phase == "down":
                self.schedule(now, P)      # Ueberlappung: eigene Ventile auslaufen lassen
                if not self.running and (not self.has_down() or
                                         int(self.fb.get("done", 0)) == self.run_id):
                    self._end_session(now)

        self._psu(now, self.phase != "idle" or self.refill, mode, pre)   # Nachlauf ab Ende

        # Pumpe
        fb_open = bool(self.fb.get("open"))
        rem = max([r["end"] - now for r in self.running.values()] + [float(self.fb.get("rem", 0)) if fb_open else 0.0])
        chain_open = bool(self.running) or fb_open
        pending = self.phase in ("own", "down") and (
            bool(self.queue) or (self.has_down() and int(self.fb.get("done", 0)) != self.run_id))
        relief = max(0.0, _f(p["relief"], 3))
        bridge = pending and P["pause"] <= 0
        if self.hold or self.phase == "idle":
            want = False
        elif chain_open:
            want = rem > relief or bridge
        else:
            want = bool(self.pump) and bridge
        if want:
            if not self.pump:
                if self.pump_want_since is None:
                    self.pump_want_since = now
                if now - self.pump_want_since >= max(0.0, _f(p["pump_delay"], 3)) - 1e-9:
                    self.pump = 1
        else:
            self.pump = 0
            self.pump_want_since = None

        # Kaskade nach unten
        cout = {"id": self.run_id if self.phase != "idle" else 0, "l": self.lauf,
                "tok": self.tok_sent if self.phase != "idle" else 0,
                "rdy": 1 if ready else 0, "hold": 1 if self.hold else 0, "stop": self.stop_cnt,
                "rain": 1 if rain else 0, "frost": 1 if frost else 0, "hok": P["hok"],
                "wf": P["wf"], "pz": P["pause"], "ov": P["ov"], "wd": P["wd"], "mp": P["mp"]}
        rest = self.remaining(now, P) if self.phase != "idle" else 0.0
        if self.phase == "prep":
            rest += max(0.0, pre - (now - (self.psu_since or now)))
        o = self._outputs(now, P, rest)
        o.update(psu=self.psu, pump=self.pump, refill=self.refill,
                 dur1=_ceil_min(d1 + pre) if d1 > 0 else 0, dur2=_ceil_min(d2 + pre) if d2 > 0 else 0,
                 st1=st1 if st1 is not None else 0, st1t=fmt_tod(st1) if st1 is not None else "--:--",
                 st2=st2 if st2 is not None else 0, st2t=fmt_tod(st2) if st2 is not None else "--:--",
                 rainlock=1 if rain else 0, frostlock=1 if frost else 0,
                 fault=1 if (self.faults or self.hold or self.fb.get("flt")) else 0,
                 cout=json.dumps(cout, separators=(",", ":"), sort_keys=True), fbout="")
        o["status"], o["status_l"] = self._status_master(now, P, st1, st2, rest, raw, auto, mode)
        self.out = o
        return o

    _had_session = False

    def _psu(self, now, need, mode, pre):
        p = self.p
        if mode == 1:
            if not self.psu:
                self.psu, self.psu_since = 1, now - 3600
            self.psu_off_at = None
        elif need:
            if not self.psu:
                self.psu, self.psu_since = 1, now
            self.psu_off_at = None
        elif self.psu:
            if self.psu_off_at is None:
                post = max(0.0, _f(p["psu_post"], 5))
                if mode == 2 and self._had_session:
                    post += max(0.0, _f(p["window"], 60)) * 60.0
                self.psu_off_at = now + post
            if now >= self.psu_off_at:
                self.psu, self.psu_off_at = 0, None
                self._had_session = False
        return bool(self.psu) and self.psu_since is not None and now - self.psu_since >= pre - 1e-9

    @staticmethod
    def _crossed(prev, cur, t):
        if cur >= prev:
            return prev < t <= cur
        return t > prev or t <= cur      # Mitternacht

    def _start_session(self, lauf, now, rain, frost, P):
        self.run_id = (self.run_id % 999999) + 1
        self.lauf = lauf
        self.tok_sent = 0
        skipped = self.build_queue(lauf, rain, frost, P)
        self.phase = "prep"
        self.last_close = None
        self._had_session = True
        txt = "%s gestartet" % LAUF_NAMES[lauf]
        if skipped:
            txt += ", gesperrt: " + ",".join(skipped)
        self._note(now, txt)

    def _end_session(self, now):
        if self.phase != "idle":
            self._note(now, "%s beendet" % LAUF_NAMES.get(self.lauf, "Lauf"))
        self.phase = "idle"
        self.lauf = 0
        self.tok_sent = 0
        self.queue = []

    def _refill_logic(self, now, lmin, lmax, session):
        p = self.p
        only_run = _bit(p["refill_run"])
        rmax = max(0.0, _f(p["refill_max"], 60)) * 60.0
        if not lmin and not self.max_used:
            self.refill_block = False
        if self.refill:
            stop = False
            if lmax:
                stop = True
            elif only_run and not session:
                stop = True
            elif rmax > 0 and now - self.refill_since >= rmax:
                stop = True
                self.refill_block = True
                if self.max_used:
                    self._fault(now, "Nachspeisung Zeit")
            if stop:
                self.refill, self.refill_since = 0, None
        elif lmin and not lmax and not self.refill_block and (session or not only_run):
            self.refill, self.refill_since = 1, now

    # ................................................................ Folge
    def _tick_follower(self, now, events):
        self.fb = self._read_json("fbin")
        self.cin = c = self._read_json("cin")
        P = self.params()
        rain, frost = bool(c.get("rain")), bool(c.get("frost"))
        stop_cnt = int(c.get("stop", 0))
        stop = self._common_events(events, now, rain, frost, P)
        if self.last_stop_seen is None:
            self.last_stop_seen = stop_cnt
        if stop or stop_cnt != self.last_stop_seen:
            self.last_stop_seen = stop_cnt
            self.abort_all(now)
            self.hand_pending = []
            self.phase, self.lauf = "idle", 0
            self._note(now, "Gestoppt")
        tok, rid = int(c.get("tok", 0)), int(c.get("id", 0))
        if self.last_tok is None:
            self.last_tok = tok          # nach Neustart keinen alten Auftrag ausfuehren
        if rid == 0 and self.phase != "idle":
            self.abort_all(now)
            self.phase, self.lauf = "idle", 0
        if tok and tok != self.last_tok:
            self.last_tok = tok
            self.cur_tok = tok
            self.run_id = tok
            self.lauf = int(c.get("l", 1))
            self.tok_sent = 0
            self.last_close = None
            skipped = self.build_queue(self.lauf, rain, frost, P)
            self.phase = "own"
            self._note(now, "%s uebernommen%s" % (LAUF_NAMES.get(self.lauf, "Lauf"),
                                                  (", gesperrt: " + ",".join(skipped)) if skipped else ""))
        elif not tok:
            self.last_tok = 0
        hold = bool(c.get("hold"))
        if self.phase != "idle":
            if hold:
                if self.running:
                    self.do_hold(now)
            else:
                self.apply_locks(now, rain, frost, P)
                if self.phase == "own":
                    if self.schedule(now, P):
                        if self.has_down():
                            self.phase = "down"
                            self.tok_sent = self.run_id
                        else:
                            self.phase = "done"
                if self.phase in ("down", "done"):
                    self.schedule(now, P)
                    if not self.running and (self.phase == "done" or not self.has_down() or
                                             int(self.fb.get("done", 0)) == self.run_id):
                        self.done_id = self.run_id
                        self.phase = "fin"
        P2 = P
        d = {"ok": 1}
        for lauf in (1, 2, 3):
            d["d%d" % lauf] = round(self.chain_plan(lauf, P2))
        fb_open = bool(self.fb.get("open"))
        d["open"] = 1 if (self.running or fb_open) else 0
        rems = [r["end"] - now for r in self.running.values()]
        if fb_open:
            rems.append(float(self.fb.get("rem", 0)))
        d["rem"] = round(max(rems + [0.0]), 1)
        d["done"] = self.done_id
        d["req"] = 1 if (self.hand_pending or self.fb.get("req")) else 0
        d["act"] = [self.first() + k for k in sorted(self.running)] + list(self.fb.get("act", []))
        active = self.phase in ("own", "down", "done")
        rest = self.remaining(now, P) if active else 0.0
        if active and self.phase == "own" and not self.running and not self.queue and self.has_down():
            rest = float(self.fb.get("rest", 0))
        d["rest"] = round(rest)
        d["flt"] = "; ".join(self.faults + ([self.fb["flt"]] if self.fb.get("flt") else []))
        o = self._outputs(now, P, rest)
        o.update(psu=0, pump=0, refill=0, dur1=_ceil_min(d["d1"]), dur2=_ceil_min(d["d2"]),
                 st1=0, st1t="", st2=0, st2t="", rainlock=1 if rain else 0, frostlock=1 if frost else 0,
                 fault=1 if d["flt"] else 0,
                 fbout=json.dumps(d, separators=(",", ":"), sort_keys=True))
        cout = dict(c)
        cout["tok"] = self.tok_sent if self.phase in ("down", "done", "fin") and self.tok_sent else 0
        o["cout"] = json.dumps(cout, separators=(",", ":"), sort_keys=True) if c else ""
        o["status"], o["status_l"] = self._status_follower(now, P, rest, hold, rain, frost, bool(c))
        # nach Abschluss: Ruhe bis zum naechsten Auftrag
        if self.phase == "fin" and not tok:
            self.phase, self.lauf = "idle", 0
        self.out = o
        return o

    # ------------------------------------------------------- Ausgaenge
    def _active_list(self):
        own = [self.first() + k for k in sorted(self.running)]
        return own + [int(x) for x in self.fb.get("act", []) if str(x).isdigit()]

    def _outputs(self, now, P, rest):
        o = {}
        for k in range(N):
            n = k + 1
            r = self.running.get(k)
            o["k%d_valve" % n] = 1 if r else 0
            o["k%d_rest" % n] = _ceil_min(r["end"] - now) if r else 0
        act = self._active_list()
        o["active"] = ",".join(str(a) for a in act)[:14]
        running = self.phase in ("prep", "own", "down", "done")
        o["running"] = 1 if running else 0
        o["run_no"] = self.lauf if running else 0
        o["rest"] = _ceil_min(rest) if running else 0
        return o

    def _recent_note(self, now):
        return self.note if self.note and now - self.note_t < 600 else ""

    def _run_text(self, now, rest):
        act = self._active_list()
        if act:
            parts = []
            for k in sorted(self.running):
                parts.append("%s (%d min)" % (self.cn(k), _ceil_min(self.running[k]["end"] - now)))
            down = [a for a in act if a not in [self.first() + k for k in self.running]]
            parts += ["K%d" % a for a in down]
            return "%s: %s laeuft, Rest gesamt %d min" % (LAUF_NAMES.get(self.lauf, "Lauf"),
                                                          ", ".join(parts), _ceil_min(rest))
        return "%s: Kreiswechsel, Rest gesamt %d min" % (LAUF_NAMES.get(self.lauf, "Lauf"), _ceil_min(rest))

    def _short_run(self, rest):
        act = self._active_list()
        a = ",".join(str(x) for x in act) if act else "-"
        return ("L%d K%s %dm" % (self.lauf if self.lauf != 3 else 0, a, _ceil_min(rest))).replace("L0", "H")

    def _status_master(self, now, P, st1, st2, rest, raw, auto, mode):
        parts = []
        if self.faults:
            parts.append("Stoerung: " + ", ".join(self.faults))
        if self.fb.get("flt"):
            parts.append("Stoerung Folge: " + _text(self.fb.get("flt")))
        if self.hold:
            short = "Trockenlauf"
            parts.append("Trockenlauf: Lauf pausiert, bis Wasser da ist")
        elif self.phase == "prep":
            short = "L%d Vorlauf" % self.lauf if self.lauf != 3 else "H Vorlauf"
            parts.append("%s: Netzteil-Vorlauf" % LAUF_NAMES[self.lauf])
        elif self.phase in ("own", "down"):
            short = self._short_run(rest)
            parts.append(self._run_text(now, rest))
        else:
            nxt = self._next_start(now, st1, st2)
            if self.frostlock:
                short = "Frost"
            elif self.rainlock:
                short = "Regensperre"
            elif not auto:
                short = "Automatik aus"
            elif nxt is not None:
                short = "Start %s" % fmt_tod(nxt[1])
            else:
                short = "Bereit"
            if nxt is not None and auto:
                parts.append("naechster Start %s um %s" % (LAUF_NAMES[nxt[0]], fmt_tod(nxt[1])))
            elif not auto:
                parts.append("Automatik aus")
            else:
                parts.append("keine Laufzeiten eingestellt")
        if self.frostlock:
            parts.append("Frostsperre")
        if self.rainlock:
            if self.rain_until:
                parts.append("Regensperre bis %s" % self._clock(self.rain_until))
            else:
                parts.append("Regensperre")
        elif raw and self.rain_since is not None:
            left = max(0, int(_f(self.p["rain_on"], 300) - (now - self.rain_since)))
            parts.append("Regen erkannt, Sperre in %d:%02d" % (left // 60, left % 60))
            if self.phase == "idle":
                short = "Regen? %d:%02d" % (left // 60, left % 60)
        if self.refill:
            parts.append("Nachspeisung aktiv")
        n = self._recent_note(now)
        if n:
            parts.append("zuletzt: " + n)
        if self.faults and self.phase == "idle":
            short = "Stoerung"
        return short[:14], " | ".join(parts)

    def _status_follower(self, now, P, rest, hold, rain, frost, linked):
        parts = []
        if not linked:
            short = "Keine Kaskade"
            parts.append("Folge: keine Verbindung zum Vorgaenger (E3)")
        elif hold:
            short = "Trockenlauf"
            parts.append("Trockenlauf beim Master: pausiert")
        elif self.phase in ("own", "down", "done"):
            short = self._short_run(rest)
            parts.append(self._run_text(now, rest))
        else:
            short = "Folge bereit"
            parts.append("Folge K%d-K%d bereit" % (self.first(), self.first() + N - 1))
        if frost:
            parts.append("Frostsperre")
        if rain:
            parts.append("Regensperre")
        if self.faults:
            parts.append("Stoerung: " + ", ".join(self.faults))
        n = self._recent_note(now)
        if n:
            parts.append("zuletzt: " + n)
        return short[:14], " | ".join(parts)

    @staticmethod
    def _clock(ts):
        lt = time.localtime(ts)
        return "%02d:%02d" % (lt.tm_hour, lt.tm_min)

    @staticmethod
    def _next_start(now, st1, st2):
        lt = time.localtime(now)
        sod = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
        best = None
        for lauf, st in ((1, st1), (2, st2)):
            if st is None:
                continue
            delta = (st - sod) % DAY
            if best is None or delta < best[2]:
                best = (lauf, st, delta)
        return best


# ------------------------------------------------------------ HS-Anbindung
class LogicModule:

    def __init__(self, hsl3):
        self.fw = hsl3
        self.debug = self.fw.create_debug_section()
        self.eng = Engine()
        self.last = {}

    def on_init(self, inputs, store):
        self.debug.set("Baustein", "%d v%s" % (BLOCK_ID, BLOCK_VERSION))
        vals = {i[0]: inputs.value(i[0]) for i in INPUTS}
        self.eng.set_inputs(vals, [])
        self._run()
        self.fw.set_timer("tick", 1)

    def on_calc(self, inputs):
        vals, changed = {}, []
        for i in INPUTS:
            ident = i[0]
            vals[ident] = inputs.value(ident)
            if inputs.changed(ident):
                changed.append(ident)
        self.eng.set_inputs(vals, changed)
        self._run()

    def on_timer(self, timer):
        self._run()
        self.fw.set_timer("tick", 1)

    def _run(self):
        try:
            out = self.eng.tick(time.time())
        except Exception as e:      # nie den HS-Logikthread abwuergen
            self.debug.log("Fehler: %r" % (e,))
            return
        for ident, _init, _de, _en in OUTPUTS:
            if ident not in out:
                continue
            v = out[ident]
            if ident in ("status", "active", "st1t", "st2t"):
                v = _text(v).encode("iso-8859-15", errors="replace")[:14]
            elif ident in TEXT_OUTPUTS:
                v = _text(v).encode("utf-8")
            else:
                v = float(v)
            if self.last.get(ident) != v:
                self.last[ident] = v
                self.fw.set_output(ident, v)
        self.debug.set("Status", _text(out.get("status_l", "")))
        self.debug.set("Phase", "%s / %s" % (self.eng.phase, LAUF_NAMES.get(self.eng.lauf, "?")))
        self.debug.set("Warteschlange", ",".join(self.eng.cn(it["k"]) for it in self.eng.queue) or "-")
