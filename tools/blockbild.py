#!/usr/bin/env python3
"""Zeichnet einen Logikbaustein im Stil des Gira-Experten (Kopf mit ID/Name/Version,
Eingänge links, Ausgänge rechts) als SVG und PNG.

Aufruf:  blockbild.py <Bausteinordner> [<Ziel.png>]
Quelle:  Quellen/config.json (HSL3, deutsche Übersetzung) oder die .hsl (HSL 1.0, Zeile 5000).
Braucht rsvg-convert für das PNG."""
import glob, json, os, re, subprocess, sys
from xml.sax.saxutils import escape

W_PIN, ROW, HEAD, PAD = 18, 18, 40, 8
FONT = "font-family='Segoe UI, Arial, sans-serif'"


def from_config(path):
    m = json.load(open(path, encoding="utf-8"))["module"]
    tr = next((t for t in m.get("translations", []) if t.get("language") == "de"), {})
    ins = [x["label"] for x in tr.get("translation_inputs", [])] or [x["label"] for x in m["inputs"]]
    outs = [x["label"] for x in tr.get("translation_outputs", [])] or [x["label"] for x in m["outputs"]]
    vals = [x.get("init_value", "") for x in m["inputs"]]
    return tr.get("name", m["name"]), m["version"], "HSL3", ins, outs, vals


def from_hsl(path):
    t = open(path, encoding="latin-1").read()
    line = next(l for l in t.splitlines() if l.startswith("5000|"))
    parts = re.findall(r'"([^"]*)"|\|(\d+)', line)
    vals = [p[0] if p[0] else p[1] for p in parts]
    name = vals[0].split("\\")[-1]
    n_in = int(vals[2]); ins = vals[3:3 + n_in]; n_out = int(vals[3 + n_in]); outs = vals[4 + n_in:4 + n_in + n_out]
    init = {}
    for l in t.splitlines():
        m = re.match(r"5002\|(\d+)\|([^|#]*)", l)
        if m:
            init[int(m.group(1))] = m.group(2).strip().strip('"')
    ver = re.search(r"V(\d+(?:\.\d+)*)", name)
    name = re.sub(r"\s*V\d+(?:\.\d+)*$", "", name)
    return name, ver.group(1) if ver else "", "HSL 1.0", ins, outs, [init.get(i + 1, "") for i in range(n_in)]


def text_w(s, size=11):
    return sum(0.62 if c.isupper() or c in "mwMW%" else 0.52 for c in s) * size


def svg(name, ver, art, ins, outs, vals):
    lw = max([text_w(s) for s in ins] + [120]) + 14
    rw = max([text_w(s) for s in outs] + [90]) + 14
    vw = max([text_w(str(v)) for v in vals] + [24]) + 10
    head_w = text_w(name, 13) + 30
    body_w = max(lw + rw + 20, head_w)
    rows = max(len(ins), len(outs))
    x0 = PAD + vw + W_PIN
    W = x0 + body_w + W_PIN + PAD
    H = PAD + HEAD + rows * ROW + 10 + PAD
    o = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{W:.0f}' height='{H:.0f}' viewBox='0 0 {W:.0f} {H:.0f}'>",
         f"<rect width='100%' height='100%' fill='#ffffff'/>",
         f"<rect x='{x0}' y='{PAD}' width='{body_w:.0f}' height='{H - 2 * PAD:.0f}' fill='#f3f6f9' stroke='#7a8899'/>",
         f"<rect x='{x0}' y='{PAD}' width='{body_w:.0f}' height='{HEAD}' fill='#dfe7ef' stroke='#7a8899'/>",
         f"<text x='{x0 + 8}' y='{PAD + 17}' font-size='13' font-weight='600' {FONT} fill='#1d2b3a'>{escape(name)}</text>",
         f"<text x='{x0 + 8}' y='{PAD + 33}' font-size='10.5' {FONT} fill='#4a5a6b'>{escape(art)} · Version {escape(ver)}</text>"]
    y = PAD + HEAD + 4
    for i, s in enumerate(ins):
        cy = y + i * ROW + ROW / 2
        o.append(f"<line x1='{x0 - W_PIN}' y1='{cy}' x2='{x0}' y2='{cy}' stroke='#3d7a3d' stroke-width='2'/>")
        o.append(f"<rect x='{x0 + 2}' y='{cy - 7}' width='12' height='14' fill='#9fd49f'/>")
        o.append(f"<text x='{x0 + 18}' y='{cy + 4}' font-size='11' {FONT} fill='#1d2b3a'>{escape(s)}</text>")
        v = str(vals[i]) if i < len(vals) and vals[i] not in ("", None) else ""
        if v:
            o.append(f"<rect x='{x0 - W_PIN - vw}' y='{cy - 8}' width='{vw - 4:.0f}' height='16' rx='2' fill='#fff6c8' stroke='#d8c56a'/>")
            o.append(f"<text x='{x0 - W_PIN - 4 - 4}' y='{cy + 4}' text-anchor='end' font-size='10.5' {FONT} fill='#5a4a00'>{escape(v)}</text>")
    for i, s in enumerate(outs):
        cy = y + i * ROW + ROW / 2
        xr = x0 + body_w
        o.append(f"<line x1='{xr}' y1='{cy}' x2='{xr + W_PIN}' y2='{cy}' stroke='#a33' stroke-width='2'/>")
        o.append(f"<rect x='{xr - 14}' y='{cy - 7}' width='12' height='14' fill='#f0a3a3'/>")
        o.append(f"<text x='{xr - 18}' y='{cy + 4}' text-anchor='end' font-size='11' {FONT} fill='#1d2b3a'>{escape(s)}</text>")
    o.append("</svg>")
    return "\n".join(o)


def main():
    d = sys.argv[1].rstrip("/")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(d, "bilder", "baustein.png")
    cfg = os.path.join(d, "Quellen", "config.json")
    data = from_config(cfg) if os.path.exists(cfg) else from_hsl(glob.glob(os.path.join(d, "*.hsl"))[0])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    s = svg(*data)
    open(out[:-4] + ".svg", "w", encoding="utf-8").write(s)
    subprocess.run(["rsvg-convert", "-z", "2", "-o", out, out[:-4] + ".svg"], check=True)
    os.remove(out[:-4] + ".svg")
    print(out)


if __name__ == "__main__":
    main()
