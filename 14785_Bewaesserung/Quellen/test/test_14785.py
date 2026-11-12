"""Tests 14785 Bewaesserung: Engine im Sekundentakt, Kaskade ueber
simulierte iKOs, dazu LogicModule mit Fake-Framework.
Aufruf: TZ=UTC python3 test_14785.py ../src/hsl3_14785_bewaesserung.py"""
import importlib.util
import json
import os
import sys
import time

os.environ["TZ"] = "UTC"
time.tzset()
spec = importlib.util.spec_from_file_location("m", sys.argv[1])
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

ok = True
T0 = 1793750400  # 2026-11-04 00:00 UTC (beliebiger Tag)


def check(name, cond, info=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(info) if info else ""))
    ok &= bool(cond)


def hm(h, m=0, s=0):
    return T0 + h * 3600 + m * 60 + s


class Sim(object):
    """Master + beliebig viele Folgen, Verdrahtung A19->E3, A20->E4."""

    def __init__(self, n_follow=0, **kw):
        self.blocks = [M.Engine() for _ in range(1 + n_follow)]
        for i, b in enumerate(self.blocks):
            vals = {k[0]: k[1] for k in M.INPUTS}
            vals["mode"] = 0 if i == 0 else 1
            vals["first"] = 1 + 5 * i
            b.set_inputs(vals, [])
        self.set(0, **kw)
        self.now = None
        self.log = []          # (t, block, key, value)

    def set(self, i, **kw):
        self.blocks[i].set_inputs(kw, list(kw.keys()))

    def step(self, now):
        outs = []
        for b in self.blocks:
            outs.append(b.tick(now))
        # Verdrahtung (wie iKOs: neuer Wert erst im naechsten Takt)
        for i in range(len(self.blocks) - 1):
            a, f = self.blocks[i], self.blocks[i + 1]
            if outs[i]["cout"] != f.p.get("cin"):
                f.set_inputs({"cin": outs[i]["cout"]}, ["cin"])
            if outs[i + 1]["fbout"] != a.p.get("fbin"):
                a.set_inputs({"fbin": outs[i + 1]["fbout"]}, ["fbin"])
        return outs

    def run(self, t_from, t_to, watch=None):
        last = {}
        t = t_from
        while t <= t_to:
            outs = self.step(t)
            for i, o in enumerate(outs):
                for k, v in o.items():
                    if watch and k not in watch:
                        continue
                    if last.get((i, k)) != v:
                        last[(i, k)] = v
                        self.log.append((t, i, k, v))
            t += 1
        self.now = t_to
        return outs

    def times(self, i, key, val):
        return [t for (t, b, k, v) in self.log if b == i and k == key and v == val]


WATCH = None
P0 = {"wf": 100.0, "pause": 0.0, "ov": 0.0, "wd": 120.0, "mp": 1}

# ------------------------------------------------------------ 1 Planung
check("sim seriell 10+5+8 min", M.simulate([(600, 0), (300, 0), (480, 0)], (), P0) == 1380)
P = dict(P0, mp=3)
check("sim 2 exklusiv + 3 parallel", M.simulate([(600, 0), (600, 0), (300, 1), (300, 1), (300, 1)], (), P) == 1500)
P = dict(P0, mp=2)
check("sim parallel max 2: 5,5,5 -> 10 min", M.simulate([(300, 1), (300, 1), (300, 1)], (), P) == 600)
P = dict(P0, ov=5)
check("sim Ueberlappung 5 s", M.simulate([(600, 0), (300, 0), (480, 0)], (), P) == 1370)
P = dict(P0, pause=10)
check("sim Pause 10 s", M.simulate([(600, 0), (300, 0), (480, 0)], (), P) == 1400)
check("Uhrzeit Text", M.parse_tod("06:30") == 23400 and M.parse_tod(b"5:07") == 18420)
check("Uhrzeit Zahl", M.parse_tod(6.5) == 23400 and M.parse_tod(23400) == 23400)

# ------------------------------------------------------------ 2 Automatiklauf Master
base = dict(k1_t=10, k2_t=5, k3_t=0, k4_t=8, k5_t=0, k2_rain=0, end="06:00", pump_delay=3, relief=3,
            psu_pre=2, psu_post=5, psu_mode=0)
s = Sim(**base)
o = s.run(hm(5, 0), hm(5, 0))
check("Gesamtlaufzeit Lauf 1 = 24 min (23 min + 2 s)", o[0]["dur1"] == 24, o[0]["dur1"])
check("Startzeit 05:36", o[0]["st1t"] == "05:36", o[0]["st1t"])
check("kein Lauf 2", o[0]["st2t"] == "--:--" and o[0]["dur2"] == 0)
check("Status kurz zeigt Start", o[0]["status"] == "Start 05:36", o[0]["status"])
o = s.run(hm(5, 0, 1), hm(6, 0, 30), WATCH)
st1 = M.parse_tod("05:36:58")
check("Netzteil an um 05:36:58", s.times(0, "psu", 1)[0] == T0 + st1, s.times(0, "psu", 1))
check("K1 auf nach Vorlauf 2 s", s.times(0, "k1_valve", 1)[0] == T0 + st1 + 2)
check("Pumpe 3 s nach Ventil", s.times(0, "pump", 1)[0] == T0 + st1 + 5)
check("K2 nach K1", s.times(0, "k2_valve", 1)[0] == T0 + st1 + 2 + 600)
check("K3 (0 min) nie", not s.times(0, "k3_valve", 1))
t_k4_off = s.times(0, "k4_valve", 0)[-1]
check("Ende genau 06:00", t_k4_off == hm(6, 0), time.strftime("%H:%M:%S", time.gmtime(t_k4_off)))
check("Pumpe aus 3 s vor Ende (Druckentlastung)", s.times(0, "pump", 0)[-1] == hm(6, 0) - 3)
check("Netzteil aus 5 s nach Ende", s.times(0, "psu", 0)[-1] == hm(6, 0, 5))
check("A4 Programm laeuft wieder 0", o[0]["running"] == 0)
pump_on = s.times(0, "pump", 1)
check("Pumpe ohne Pause durchgehend (1x ein)", len(pump_on) == 1, pump_on)

# ------------------------------------------------------------ 3 Netzteil Modus 2 (Fenster)
s = Sim(**dict(base, psu_mode=2, window=60))
s.run(hm(5, 30), hm(7, 10), ("psu",))
check("Modus 2: Netzteil bis 07:00:05", s.times(0, "psu", 0)[-1] == hm(7, 0, 5))
s = Sim(**dict(base, psu_mode=1))
o = s.run(hm(5, 30), hm(5, 30))
check("Modus 1: Netzteil dauerhaft, kein Vorlauf in Zeit", o[0]["psu"] == 1 and o[0]["st1t"] == "05:37")

# ------------------------------------------------------------ 4 Regen
s = Sim(**dict(base, rain_on=300, rain_after=120))
s.run(hm(5, 36), hm(5, 38))
s.set(0, rain=1)                       # 05:38 Regen, K1 (Regen beachten) laeuft
s.run(hm(5, 38, 1), hm(5, 40))
s.set(0, rain=0)                       # nur 2 min -> keine Sperre
s.run(hm(5, 40, 1), hm(5, 40, 5))
check("Regen < Verzoegerung: K1 laeuft weiter", s.blocks[0].out["k1_valve"] == 1)
s.set(0, rain=1)                       # ab 05:40:06 durchgehend
s.run(hm(5, 40, 6), hm(5, 46))
k1_off = s.times(0, "k1_valve", 0)
check("Regen >= 300 s: K1 abgebrochen 05:45:06", k1_off[-1] == hm(5, 45, 6), time.strftime("%H:%M:%S", time.gmtime(k1_off[-1])))
check("K2 ohne Regensperre startet sofort", s.times(0, "k2_valve", 1)[-1] == hm(5, 45, 6))
o = s.run(hm(5, 46, 1), hm(6, 0))
check("K2 laeuft volle 5 min", s.times(0, "k2_valve", 0)[-1] == hm(5, 50, 6))
check("K4 (Regen) uebersprungen", not s.times(0, "k4_valve", 1))
check("Regensperre aktiv", o[0]["rainlock"] == 1 and o[0]["running"] == 0)
s.set(0, rain=0)
s.run(hm(6, 0, 1), hm(8, 1))
check("Nachwirkzeit 120 min -> Sperre weg 08:00:01", s.times(0, "rainlock", 0)[-1] == hm(8, 0, 1))

# ------------------------------------------------------------ 5 Frost
s = Sim(**dict(base, t_out=1.5))
o = s.run(hm(5, 30), hm(6, 10))
check("Frost: kein Automatikstart", not s.times(0, "k1_valve", 1) and o[0]["frostlock"] == 1)
s.set(0, t_out=3.5)
o = s.run(hm(6, 10, 1), hm(6, 10, 1))
check("Frost Hysterese 1 K: bei 3,5 noch aktiv", o[0]["frostlock"] == 1)
s.set(0, t_out=4.0)
o = s.run(hm(6, 10, 2), hm(6, 10, 2))
check("Frost aus ab 4,0", o[0]["frostlock"] == 0)

# ------------------------------------------------------------ 6 Hand + Stop + Automatik aus
s = Sim(**dict(base, auto=0))
s.run(hm(12), hm(12))
s.set(0, k2_hand=1)
s.run(hm(12, 0, 1), hm(12, 2))
check("Handstart K2 ohne Programm -> Hand-Lauf", s.times(0, "k2_valve", 1) == [hm(12, 0, 3)], s.times(0, "k2_valve", 1))
check("A5 = 3 (Hand)", 3 in [v for (t, b, k, v) in s.log if k == "run_no"])
s.set(0, k2_hand=0)
o = s.run(hm(12, 2, 1), hm(12, 2, 2))
check("Hand-Stopp schliesst", o[0]["k2_valve"] == 0 and o[0]["running"] == 0)
s.set(0, k3_hand=1)
o = s.run(hm(12, 3), hm(12, 3, 5))
check("Handstart K3 mit 0 min -> nichts", o[0]["k3_valve"] == 0 and "keine Laufzeit" in o[0]["status_l"])
o = s.run(hm(5, 0), hm(6, 30))   # (Zeit springt; Automatik aus)
check("Automatik aus: kein Start", not [t for t in s.times(0, "k1_valve", 1) if t > hm(5)])
s.set(0, auto=1, start=1)
s.run(hm(13), hm(13, 0, 10))
check("Programm-Start E6 -> K1 laeuft", s.blocks[0].out["k1_valve"] == 1)
s.set(0, stop=1)
o = s.run(hm(13, 0, 11), hm(13, 0, 12))
check("Stopp: alles zu", o[0]["k1_valve"] == 0 and o[0]["running"] == 0 and o[0]["pump"] == 0)

# ------------------------------------------------------------ 7 Lauf 2 (Zyklus 2)
s = Sim(**dict(base, k1_cyc=2, k4_cyc=2))
o = s.run(hm(12), hm(12))
check("Lauf 2: 18 min + 2 s, Start 17:41:58", o[0]["dur2"] == 19 and o[0]["st2t"] == "17:41", (o[0]["dur2"], o[0]["st2t"]))
s.run(hm(17, 41), hm(18, 0, 10))
check("Lauf 2: K1, K4, nicht K2", s.times(0, "k1_valve", 1) and s.times(0, "k4_valve", 1) and not s.times(0, "k2_valve", 1))
check("Lauf 2 endet 18:00", s.times(0, "k4_valve", 0)[-1] == hm(18))

# ------------------------------------------------------------ 8 Parallel
s = Sim(**dict(base, k1_t=10, k2_t=10, k3_t=5, k4_t=5, k5_t=5, k3_par=1, k4_par=1, k5_par=1, max_par=3))
o = s.run(hm(5), hm(5))
check("Parallel: 25 min + 2 s -> 26 min", o[0]["dur1"] == 26 and o[0]["st1t"] == "05:34")
s.run(hm(5, 34), hm(6, 0, 10))
check("K3,K4,K5 gemeinsam", s.times(0, "k3_valve", 1) == s.times(0, "k4_valve", 1) == s.times(0, "k5_valve", 1))
check("A6 Aktive Kreise '3,4,5'", ("3,4,5" in [v for (t, b, k, v) in s.log if k == "active"]))

# ------------------------------------------------------------ 9 Kaskade Master + Folge
s = Sim(1, **dict(base, overlap=2))
s.set(1, k1_t=4, k2_t=0, k3_t=3, k4_t=0, k5_t=0)      # Folge = K6..K10
o = s.run(hm(5), hm(5, 0, 5))
# Master 23 min - 2 x 2 s Ueberlappung, Folge 7 min - 2 s, Uebergabe -2 s: 23*60+7*60-6 = 1794 + 2 Vorlauf
check("Kaskade: Gesamtlaufzeit 30 min (1796 s)", o[0]["dur1"] == 30, o[0]["dur1"])
check("Kaskade: Startzeit 05:30:04 -> '05:30'", o[0]["st1t"] == "05:30", o[0]["st1t"])
check("Folge zeigt keine Startzeit, aber Kreisnummer", o[1]["status"] == "Folge bereit")
s.run(hm(5, 0, 6), hm(6, 1), WATCH)
k6 = s.times(1, "k1_valve", 1)
k4_off = s.times(0, "k4_valve", 0)
check("K6 (Folge) startet nach K4", k6 and k6[0] >= k4_off[-1] - 3, (k6, k4_off))
end = s.times(1, "k3_valve", 0)[-1]
check("Kette endet um 06:00 (+-3 s Kaskadenlaufzeit)", abs(end - hm(6)) <= 3, time.strftime("%H:%M:%S", time.gmtime(end)))
check("Pumpe ueber Uebergabe durchgehend", len(s.times(0, "pump", 1)) == 1, s.times(0, "pump", 1))
check("Master beendet erst nach Folge", s.times(0, "running", 0)[-1] >= end)
check("A6 am Master zeigt K8", "8" in [v for (t, b, k, v) in s.log if b == 0 and k == "active"])

# Handstart in der Folge -> Master startet Hand-Lauf, Netzteil + Pumpe vom Master
s.set(1, k3_hand=1)
s.run(hm(12), hm(12, 0, 30))
check("Folge-Hand: Netzteil an", s.blocks[0].out["psu"] == 1)
check("Folge-Hand: K8 offen", s.blocks[1].out["k3_valve"] == 1)
check("Folge-Hand: Pumpe am Master", s.blocks[0].out["pump"] == 1)
s.run(hm(12, 0, 31), hm(12, 4))
check("Folge-Hand: fertig, Netzteil im Nachlauf/aus", s.blocks[0].out["running"] == 0)

# Stopp vom Master stoppt Folge
s.set(0, start=1)
s.run(hm(13), hm(13, 25))
check("Folge laeuft (K6)", s.blocks[1].out["k1_valve"] == 1)
s.set(0, stop=1)
s.run(hm(13, 25, 1), hm(13, 25, 4))
check("Stopp am Master schliesst Folge", s.blocks[1].out["k1_valve"] == 0 and s.blocks[0].out["running"] == 0)

# ------------------------------------------------------------ 10 Nachspeisung
s = Sim(**dict(base, refill_max=10, psu_mode=0))
s.run(hm(12), hm(12))
s.set(0, lmin=1)
o = s.run(hm(12, 0, 1), hm(12, 0, 2))
check("Nachspeisung an bei leer, Netzteil an", o[0]["refill"] == 1 and o[0]["psu"] == 1)
s.run(hm(12, 0, 3), hm(12, 10, 5))
check("ohne Max-Schwimmer: nach 10 min aus, keine Stoerung", s.blocks[0].out["refill"] == 0 and s.blocks[0].out["fault"] == 0)
s.run(hm(12, 10, 6), hm(12, 11))
check("kein Neustart solange min noch 1", s.blocks[0].out["refill"] == 0)
s.set(0, lmin=0)
s.run(hm(12, 11, 1), hm(12, 11, 2))
s.set(0, lmin=1)
o = s.run(hm(12, 11, 3), hm(12, 11, 4))
check("erneut leer -> wieder an", o[0]["refill"] == 1)
s.set(0, lmax=1)
o = s.run(hm(12, 11, 5), hm(12, 11, 6))
check("Max-Schwimmer voll -> aus", o[0]["refill"] == 0)
s.set(0, lmax=0)
s.run(hm(12, 11, 7), hm(12, 30))
check("mit Max: Zeit ueberschritten -> Stoerung", s.blocks[0].out["fault"] == 1 and s.blocks[0].out["refill"] == 0)
s.set(0, ack=1, lmin=0)
o = s.run(hm(12, 30, 1), hm(12, 30, 2))
check("Quittieren loescht Stoerung", o[0]["fault"] == 0)

# ------------------------------------------------------------ 11 Trockenlauf
s = Sim(**dict(base, dry=30))
s.run(hm(5, 36), hm(5, 40))
s.set(0, lmin=1)
s.run(hm(5, 40, 1), hm(5, 41))
o = s.blocks[0].out
check("Trockenlauf: Ventil zu, Pumpe aus", o["k1_valve"] == 0 and o["pump"] == 0 and o["status"] == "Trockenlauf")
s.set(0, lmin=0)
s.run(hm(5, 41, 1), hm(6, 30))
check("nach Wasser: K1 weiter, Rest erhalten (Ende ~06:00:30)",
      abs(s.times(0, "k4_valve", 0)[-1] - hm(6, 0, 30)) <= 2,
      time.strftime("%H:%M:%S", time.gmtime(s.times(0, "k4_valve", 0)[-1])))

# ------------------------------------------------------------ 12 Wetterfaktor + Watchdog-Kappung
s = Sim(**dict(base, wf=50))
o = s.run(hm(5), hm(5))
check("Wetterfaktor 50 %: 11,5 min + 2 s -> 12 min", o[0]["dur1"] == 12, o[0]["dur1"])
s = Sim(**dict(base, k1_t=200, wd=120))
o = s.run(hm(1), hm(1))
check("Laufzeit auf Watchdog 120 min begrenzt", o[0]["dur1"] == 134, o[0]["dur1"])

# ------------------------------------------------------------ 12b Randfaelle
s = Sim(**dict(base, end="00:10"))
o = s.run(hm(22), hm(22))
check("Ende 00:10 -> Start 23:46 (ueber Mitternacht)", o[0]["st1t"] == "23:46", o[0]["st1t"])
s.run(hm(23, 46), hm(24, 10, 5), ("k1_valve", "k4_valve"))
check("Start ueber Mitternacht ausgefuehrt, Ende 00:10", s.times(0, "k4_valve", 0)[-1] == hm(24, 10))
s = Sim(**dict(base, pause=20))
s.run(hm(5, 30), hm(6, 1), ("pump", "k2_valve"))
check("Pause 20 s: Pumpe geht zwischen Kreisen aus", len(s.times(0, "pump", 1)) == 3, s.times(0, "pump", 1))
check("Pause: Ende trotzdem 06:00", s.times(0, "k2_valve", 0)[-1] < hm(6))
s = Sim(**base)
s.run(hm(5, 36), hm(5, 40))
s.set(0, k5_t=2, k5_hand=1)
s.run(hm(5, 40, 1), hm(6, 5), ("k5_valve",))
check("Hand waehrend Programm: hinten angehaengt (nach K4, 06:00)", s.times(0, "k5_valve", 1) == [hm(6)], s.times(0, "k5_valve", 1))

# ------------------------------------------------------------ 12c Rueckmeldung (v1.1)


class SimFB(Sim):
    """Wie Sim, dazu ein Aktor: Rueckmeldung folgt dem Ventil nach `delay` s;
    dead = Kreise, deren Aktor nicht reagiert."""

    def __init__(self, n_follow=0, delay=2, dead=(), **kw):
        Sim.__init__(self, n_follow, **kw)
        self.delay, self.dead, self.pend, self.cur = delay, set(dead), [], {}

    def step(self, now):
        for item in [p for p in self.pend if p[0] <= now]:
            self.pend.remove(item)
            _t, i, key, val = item
            self.blocks[i].set_inputs({key: val}, [key])
        outs = Sim.step(self, now)
        for i, o in enumerate(outs):
            for k in range(1, 6):
                v = o["k%d_valve" % k]
                if self.cur.get((i, k)) != v:
                    self.cur[(i, k)] = v
                    if (i, k) not in self.dead:
                        self.pend.append((now + self.delay, i, "k%d_fb" % k, v))
        return outs

    def extern(self, i, k, v):
        self.cur[(i, k)] = v
        self.set(i, **{"k%d_fb" % k: v})


fbbase = dict(base, k1_fb=0, k2_fb=0, k4_fb=0)
s = SimFB(**fbbase)
for k in (1, 2, 4):                       # Rueckmeldung angeschlossen (Telegramm 0 beim Start)
    s.set(0, **{"k%d_fb" % k: 0})
s.run(hm(5, 30), hm(6, 2), ("k1_valve", "k2_valve", "k4_valve", "running"))
on1, off1 = s.times(0, "k1_valve", 1)[0], s.times(0, "k1_valve", 0)[-1]
check("RM: K1 laeuft 10 min ab Rueckmeldung (2 s spaeter)", off1 - on1 == 602, off1 - on1)
check("RM: Lauf endet ~6 s spaeter (3 Kreise x 2 s)", s.times(0, "k4_valve", 0)[-1] == hm(6, 0, 6))

s = SimFB(**fbbase)
s.run(hm(12), hm(12, 0, 2))
s.extern(0, 2, 1)                          # K2 am Taster ein, kein Programm
o = s.run(hm(12, 0, 3), hm(12, 0, 10))
check("Extern ein: Netzteil an, Ventil-Ausgang 1, Hand-Lauf", o[0]["psu"] == 1 and o[0]["k2_valve"] == 1 and o[0]["run_no"] == 3)
s.run(hm(12, 0, 11), hm(12, 6), ("k2_valve", "k1_valve", "k4_valve", "running"))
check("Extern ein: nach 5 min aus", s.times(0, "k2_valve", 0)[-1] == hm(12, 5, 3), time.strftime("%H:%M:%S", time.gmtime(s.times(0, "k2_valve", 0)[-1])))
check("Extern ein: kein weiterer Kreis", not s.times(0, "k1_valve", 1) and not s.times(0, "k4_valve", 1))
check("Extern ein: Lauf beendet", s.blocks[0].out["running"] == 0)

s.extern(0, 4, 1)
s.run(hm(13), hm(13, 1))
s.extern(0, 4, 0)                          # extern wieder aus
o = s.run(hm(13, 1, 1), hm(13, 1, 3))
check("Extern aus: Kreis beendet, sonst nichts", o[0]["k4_valve"] == 0 and o[0]["running"] == 0 and o[0]["k1_valve"] == 0)

s = SimFB(**fbbase)
for k in (1, 2, 4):
    s.set(0, **{"k%d_fb" % k: 0})
s.run(hm(5, 36), hm(5, 40), ("k1_valve", "k2_valve"))
s.extern(0, 1, 0)                          # Programm laeuft, K1 extern aus
s.run(hm(5, 40, 1), hm(5, 40, 5), ("k1_valve", "k2_valve"))
check("Programm: K1 extern aus -> K2 startet", s.times(0, "k2_valve", 1) and s.times(0, "k2_valve", 1)[0] <= hm(5, 40, 2))
s.extern(0, 4, 1)                          # anderer Kreis extern ein, waehrend K2 laeuft
s.run(hm(5, 40, 6), hm(5, 41))
o = s.blocks[0].out
check("Programm + extern: K2 und K4 gleichzeitig (Variante a)", o["k2_valve"] == 1 and o["k4_valve"] == 1)
s.run(hm(5, 41, 1), hm(6, 0), ("k4_valve", "k2_valve"))
k4_off = s.times(0, "k4_valve", 0)
check("K4 einmal 8 min, nicht nochmal im Programm", k4_off == [hm(5, 48, 6)] and o["k4_valve"] == 1,
      [time.strftime("%H:%M:%S", time.gmtime(t)) for t in k4_off])

s = SimFB(dead=[(0, 1)], **fbbase)
s.set(0, k1_fb=0)
s.run(hm(5, 36), hm(5, 37, 20))
check("Keine Rueckmeldung: Stoerung nach 10 s", s.blocks[0].out["fault"] == 1 and "keine Rueckmeldung" in s.blocks[0].out["status_l"])
check("Keine Rueckmeldung: Zeit laeuft trotzdem", s.blocks[0].out["k1_valve"] == 1 and s.blocks[0].out["k1_rest"] == 10)

s = SimFB(1, **base)
s.set(1, k1_t=4, k3_t=3)
s.run(hm(12), hm(12, 0, 3))
s.extern(1, 3, 1)                          # Folge K8 extern ein
s.run(hm(12, 0, 4), hm(12, 0, 15))
check("Folge extern ein: Master schaltet Netzteil + Pumpe", s.blocks[0].out["psu"] == 1 and s.blocks[0].out["pump"] == 1)
s.run(hm(12, 0, 16), hm(12, 4))
check("Folge extern ein: nach 3 min aus, kein K6", s.blocks[1].out["k3_valve"] == 0 and not s.times(1, "k1_valve", 1))

# ------------------------------------------------------------ 13 LogicModule mit Fake-Framework


class FakeInputs(object):
    def __init__(self, vals, changed=()):
        self.vals, self.ch = vals, set(changed)

    def value(self, k):
        return self.vals[k]

    def changed(self, k):
        return k in self.ch


class FakeDebug(object):
    def __init__(self):
        self.d = {}

    def set(self, k, v):
        self.d[k] = v

    def log(self, t):
        self.d.setdefault("_log", []).append(t)


class FakeFW(object):
    def __init__(self):
        self.out, self.timers, self.dbg = {}, [], FakeDebug()

    def create_debug_section(self):
        return self.dbg

    def set_output(self, k, v):
        self.out[k] = v

    def set_timer(self, k, s):
        self.timers.append((k, s))


fw = FakeFW()
lm = M.LogicModule(fw)
vals = {i[0]: i[1] for i in M.INPUTS}
vals.update(k1_t=10.0, end=b"06:00")
lm.on_init(FakeInputs(vals), None)
check("on_init: Timer gesetzt", fw.timers == [("tick", 1)])
check("Ausgaenge float/bytes", isinstance(fw.out["dur1"], float) and isinstance(fw.out["status"], bytes))
check("Status kurz <= 14 Byte", len(fw.out["status"]) <= 14 and len(fw.out["st1t"]) == 5, fw.out["status"])
vals["k1_hand"] = 1.0
lm.on_calc(FakeInputs(vals, ["k1_hand"]))
check("on_calc: Handstart angenommen", lm.eng.phase in ("prep", "own"), lm.eng.phase)
for _ in range(3):
    lm.on_timer("tick")
check("Debug-Seite ohne Fehler", "_log" not in fw.dbg.d, fw.dbg.d.get("_log"))
check("Kaskaden-Text ist JSON", json.loads(fw.out["cout"].decode())["l"] == 3)

print("\nALLE OK" if ok else "\nFEHLER")
sys.exit(0 if ok else 1)
