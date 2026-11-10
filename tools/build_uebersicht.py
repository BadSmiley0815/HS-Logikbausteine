#!/usr/bin/env python3
"""Baut Logikbausteine_Uebersicht.zip aus bausteine.json (bei jeder Bausteinänderung: JSON anpassen, neu bauen).
Aufruf: build_uebersicht.py <bausteine.json> <Quellordner Logikbausteine> <Ziel.zip>"""
import csv, html, io, json, os, sys, zipfile

src, root, out = sys.argv[1:4]
D = json.load(open(src, encoding="utf-8"))
B = sorted(D["bausteine"], key=lambda b: b["id"])
used = {b["id"] for b in B}
lo, hi = 14770, 14789
frei = [i for i in range(lo, hi + 1) if i not in used]
ports = sorted([b for b in B if b.get("port")], key=lambda b: str(b["port"]))

def v(x):
    return "" if x is None else str(x)

# Markdown
md = [f"# Logikbausteine und Ports – Stand {D['stand']}", "",
      f"Eigener ID-Bereich: **{D['bereich']}** · nächste freie ID: **{frei[0] if frei else '–'}**", "",
      "## Bausteine", "", "| ID | Name | Version | Art | Port | Basis-Pfad | ex | Einsatz | Status |", "|---|---|---|---|---|---|---|---|---|"]
for b in B:
    md.append(f"| {b['id']} | {b['name']} | {v(b['version'])} | {v(b['art'])} | {v(b['port'])} | {v(b['pfad'])} | {v(b['ex'])} | {v(b['einsatz'])} | {v(b['status'])} |")
md += ["", "## Ports", "", "| Port | Baustein | Adresse |", "|---|---|---|"]
for b in ports:
    md.append(f"| {b['port']} | {b['id']} {b['name']} | {'https://<HS>/' + b['pfad'] + '/' if b['pfad'] and not b['pfad'].startswith('(') and b['pfad'] != '?' else ''} |")
md += ["", "## Freie IDs", "", ", ".join(map(str, frei)) or "keine", "", "## Regeln", ""] + [f"- {r}" for r in D["regeln"]] + [""]
md_txt = "\n".join(md)

# HTML
def row(cells, tag="td"):
    return "<tr>" + "".join(f"<{tag}>{html.escape(v(c))}</{tag}>" for c in cells) + "</tr>"
h = [f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Logikbausteine und Ports</title><style>
body{{font:14px/1.45 system-ui,Segoe UI,sans-serif;margin:24px;color:#1d1d1f;background:#fafafa}}h1{{font-size:22px}}h2{{font-size:17px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;background:#fff}}th,td{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}}th{{background:#f0f0f0}}
td:first-child{{font-weight:600;white-space:nowrap}}.hint{{color:#666}}</style></head><body>
<h1>Logikbausteine und Ports</h1><p class="hint">Stand {html.escape(D['stand'])} · Bereich {html.escape(D['bereich'])} · nächste freie ID: <b>{frei[0] if frei else '–'}</b></p>
<h2>Bausteine</h2><table>""", row(["ID", "Name", "Version", "Art", "Port", "Basis-Pfad", "ex", "Einsatz", "Status", "Datei"], "th")]
for b in B:
    h.append(row([b["id"], b["name"], b["version"], b["art"], b["port"], b["pfad"], b["ex"], b["einsatz"], b["status"], os.path.basename(b["datei"]) if b["datei"] else ""]))
h.append("</table><h2>Ports</h2><table>" + row(["Port", "Baustein", "Basis-Pfad"], "th"))
for b in ports:
    h.append(row([b["port"], f"{b['id']} {b['name']}", b["pfad"]]))
h.append(f"</table><h2>Freie IDs</h2><p>{', '.join(map(str, frei)) or 'keine'}</p><h2>Regeln</h2><ul>" +
         "".join(f"<li>{html.escape(r)}</li>" for r in D["regeln"]) + "</ul></body></html>\n")

# CSV
cb = io.StringIO(); w = csv.writer(cb, delimiter=";")
w.writerow(["ID", "Name", "Version", "Art", "Kategorie", "Port", "Basis-Pfad", "ex", "Einsatz", "Status", "Datei"])
for b in B:
    w.writerow([b["id"], b["name"], v(b["version"]), v(b["art"]), v(b["kategorie"]), v(b["port"]), v(b["pfad"]), v(b["ex"]), v(b["einsatz"]), v(b["status"]), v(b["datei"])])

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("Uebersicht.html", "".join(h))
    z.writestr("Uebersicht.md", md_txt)
    z.writestr("bausteine.csv", "﻿" + cb.getvalue())
    z.writestr("bausteine.json", json.dumps(D, ensure_ascii=False, indent=1))
    z.write(os.path.abspath(__file__), "build_uebersicht.py")   # zum Neubauen: bausteine.json ändern, Skript aufrufen
    for b in B:
        if b["datei"]:
            p = os.path.join(root, b["datei"])
            if os.path.exists(p):
                z.write(p, "bausteine/" + os.path.basename(p))
            else:
                print("fehlt:", b["datei"])
print(out, "· frei:", frei)
