"""Baut 14785: config.json, .hsl (Gira-Generator, Python 3.9), Hilfe DE/EN, .hslz.
Aufruf: python build.py            (Pfade ueber HSL3_GEN / PY39 anpassen)
        python build.py --no-gen   (nur config.json + Hilfe, ohne Generator)"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ID = "14785"
SLUG = "Bewaesserung"
SCRIPT = "hsl3_14785_bewaesserung.py"
GEN = os.environ.get("HSL3_GEN", os.path.join(HERE, "generator3.cpython-39.pyc"))
PY39 = os.environ.get("PY39", "python3.9")
CAT_DE, CAT_EN = "Garten", "Garden"
NAME_DE = "14785 Bewässerung 5 Kreise (kaskadierbar)"
NAME_EN = "14785 Irrigation 5 circuits (cascadable)"

spec = importlib.util.spec_from_file_location("m", os.path.join(HERE, "src", SCRIPT))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
VERSION = M.BLOCK_VERSION

# Umlaute fuer die deutschen Labels (Code bewusst ASCII). Wortliste statt
# Ersetzungsregel, damit z. B. "dauerhaft" nicht zu "daürhaft" wird.
WORDS = {"Aussentemperatur": "Außentemperatur", "Einschaltverzoegerung": "Einschaltverzögerung",
         "Fuellstand": "Füllstand", "Gewuenschtes": "Gewünschtes", "Rueckmeldung": "Rückmeldung",
         "Stoerung": "Störung", "Ueberlappung": "Überlappung", "Verzoegerung": "Verzögerung",
         "Vorgaenger": "Vorgänger", "ausfuehrlich": "ausführlich", "laeuft": "läuft",
         "taeglich": "täglich", "ueberspringen": "überspringen", "waehrend": "während", "degC": "°C"}


def de(t):
    for a, b in WORDS.items():
        t = t.replace(a, b)
    return t


def slot(t):
    ident, init, _de, en = t
    typ = "string" if isinstance(init, str) else "number"
    return {"type": typ, "identifier": ident, "init_value": init, "label": en}


def main():
    no_gen = "--no-gen" in sys.argv
    b = os.path.join(HERE, "build")
    shutil.rmtree(b, ignore_errors=True)
    os.makedirs(b)
    shutil.copy(os.path.join(HERE, "src", SCRIPT), b)
    hsl = "%s_%s.hsl" % (ID, SLUG)
    cfg = {"module": {
        "category": CAT_EN, "context": "ElektroRausch_14785", "id": ID, "name": NAME_EN,
        "hsl_filename": hsl, "version": VERSION,
        "inputs": [slot(i) for i in M.INPUTS],
        "outputs": [slot(o) for o in M.OUTPUTS],
        "stores": [], "timers": [{"identifier": "tick"}],
        "scripts": [{"filename": SCRIPT}],
        "translations": [
            {"language": "de", "name": NAME_DE, "category": CAT_DE,
             "translation_inputs": [{"label": de(i[2])} for i in M.INPUTS],
             "translation_outputs": [{"label": de(o[2])} for o in M.OUTPUTS]},
            {"language": "en", "name": NAME_EN, "category": CAT_EN,
             "translation_inputs": [{"label": i[3]} for i in M.INPUTS],
             "translation_outputs": [{"label": o[3]} for o in M.OUTPUTS]},
        ]}}
    with open(os.path.join(b, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    shutil.copy(os.path.join(b, "config.json"), os.path.join(HERE, "config.json"))
    sys.path.insert(0, os.path.join(HERE, "help"))
    import make_help
    make_help.write(M, de, b, VERSION)
    for lang in ("DE", "EN"):
        n = "%s-log%s.html" % (lang, ID)
        shutil.copy(os.path.join(b, n), os.path.join(HERE, n))
    if no_gen:
        print("OK (ohne Generator): config.json + Hilfe in", b)
        return
    shutil.copy(GEN, b)
    subprocess.check_call([PY39, os.path.basename(GEN), "--source", "config.json", "--target", hsl], cwd=b)
    hslz = os.path.join(b, "%s_%s.hslz" % (ID, SLUG))
    with zipfile.ZipFile(hslz, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(b, hsl), hsl)
        for lang in ("DE", "EN"):
            z.write(os.path.join(b, "%s-log%s.html" % (lang, ID)), "%s-log%s.html" % (lang, ID))
    os.remove(os.path.join(b, os.path.basename(GEN)))
    print("OK", hsl, hslz)


if __name__ == "__main__":
    main()
