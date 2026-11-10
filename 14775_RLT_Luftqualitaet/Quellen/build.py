"""Baut 14775: config.json, .hsl (Gira-Generator, Python 3.9), Hilfe DE/EN, .hslz.
Aufruf: python build.py  (Pfade GEN/PY39 ggf. anpassen)"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ID = "14775"
SLUG = "RLT_Luftqualitaet"
SCRIPT = "hsl3_14775_rlt_luftqualitaet.py"
GEN = os.environ.get("HSL3_GEN", os.path.join(HERE, "generator3.cpython-39.pyc"))
PY39 = os.environ.get("PY39", "/root/.local/share/uv/python/cpython-3.9-linux-x86_64-gnu/bin/python3.9")
CAT_DE, CAT_EN = "Lüftung", "Ventilation"
NAME_DE = "14775 RLT Luftqualitätsregelung"
NAME_EN = "14775 AHU air quality control"

spec = importlib.util.spec_from_file_location("m", os.path.join(HERE, "src", SCRIPT))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
VERSION = M.BLOCK_VERSION

# Deutsche Labels mit Umlauten (im Code bewusst ASCII)
UML = [("Ae", "Ä"), ("Ue", "Ü"), ("Oe", "Ö"), ("ae", "ä"), ("ue", "ü"), ("oe", "ö"), ("degC", "°C")]


def de(t):
    for a, b in UML:
        t = t.replace(a, b)
    return t.replace("Aussen", "Außen").replace("aussen", "außen").replace("Äussen", "Außen")


def slot(t, typ=None):
    ident, init, _de, en = t
    typ = typ or ("string" if isinstance(init, str) else "number")
    return {"type": typ, "identifier": ident, "init_value": init, "label": en}


def main():
    b = os.path.join(HERE, "build")
    shutil.rmtree(b, ignore_errors=True)
    os.makedirs(b)
    shutil.copy(os.path.join(HERE, "src", SCRIPT), b)
    hsl = "%s_%s.hsl" % (ID, SLUG)
    cfg = {"module": {
        "category": CAT_EN, "context": "ElektroRausch_14775", "id": ID, "name": NAME_EN,
        "hsl_filename": hsl, "version": VERSION,
        "inputs": [slot(i) for i in M.INPUTS],
        "outputs": [slot(o) for o in M.OUTPUTS],
        "stores": [], "timers": [],
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
    shutil.copy(GEN, b)
    subprocess.check_call([PY39, os.path.basename(GEN), "--source", "config.json", "--target", hsl], cwd=b)
    sys.path.insert(0, os.path.join(HERE, "help"))
    import make_help
    make_help.write(M, de, b, VERSION)
    hslz = os.path.join(b, "%s_%s.hslz" % (ID, SLUG))
    with zipfile.ZipFile(hslz, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(b, hsl), hsl)
        for lang in ("DE", "EN"):
            z.write(os.path.join(b, "%s-log%s.html" % (lang, ID)), "%s-log%s.html" % (lang, ID))
    os.remove(os.path.join(b, os.path.basename(GEN)))
    print("OK", hsl, hslz)


if __name__ == "__main__":
    main()
