"""Tests 14775 gegen die Beispiele aus der Anforderung + Fake-Framework."""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("m", sys.argv[1])
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

ok = True


def check(name, cond, info=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(info) if info else ""))
    ok &= bool(cond)


def P(**kw):
    p = {i[0]: float(i[1]) for i in M.INPUTS}
    p.update({k: float(v) for k, v in kw.items()})
    return p


c = M.compute
# 1. AUS
o, s = c(P(enable=0, aq=2000), {"ot": True, "amp": 0})
check("AUS: Ventilatoren 0, AU/FO zu", o["supply"] == 0 and o["exhaust"] == 0 and o["oa"] == 0 and o["ex"] == 0 and not s["ot"])
check("AUS: Ampel trotzdem rot", o["amp"] == 2)

# 2. Klappen gut / schlecht / Mitte
o, _ = c(P(enable=1, aq=800), None)
check("gut: UM80 AU20 FO20", (o["rec"], o["oa"], o["ex"]) == (80, 20, 20), o["status"])
o, _ = c(P(enable=1, aq=1400), None)
check("schlecht: UM0 AU100 FO100", (o["rec"], o["oa"], o["ex"]) == (0, 100, 100))
o, _ = c(P(enable=1, aq=1100), None)
check("Mitte: UM40 AU60 FO60", (o["rec"], o["oa"], o["ex"]) == (40, 60, 60))
o, _ = c(P(enable=1, aq=300), None)
check("besser als gut begrenzt", o["rec"] == 80)
o, _ = c(P(enable=1, aq=60, aq_good=80, aq_bad=20), None)   # fallende Skala (LQ %)
check("fallende Skala 80%%gut/20%%schlecht, 60 -> 1/3", abs(o["aq_level"] - 33.3) < 0.1, o["aq_level"])

# 2.1 Uebertemperatur Hysterese
s = None
o, s = c(P(enable=1, aq=800, t_room=21.0, t_set=20), s)
check("+1,0 K noch nicht Uebertemp.", o["ot"] == 0)
o, s = c(P(enable=1, aq=800, t_room=21.1, t_set=20), s)
check(">+1,0 K -> 100 % AU", o["ot"] == 1 and (o["rec"], o["oa"], o["ex"]) == (0, 100, 100))
o, s = c(P(enable=1, aq=800, t_room=20.6, t_set=20), s)
check("+0,6 K bleibt (Hysterese)", o["ot"] == 1)
o, s = c(P(enable=1, aq=800, t_room=20.4, t_set=20), s)
check("<+0,5 K zurueck zur LQ-Automatik", o["ot"] == 0 and o["rec"] == 80)

# 3. Ventilatoren
o, _ = c(P(enable=1, aq=800), None)
check("gut -> 30 %", o["supply"] == 30 and o["exhaust"] == 30)
o, _ = c(P(enable=1, aq=1400), None)
check("schlecht -> 100 %", o["supply"] == 100 and o["exhaust"] == 100)

# 4. Freecooling – Beispiel: LQ ergibt 60 %, Korrektur 50 % -> ZU 30 / AB 60
aq60 = 800 + (1400 - 800) * (60 - 30) / 70.0
o, _ = c(P(enable=1, aq=aq60, t_room=22.5, t_set=20, t_out=15), None)
check("Beispiel ZU 30 / AB 60", o["supply"] == 30 and o["exhaust"] == 60 and o["fc"] == 1 and o["fc_corr"] == 50, o["status"])
o, _ = c(P(enable=1, aq=aq60, t_room=22.5, t_set=20, t_out=12), None)
check("Aussen = 12 degC -> kein Freecooling", o["fc"] == 0 and o["supply"] == 60)
o, _ = c(P(enable=1, aq=aq60, t_room=22.5, t_set=20, t_out=23), None)
check("Aussen waermer als innen -> kein Freecooling", o["fc"] == 0)
o, _ = c(P(enable=1, aq=aq60, t_room=19.5, t_set=20, t_out=15), None)
check("Raum unter Soll -> kein Freecooling", o["fc"] == 0)
o, _ = c(P(enable=1, aq=aq60, t_room=27, t_set=20, t_out=15), None)
check("dT 7 K -> 100 % Korrektur, ZU 0", o["supply"] == 0 and o["exhaust"] == 60)
o, _ = c(P(enable=1, aq=aq60, t_room=27, t_set=20, t_out=15, fc_supply_min=20), None)
check("Untergrenze 20 %%", o["supply"] == 20)
o, _ = c(P(enable=1, aq=aq60, t_room=22.5, t_set=20, t_out=15, fc_t_out_min=16), None)
check("Grenze einstellbar (16 degC)", o["fc"] == 0)


# 5. Ampel
s = None
seq = [(900, 0), (1000, 1), (1399, 1), (1400, 2), (1360, 2), (1349, 1), (960, 1), (949, 0), (1500, 2), (700, 0)]
for aq, exp in seq:
    o, s = c(P(enable=1, aq=aq), s)
    check("Ampel %d ppm -> %d" % (aq, exp), o["amp"] == exp, o["amp"])
s = None
for aq, exp in [(85, 0), (70, 0), (45, 1), (25, 2), (32, 2), (36, 1)]:   # LQ in %, 100 = gut
    o, s = c(P(enable=1, aq=aq, aq_good=80, aq_bad=30, amp_yellow=50, amp_red=30, amp_hyst=5), s)
    check("Ampel fallende Skala %d %% -> %d" % (aq, exp), o["amp"] == exp, o["amp"])


# Framework-Lauf
class Slots:
    def __init__(self, d, ch=()):
        self.d, self.ch = d, ch

    def value(self, k):
        return self.d[k]

    def changed(self, k):
        return k in self.ch

    def keys(self):
        return list(self.d)


class Dbg:
    def set(self, *a):
        pass

    def log(self, *a):
        pass


class FW:
    def __init__(self):
        self.out = []

    def create_debug_section(self):
        return Dbg()

    def set_output(self, k, v):
        assert isinstance(v, (int, float, bytes)), (k, v)
        self.out.append((k, v))


fw = FW()
m = M.LogicModule(fw)
d = {i[0]: i[1] for i in M.INPUTS}
m.on_init(Slots(d), None)
check("on_init setzt alle Ausgaenge", len(fw.out) == len(M.OUTPUTS))
n = len(fw.out)
m.on_calc(Slots(d, ("aq",)))
check("unveraendert -> nichts senden", len(fw.out) == n)
d["enable"] = 1
d["aq"] = 1400
m.on_calc(Slots(d, ("enable",)))
check("Aenderung -> Ausgaenge gesendet", dict(fw.out[n:]).get("supply") == 100.0, fw.out[n:])

print("\nALLES OK" if ok else "\nFEHLER")
sys.exit(0 if ok else 1)
