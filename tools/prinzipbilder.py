#!/usr/bin/env python3
"""Prinzipbilder für die Formelbausteine 14776 und 14777 (vereinfachte Simulation / Darstellung der Zuordnung)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, GREEN, GREY, RED = "#2a6fb0", "#d9822b", "#3a9a4a", "#7a8899", "#b03a2e"

def wrg(out):
    # 14776 – Standardwerte: Soll 80 °C, Kp 3 %/K, Tn 300 s, Min 15 %, Max 100 %, Rampe auf 5 %/min, ab 20 %/min, Filter 60 s
    dt = 1.0; sp, kp, tn, mn, mx, up, dn, tf = 80, 3, 300, 15, 100, 5, 20, 60
    T, Tf, y, I, active = 40.0, 40.0, 0.0, 0.0, False
    ts, Ts, ys, acts = [], [], [], []
    for k in range(int(100 * 60)):
        t = k * dt; on = 5 * 60 <= t < 85 * 60
        heat = 9.0 if on else 0.0                        # Abwärme des Verdichters (Modell)
        T += dt * (heat - 0.0065 * y * (T - 30) - 0.002 * (T - 20)) / 60
        Tf += dt / tf * (T - Tf)
        if not on:
            y, I, active = 0.0, 0.0, False
        else:
            if not active and Tf >= sp: active = True
            if not active: target = mn
            else:
                e = Tf - sp
                I_new = I + kp * e * dt / tn
                target = kp * e + I_new + mn
                lim = max(mn, min(mx, target))
                if abs(lim - target) < 1e-9: I = I_new
                target = lim
            step_up, step_dn = up / 60 * dt, dn / 60 * dt
            y = mn if y < mn else y
            y = min(target, y + step_up) if target > y else max(target, y - step_dn)
        ts.append(t / 60); Ts.append(Tf); ys.append(y); acts.append(active)
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=130)
    ax.plot(ts, Ts, color=RED, lw=2, label="Istwert Vorlauf (gefiltert, A4)")
    ax.axhline(sp, color=GREY, ls="--", lw=1); ax.text(55, sp + 2, "Soll 80 °C (E4)", color=GREY)
    ax.set_ylabel("°C"); ax.set_xlabel("Minuten"); ax.set_ylim(20, 100)
    a2 = ax.twinx(); a2.plot(ts, ys, color=BLUE, lw=2, label="Stellwert Pumpe (A1)"); a2.set_ylim(0, 105); a2.set_ylabel("%")
    a2.spines["top"].set_visible(False)
    a2.axvspan(5, 85, color="#eef3f8", zorder=0)
    ax.set_zorder(a2.get_zorder() + 1); ax.patch.set_visible(False); a2.patch.set_visible(True)
    first = next(i for i, a in enumerate(acts) if a)
    a2.annotate("Soll erreicht → Regelung aktiv (A2 = 1)", (ts[first], ys[first]), (ts[first] + 4, 70), arrowprops={"arrowstyle": "->", "color": GREY}, color="#333")
    a2.text(6, 18, "Mindestdrehzahl 15 %", color=BLUE); a2.text(86, 50, "Verdichter\naus → 0 %", color=GREY)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    ax.set_title("14776 – Verdichter läuft von Minute 5 bis 85 (vereinfachte Simulation)", loc="left", fontsize=11)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)

def klappen(out):
    names = ["M1 Kanal 1\naußen", "M2 Kanal 1\ninnen", "M3 Kanal 2\naußen", "M4\nUmluft", "M5\nLager", "M6 Fenster\naußen", "M7\nFenster"]
    sommer = [100, 0, 100, 0, 0, 100, 100]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), dpi=130, gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axs[0]; x = range(7)
    ax.bar([i - 0.2 for i in x], sommer, 0.4, color=ORANGE, label="Sommer (feste Vorgaben E14–E20)")
    y1, y4 = 40, 70
    winter = [100 - y4, y4, 0, y1, 50, 100 - y1, 100 - y1]
    ax.bar([i + 0.2 for i in x], winter, 0.4, color=BLUE, label=f"Winter (Beispiel: Regler Kompressorraum {y1} %, Halle {y4} %)")
    ax.set_xticks(list(x)); ax.set_xticklabels(names, fontsize=8.5); ax.set_ylabel("Klappenstellung %"); ax.set_ylim(0, 118)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left"); ax.set_title("Klappen im Sommer und im Winter", loc="left", fontsize=11)
    ax = axs[1]; r = [0, 100]
    ax.plot(r, r, color=BLUE, lw=2.2, label="M4 Umluft = y1"); ax.plot(r, [100, 0], color=BLUE, lw=2.2, ls="--", label="M6 = M7 = 100 − y1")
    from matplotlib.lines import Line2D
    ax.set_xlabel("Stellgröße Regler (y1 bzw. y4) %"); ax.set_ylabel("Klappenstellung %")
    h, l = ax.get_legend_handles_labels()
    h += [Line2D([], [], color=GREEN, lw=2.2), Line2D([], [], color=GREEN, lw=2.2, ls="--")]
    l += ["M2 innen = y4 (Regler Halle)", "M1 außen = 100 − y4"]
    ax.legend(h, l, frameon=True, framealpha=0.95, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2); ax.set_title("Winter: PI-Regler führen die Klappen", loc="left", fontsize=11, pad=48)
    fig.text(0.01, 0.01, "Sommer/Winter: Mittel der Außentemperatur (T7 + T14 + 2·T22)/4 ≥ E4 → Sommer. Werte und Stellungen sind Standardwerte bzw. ein Beispiel.", fontsize=8.5, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(out); plt.close(fig)

if __name__ == "__main__":
    import sys, os
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    wrg(os.path.join(root, "14776_WRG_Pumpenregelung/bilder/beispiel_simulation.png"))
    klappen(os.path.join(root, "14777_Kompressor_Klappensteuerung/bilder/beispiel_klappen.png"))
    print("ok")
