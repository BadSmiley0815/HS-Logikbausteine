"""Baut 14771: .hsl (Gira-Generator, Python 3.9) aus config.json + src/, dann .hslz.
Aufruf: python build.py   (Pfade über Umgebungsvariablen HSL3_GEN / PY39 anpassen)"""
import os, shutil, subprocess, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ID, SLUG = "14771", "verlauf"
SCRIPT = "hsl3_%s_%s.py" % (ID, SLUG)
GEN = os.environ.get("HSL3_GEN", os.path.join(HERE, "generator3.cpython-39.pyc"))
PY39 = os.environ.get("PY39", "python3.9")

def main():
    b = os.path.join(HERE, "build")
    shutil.rmtree(b, ignore_errors=True); os.makedirs(b)
    shutil.copy(os.path.join(HERE, "src", SCRIPT), b)
    shutil.copy(os.path.join(HERE, "config.json"), b)
    shutil.copy(GEN, b)
    hsl = "%s_%s.hsl" % (ID, SLUG)
    subprocess.check_call([PY39, os.path.basename(GEN), "--source", "config.json", "--target", hsl], cwd=b)
    hslz = os.path.join(HERE, "..", "%s_%s.hslz" % (ID, SLUG))
    with zipfile.ZipFile(hslz, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(b, hsl), hsl)
        for lang in ("DE", "EN"):
            n = "%s-log%s.html" % (lang, ID); z.write(os.path.join(HERE, n), n)
    shutil.copy(os.path.join(b, hsl), HERE)
    shutil.rmtree(b)
    print("OK", hslz)

if __name__ == "__main__":
    main()
