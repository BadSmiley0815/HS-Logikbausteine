#!/usr/bin/env python3
"""Erzeugt README.md (Startseite) und die README je Baustein aus bausteine.json,
den Quellen (config.json bzw. .hsl) und den Bildern in <Baustein>/bilder/.
Aufruf im Repo-Ordner:  python3 tools/readmes.py"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import blockbild

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = json.load(open(os.path.join(R, "bausteine.json"), encoding="utf-8"))
B = sorted(D["bausteine"], key=lambda b: b["id"])

# Bildunterschriften je Datei (Dateiname ohne Endung)
CAPTION = {
    "beispiel_diagramm": "Ergebnis: interaktives Diagramm in der Visu (Testdaten)",
    "beispiel_verdrahtung": "Beispiel: Verdrahtung im Experten (Testprojekt mit Zufallswerten)",
    "beispiel_funktionsprinzip": "Funktionsprinzip",
    "beispiel_klappen": "Beispiel: Klappenstellungen",
    "beispiel_simulation": "Beispiel: Verlauf beim Einschalten des Verdichters (vereinfachte Simulation)",
    "beispiel_szenen": "Ergebnis: Szenen-Seite mit Beispiel-Szenen (ohne Verbindung zum HS aufgenommen)",
    "beispiel_pruefseite": "Ergebnis: Prüfseite mit zwei Testkameras – Standbild schnell nachgeladen und MJPEG-Strom",
}


def folder(b):
    f = os.path.dirname(b["datei"]) if b.get("datei") else ""
    return f if f and os.path.isdir(os.path.join(R, f)) else ""


def block_readme(b, f):
    d = os.path.join(R, f)
    cfg = os.path.join(d, "Quellen", "config.json")
    if os.path.exists(cfg):
        name, ver, art, ins, outs, _ = blockbild.from_config(cfg)
    else:
        name, ver, art, ins, outs, _ = blockbild.from_hsl(glob.glob(os.path.join(d, "*.hsl"))[0])
        if not name.startswith(str(b["id"])):
            name = f"{b['id']} {name}"
    o = [f"# {name} – Version {ver}", "", f"**ID {b['id']} · Version {ver} · {art}**", "", b["einsatz"] + ".", ""]
    if b.get("port") and isinstance(b["port"], int):
        o += [f"Der HomeServer leitet `https://<HS>/{b['pfad']}/` an den Baustein (Port {b['port']}) weiter – "
              "gleiche Adresse und gleiches Zertifikat wie der HS.", ""]
    o += ["## Baustein", "", "![Baustein](bilder/baustein.png)", ""]
    pics = sorted(p for p in glob.glob(os.path.join(d, "bilder", "beispiel_*")))
    if pics:
        o += ["## Beispiel", ""]
        for p in pics:
            key = os.path.splitext(os.path.basename(p))[0]
            cap = CAPTION.get(key, key.replace("_", " "))
            o += [f"**{cap}**", "", f"![{cap}](bilder/{os.path.basename(p)})", ""]
    if not os.path.exists(cfg):
        t = open(glob.glob(os.path.join(d, "*.hsl"))[0], encoding="latin-1").read()
        head = [l[2:] if l.startswith("# ") else l[1:] for l in t.splitlines() if l.startswith("#") and not l.startswith("####")]
        o += ["## Beschreibung (aus dem Baustein)", "", "```"] + head[1:] + ["```", ""]
    o += ["## Eingänge", ""] + [f"- {x}" for x in ins] + ["", "## Ausgänge", ""] + [f"- {x}" for x in outs] + ["", "## Dateien", ""]
    main = glob.glob(os.path.join(d, "*.hslz")) or glob.glob(os.path.join(d, "*.hsl"))
    o.append(f"- `{os.path.basename(main[0])}` – Import im Experten: Logikbausteine → Importieren")
    if os.path.exists(cfg):
        o += [f"- `Quellen/DE-log{b['id']}.html` – ausführliche Hilfe (im Experten über die Bausteinhilfe)",
              "- `Quellen/src/…py`, `Quellen/config.json` – Quellcode; die `.hsl` erzeugt der Gira-Generator (HSL3 SDK, nicht enthalten)"]
    if os.path.exists(os.path.join(d, "Anleitung_Einbau.md")):
        o.append("- [`Anleitung_Einbau.md`](Anleitung_Einbau.md) – Einbau Schritt für Schritt")
    if os.path.isdir(os.path.join(d, "WebApp")):
        o.append("- `WebApp/homeserver-webapp/` – die HTML5-Visu zum Baustein")
    o += ["", "iKOs bei Bedarf per CSV-Import anlegen: Kommunikationsobjekte → Extras → Datenabgleich → CSV-Datei synchronisieren/importieren.",
          "", "[← zur Übersicht](../README.md)", ""]
    open(os.path.join(d, "README.md"), "w", encoding="utf-8").write("\n".join(o))


used = {b["id"] for b in B}
frei = [i for i in range(14770, 14790) if i not in used]
o = ["# HS-Logikbausteine", "",
     "Freie Logikbausteine (HSL3 und HSL 1.0) für den Gira HomeServer / FacilityServer – mit Quellcode, Hilfe, Bild und Beispiel.",
     "Jeder Ordner enthält die importierbare `.hslz` bzw. `.hsl` und eine README.", "",
     "Passend dazu: [QC-Client](https://github.com/BadSmiley0815/QC-Client) – der QuadClient im Browser.", "",
     "Alle Versionen aller Bausteine: [CHANGELOG.md](CHANGELOG.md)", "",
     f"Stand {D['stand']} · ID-Bereich {D['bereich']} · nächste freie ID **{frei[0] if frei else '–'}**", "",
     "## Bausteine", "", "| ID | Baustein | Version | Port / Pfad |", "|---|---|---|---|"]
for b in B:
    f = folder(b)
    nm = f"[{b['name']}]({f}/)" if f else b["name"]
    pp = f"{b['port']} `/{b['pfad']}/`" if isinstance(b.get("port"), int) else (str(b["port"]) if b.get("port") else "")
    st = b.get("status", "")
    note = "" if f else " – " + ("noch nicht veröffentlicht" if "fehlt" in st else st)
    if pp == "?": pp = ""
    o.append(f"| {b['id']} | {nm}{note} | {b['version']} | {pp} |")
o += ["", "## Auf einen Blick", ""]
for b in B:
    f = folder(b)
    if not f:
        continue
    pics = sorted(glob.glob(os.path.join(R, f, "bilder", "beispiel_*")))
    o += [f"### [{b['id']} {b['name']}]({f}/)", "", b["einsatz"] + ".", ""]
    if pics:
        o += [f"<img src=\"{f}/bilder/{os.path.basename(pics[0])}\" width=\"640\" alt=\"{b['name']}\">", ""]
o += ["## Regeln", ""] + [f"- {r}" for r in D["regeln"]] + [
      "", "## Lizenz", "",
      "GPL-3.0, siehe [LICENSE](LICENSE). Entwickelt mit Claude (Anthropic). Gira, HomeServer und QuadClient sind Marken der "
      "Gira Giersiepen GmbH & Co. KG; dieses Projekt ist kein Produkt von Gira. Der Gira-Generator (HSL3 SDK) ist nicht enthalten.", "",
      "Bilder neu erzeugen: `python3 tools/blockbild.py <Ordner>` (Baustein), `python3 tools/prinzipbilder.py` (14776/14777), "
      "danach `python3 tools/readmes.py`.", ""]
open(os.path.join(R, "README.md"), "w", encoding="utf-8").write("\n".join(o))
for b in B:
    f = folder(b)
    if f:
        block_readme(b, f)
print("README erzeugt")
