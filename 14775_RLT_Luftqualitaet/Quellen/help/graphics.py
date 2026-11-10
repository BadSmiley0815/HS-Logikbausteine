"""Grafiken für die Hilfe von 14775: SVG -> PNG (Playwright) -> Data-URI.
Die .hslz darf keine Bilddateien enthalten, deshalb werden die Bilder eingebettet."""
import base64
import io
import os

from PIL import Image

INK = "#1f2a33"
MUTED = "#6b7782"
GRID = "#dfe4e8"
C_REC = "#2f6fb3"    # Umluft
C_OA = "#2e9a5a"     # Außenluft
C_EX = "#d07a16"     # Fortluft
C_FAN = "#7a4fb0"    # Ventilator
C_SUP = "#2f6fb3"
C_EXH = "#d07a16"
FONT = "font-family:Arial,Helvetica,sans-serif"

L = {
 "DE": dict(
  aq="Luftqualität", good="gut", bad="schlecht", dampers="Klappenstellung", damper_title="Klappen nach Luftqualität",
  rec="Umluft", oa="Außenluft", ex="Fortluft", fans="Ventilatoren nach Luftqualität", speed="Drehzahl",
  fan="Zu- und Abluft (Grunddrehzahl)", fc_title="Freecooling: Zuluftkorrektur", corr="Korrektur",
  dt="ΔT = Raum − Soll", ot_title="Übertemperatur mit Hysterese", ot_on="EIN", ot_off="AUS",
  ot_auto="Klappen nach Luftqualität", ot_full="100 % Außenluft", ex_title="Beispiel: Freecooling",
  sup="Zuluft", exh="Abluft", before="nach Luftqualität", after="mit Freecooling −50 %",
  ov_title="Funktionsprinzip",
  ov=dict(e1="E1 Freigabe", e2="E2 Luftqualität", e34="E3/E4 Raum / Soll", e5="E5 Außentemp.",
          gate="Anlage EIN?", gate_off="AUS: Ventilatoren 0 %,\nAU/FO-Klappe zu",
          curve="Kennlinie\nLuftqualität 0–100 %", dampers="Klappen\nUM / AU / FO",
          fan="Grunddrehzahl\nMin … Max", ot="Übertemperatur\nΔT > 1 K (Hyst.)",
          fc="Freecooling\n12 °C < Außen < Raum", corr="Zuluft-\nkorrektur",
          a35="A3–A5 Klappen", a2="A2 Abluft", a1="A1 Zuluft", a6="A6 Freigabe Temp.-Regelung",
          override="übersteuert:\n100 % Außenluft", minus="reduziert nur Zuluft")),
 "EN": dict(
  aq="Air quality", good="good", bad="bad", dampers="Damper position", damper_title="Dampers by air quality",
  rec="Recirculation", oa="Outdoor air", ex="Exhaust air", fans="Fans by air quality", speed="Speed",
  fan="Supply and exhaust (base speed)", fc_title="Free cooling: supply correction", corr="Correction",
  dt="ΔT = room − setpoint", ot_title="Overtemperature with hysteresis", ot_on="ON", ot_off="OFF",
  ot_auto="Dampers by air quality", ot_full="100 % outdoor air", ex_title="Example: free cooling",
  sup="Supply", exh="Exhaust", before="by air quality", after="with free cooling −50 %",
  ov_title="Principle of operation",
  ov=dict(e1="I1 Enable", e2="I2 Air quality", e34="I3/I4 Room / setpoint", e5="I5 Outdoor temp.",
          gate="Plant ON?", gate_off="OFF: fans 0 %,\nOA/EA dampers closed",
          curve="Curve\nair quality 0–100 %", dampers="Dampers\nREC / OA / EA",
          fan="Base speed\nmin … max", ot="Overtemperature\nΔT > 1 K (hyst.)",
          fc="Free cooling\n12 °C < outdoor < room", corr="Supply\ncorrection",
          a35="O3–O5 Dampers", a2="O2 Exhaust", a1="O1 Supply", a6="O6 Enable temp. control",
          override="overrides:\n100 % outdoor air", minus="reduces supply only")),
}


def _t(x, y, s, size=12, color=INK, anchor="start", weight="normal"):
    lines = str(s).split("\n")
    out = []
    y0 = y - (len(lines) - 1) * size * 0.6
    for i, ln in enumerate(lines):
        out.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="%s" font-weight="%s" style="%s">%s</text>'
                   % (x, y0 + i * size * 1.2, size, color, anchor, weight, FONT,
                      ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")))
    return "".join(out)


def _svg(w, h, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker></defs>'
            '<rect width="100%%" height="100%%" fill="#ffffff"/>%s</svg>' % (w, h, w, h, MUTED, body))


class Plot:
    """Einfaches xy-Diagramm."""

    def __init__(self, w, h, x0, x1, y0, y1, left=58, right=150, top=34, bottom=46):
        self.w, self.h = w, h
        self.px0, self.px1 = left, w - right
        self.py0, self.py1 = h - bottom, top
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.b = []

    def X(self, x):
        return self.px0 + (x - self.x0) / (self.x1 - self.x0) * (self.px1 - self.px0)

    def Y(self, y):
        return self.py0 + (y - self.y0) / (self.y1 - self.y0) * (self.py1 - self.py0)

    def frame(self, title, xlabel, ylabel, yticks, xticks):
        b = self.b
        b.append(_t(self.px0, 20, title, 14, INK, weight="bold"))
        for v, lab in yticks:
            y = self.Y(v)
            b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (self.px0, y, self.px1, y, GRID))
            b.append(_t(self.px0 - 8, y + 4, lab, 11, MUTED, "end"))
        for v, lab in xticks:
            x = self.X(v)
            b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (x, self.py0, x, self.py0 + 5, MUTED))
            b.append(_t(x, self.py0 + 18, lab, 11, MUTED, "middle"))
        b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (self.px0, self.py0, self.px1, self.py0, MUTED))
        b.append(_t((self.px0 + self.px1) / 2, self.h - 8, xlabel, 12, MUTED, "middle"))
        b.append('<text x="14" y="%.1f" font-size="12" fill="%s" style="%s" transform="rotate(-90 14 %.1f)" text-anchor="middle">%s</text>'
                 % ((self.py0 + self.py1) / 2, MUTED, FONT, (self.py0 + self.py1) / 2, ylabel))

    def line(self, pts, color, label=None, dash=None, width=3, label_dy=0):
        d = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", self.X(x), self.Y(y)) for i, (x, y) in enumerate(pts))
        self.b.append('<path d="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round"%s/>'
                      % (d, color, width, ' stroke-dasharray="%s"' % dash if dash else ""))
        if label:
            x, y = pts[-1]
            self.b.append(_t(self.X(x) + 8, self.Y(y) + 4 + label_dy, label, 12, color, weight="bold"))

    def dot(self, x, y, color, text=None, dx=6, dy=-8, anchor="start"):
        self.b.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (self.X(x), self.Y(y), color))
        if text:
            self.b.append(_t(self.X(x) + dx, self.Y(y) + dy, text, 11, color, anchor))

    def svg(self):
        return _svg(self.w, self.h, "".join(self.b))


def fig_dampers(lang):
    t = L[lang]
    p = Plot(660, 280, -0.25, 1.25, 0, 100)
    p.frame(t["damper_title"], t["aq"], t["dampers"] + " %",
            [(v, "%d" % v) for v in (0, 20, 40, 60, 80, 100)],
            [(0, "E6 " + t["good"] if lang == "DE" else "I6 " + t["good"]),
             (1, "E7 " + t["bad"] if lang == "DE" else "I7 " + t["bad"])])
    for x in (0, 1):
        p.b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="4 4"/>'
                   % (p.X(x), p.py0, p.X(x), p.py1, MUTED))
    p.line([(-0.25, 80), (0, 80), (1, 0), (1.25, 0)], C_REC, t["rec"] + " (E8→E9)" if lang == "DE" else t["rec"] + " (I8→I9)")
    p.line([(-0.25, 20), (0, 20), (1, 100), (1.25, 100)], C_OA, t["oa"] + " (E10→E11)" if lang == "DE" else t["oa"] + " (I10→I11)", label_dy=-8)
    p.line([(-0.25, 20), (0, 20), (1, 100), (1.25, 100)], C_EX, t["ex"] + " (E12→E13)" if lang == "DE" else t["ex"] + " (I12→I13)", dash="7 5", width=2, label_dy=10)
    p.dot(0.5, 40, C_REC, "40 %", dx=8, dy=18)
    p.dot(0.5, 60, C_OA, "60 %", dx=-8, dy=-8, anchor="end")
    return p.svg()


def fig_fans(lang):
    t = L[lang]
    p = Plot(660, 250, -0.25, 1.25, 0, 100)
    e = "E" if lang == "DE" else "I"
    p.frame(t["fans"], t["aq"], t["speed"] + " %", [(v, "%d" % v) for v in (0, 30, 60, 100)],
            [(0, e + "6 " + t["good"]), (1, e + "7 " + t["bad"])])
    for x in (0, 1):
        p.b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="4 4"/>'
                   % (p.X(x), p.py0, p.X(x), p.py1, MUTED))
    p.line([(-0.25, 30), (0, 30), (1, 100), (1.25, 100)], C_FAN, t["fan"].replace(" (", "\n("))
    p.dot(0, 30, C_FAN, e + "16 Min 30 %", dx=6, dy=18)
    p.dot(1, 100, C_FAN, e + "17 Max 100 %", dx=-8, dy=-8, anchor="end")
    return p.svg()


def fig_fc(lang):
    t = L[lang]
    e = "E" if lang == "DE" else "I"
    # links: Kennlinie, rechts: Balken-Beispiel
    p = Plot(380, 270, -1, 7, 0, 100, right=24, top=48)
    p.frame(t["fc_title"], t["dt"] + " (K)", t["corr"] + " %", [(v, "%d" % v) for v in (0, 50, 100)],
            [(v, "%d" % v) for v in range(-1, 8)])
    p.line([(-1, 0), (0, 0), (5, 100), (7, 100)], C_SUP)
    p.dot(0, 0, C_SUP, e + "19", dx=-4, dy=-10, anchor="end")
    p.dot(5, 100, C_SUP, e + "20 / " + e + "21", dx=6, dy=18)
    p.dot(2.5, 50, C_SUP, "2,5 K → 50 %" if lang == "DE" else "2.5 K → 50 %", dx=8, dy=4)
    left = "".join(p.b)
    # Balken
    bx, bw, base_y, scale = 430, 46, 210, 1.5
    b = [_t(410, 20, t["ex_title"], 14, INK, weight="bold")]
    groups = [(t["before"], 60, 60), (t["after"], 30, 60)]
    for gi, (glab, s, a) in enumerate(groups):
        x = bx + gi * 140
        for j, (val, col, lab) in enumerate(((s, C_SUP, t["sup"]), (a, C_EXH, t["exh"]))):
            xx = x + j * (bw + 8)
            h = val * scale
            b.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s" rx="2"/>' % (xx, base_y - h, bw, h, col))
            b.append(_t(xx + bw / 2, base_y - h - 6, "%d %%" % val, 12, INK, "middle", "bold"))
            b.append(_t(xx + bw / 2, base_y + 16, lab, 11, MUTED, "middle"))
        b.append(_t(x + bw + 4, base_y + 36, glab, 11, INK, "middle"))
    b.append('<line x1="420" y1="%d" x2="720" y2="%d" stroke="%s"/>' % (base_y, base_y, MUTED))
    return _svg(740, 270, left + "".join(b))


def fig_ot(lang):
    t = L[lang]
    e = "E" if lang == "DE" else "I"
    p = Plot(700, 220, -0.5, 2.0, 0, 1, left=190, right=40, top=40)
    p.frame(t["ot_title"], t["dt"] + " (K)", "", [(0, t["ot_auto"]), (1, t["ot_full"])],
            [(v, ("%.1f" % v).replace(".", "," if lang == "DE" else ".")) for v in (-0.5, 0, 0.5, 1.0, 1.5, 2.0)])
    p.px0 = p.px0  # Platz für Labels links
    # steigend (rot), fallend (blau)
    p.line([(-0.5, 0), (1.0, 0), (1.0, 1), (2.0, 1)], "#c0392b", width=3)
    p.line([(2.0, 1), (0.5, 1), (0.5, 0), (-0.5, 0)], C_REC, dash="7 5", width=3)
    p.b.append(_t(p.X(1.0) + 6, p.Y(0.5), "%s %s 1,0 K →" % (t["ot_on"], e + "14") if lang == "DE" else "%s %s 1.0 K →" % (t["ot_on"], e + "14"), 11, "#c0392b"))
    p.b.append(_t(p.X(0.5) - 6, p.Y(0.5), "← %s %s 0,5 K" % (t["ot_off"], e + "15") if lang == "DE" else "← %s %s 0.5 K" % (t["ot_off"], e + "15"), 11, C_REC, "end"))
    return p.svg()


def _box(x, y, w, h, text, fill, stroke, size=12, bold=False):
    return ('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" stroke="%s" stroke-width="1.5"/>' % (x, y, w, h, fill, stroke)
            + _t(x + w / 2, y + h / 2 + 4, text, size, INK, "middle", "bold" if bold else "normal"))


def _arrow(x1, y1, x2, y2, color=MUTED, dash=None):
    return ('<path d="M%d,%d L%d,%d" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#ar)"%s/>'
            % (x1, y1, x2, y2, color, ' stroke-dasharray="%s"' % dash if dash else ""))


def _poly(pts, color=MUTED, dash=None):
    d = " ".join("%s%d,%d" % ("M" if i == 0 else "L", x, y) for i, (x, y) in enumerate(pts))
    return ('<path d="%s" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#ar)"%s/>'
            % (d, color, ' stroke-dasharray="%s"' % dash if dash else ""))


def fig_overview(lang):
    o = L[lang]["ov"]
    IN, FN, OUT = "#eef3f8", "#fff7e8", "#eaf6ee"
    b = [_t(20, 24, L[lang]["ov_title"], 15, INK, weight="bold")]
    # Eingänge
    b.append(_box(20, 50, 150, 40, o["e1"], IN, "#8aa6c1"))
    b.append(_box(20, 130, 150, 40, o["e2"], IN, "#8aa6c1"))
    b.append(_box(20, 250, 150, 40, o["e34"], IN, "#8aa6c1"))
    b.append(_box(20, 330, 150, 40, o["e5"], IN, "#8aa6c1"))
    # Freigabe
    b.append(_box(220, 46, 150, 48, o["gate"], "#f3f0fa", "#9b86c4", bold=True))
    b.append(_arrow(170, 70, 218, 70))
    b.append(_t(392, 90, o["gate_off"].replace("\n", " "), 11, MUTED))
    # Funktionen
    b.append(_box(220, 124, 150, 52, o["curve"], FN, "#d9a75a"))
    b.append(_arrow(170, 150, 218, 150))
    b.append(_box(430, 110, 150, 46, o["dampers"], FN, "#d9a75a"))
    b.append(_box(430, 176, 150, 46, o["fan"], FN, "#d9a75a"))
    b.append(_poly([(370, 142), (400, 142), (400, 133), (428, 133)]))
    b.append(_poly([(370, 158), (400, 158), (400, 199), (428, 199)]))
    b.append(_box(220, 244, 150, 52, o["ot"], "#fdecea", "#d48a80"))
    b.append(_box(220, 324, 150, 52, o["fc"], "#e8f1fb", "#7fa7d3"))
    b.append(_arrow(170, 270, 218, 270))
    b.append(_poly([(170, 280), (195, 280), (195, 340), (218, 340)]))
    b.append(_arrow(170, 350, 218, 350))
    # Übersteuerung
    b.append(_poly([(370, 262), (412, 262), (412, 148), (428, 148)], "#c0392b", "5 4"))
    b.append(_t(422, 248, o["override"].replace("\n", " "), 11, "#c0392b"))
    # Korrektur
    b.append(_box(430, 324, 150, 52, o["corr"], "#e8f1fb", "#7fa7d3"))
    b.append(_arrow(370, 350, 428, 350, C_SUP))
    # Ausgänge
    b.append(_box(640, 110, 170, 46, o["a35"], OUT, "#79b48f"))
    b.append(_box(640, 176, 170, 40, o["a2"], OUT, "#79b48f"))
    b.append(_box(640, 236, 170, 40, o["a1"], OUT, "#79b48f"))
    b.append(_box(640, 46, 170, 48, o["a6"], OUT, "#79b48f", size=11))
    b.append(_arrow(370, 70, 638, 70))
    b.append(_arrow(580, 133, 638, 133))
    b.append(_arrow(580, 196, 638, 196))
    b.append(_poly([(580, 208), (610, 208), (610, 256), (638, 256)]))
    b.append(_poly([(580, 350), (620, 350), (620, 268), (638, 268)], C_SUP))
    b.append(_t(626, 312, o["minus"], 11, C_SUP))
    # Freigabe wirkt auf alles
    b.append(_poly([(295, 94), (295, 122)], "#9b86c4", "4 3"))
    return _svg(830, 395, "".join(b))


AMP_L = {"DE": dict(title="Ampel Luftqualität", g="grün (0)", y="gelb (1)", r="rot (2)", up="steigend",
                    down="fallend", ppm="Luftqualität (ppm)"),
         "EN": dict(title="Air quality traffic light", g="green (0)", y="yellow (1)", r="red (2)", up="rising",
                    down="falling", ppm="Air quality (ppm)")}


def fig_amp(lang):
    t = AMP_L[lang]
    e = "E" if lang == "DE" else "I"
    w, x0, x1 = 700, 80, 670
    lo, hi = 600, 1700

    def X(v):
        return x0 + (v - lo) / float(hi - lo) * (x1 - x0)
    G, Y, R = "#2e9a5a", "#e0b000", "#d0392b"
    b = [_t(x0, 22, t["title"], 14, INK, weight="bold")]
    b.append(_t(x0 - 8, 62, t["up"], 11, MUTED, "end"))
    for a, z, c in ((lo, 1000, G), (1000, 1400, Y), (1400, hi, R)):
        b.append('<rect x="%.1f" y="46" width="%.1f" height="24" fill="%s"/>' % (X(a), X(z) - X(a), c))
    b.append(_t(x0 - 8, 104, t["down"], 11, MUTED, "end"))
    for a, z, c in ((lo, 950, G), (950, 1350, Y), (1350, hi, R)):
        b.append('<rect x="%.1f" y="88" width="%.1f" height="24" fill="%s" opacity="0.75"/>' % (X(a), X(z) - X(a), c))
    for v, lab in ((1000, e + "24 = 1000"), (1400, e + "25 = 1400")):
        b.append('<line x1="%.1f" y1="40" x2="%.1f" y2="120" stroke="%s" stroke-dasharray="4 3"/>' % (X(v), X(v), INK))
        b.append(_t(X(v), 136, lab, 11, INK, "middle"))
    for v in (950, 1350):
        b.append(_t(X(v), 84, "−%s26" % e, 10, INK, "middle"))
    for v in (600, 800, 1600):
        b.append(_t(X(v), 136, str(v), 11, MUTED, "middle"))
    b.append(_t((x0 + x1) / 2, 158, t["ppm"], 12, MUTED, "middle"))
    lx = x0
    for c, lab in ((G, t["g"]), (Y, t["y"]), (R, t["r"])):
        b.append('<circle cx="%d" cy="182" r="8" fill="%s"/>' % (lx + 8, c))
        b.append(_t(lx + 22, 186, lab, 12, INK))
        lx += 130
    return _svg(w, 200, "".join(b))


FIGS = [("overview", fig_overview), ("dampers", fig_dampers), ("fans", fig_fans),
        ("ot", fig_ot), ("fc", fig_fc), ("amp", fig_amp)]


def render_all(outdir=None):
    """-> {lang: {name: data-uri}}; optional PNG-Dateien zum Ansehen."""
    from playwright.sync_api import sync_playwright
    res = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(device_scale_factor=1.5)
        for lang in L:
            res[lang] = {}
            for name, fn in FIGS:
                svg = fn(lang)
                pg.set_content('<html><body style="margin:0;background:#fff">%s</body></html>' % svg)
                png = pg.locator("svg").screenshot()
                im = Image.open(io.BytesIO(png)).convert("RGB")
                im = im.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
                buf = io.BytesIO()
                im.save(buf, "PNG", optimize=True)
                data = buf.getvalue()
                if outdir:
                    with open(os.path.join(outdir, "%s_%s.png" % (lang, name)), "wb") as f:
                        f.write(data)
                w = int(round(im.width / 1.5))
                res[lang][name] = ("data:image/png;base64," + base64.b64encode(data).decode(), w, len(data))
        br.close()
    return res


if __name__ == "__main__":
    d = "/tmp/claude-0/-home-claude/1b9b214a-ea7b-5ddb-bcea-f085df826a77/scratchpad/fig"
    os.makedirs(d, exist_ok=True)
    r = render_all(d)
    for lang in r:
        for k, (_u, w, n) in r[lang].items():
            print(lang, k, w, "px", n, "Bytes")
