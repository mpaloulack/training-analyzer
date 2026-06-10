#!/usr/bin/env python3
"""
Graphiques d'analyse entraînement à partir de training_data.json

Graphiques générés :
  1. %FCM vs Allure ajustée — coloré par température
  2. %FCM vs Allure ajustée — coloré par vent (km/h)
  3. Scatter allure brute vs ajustée avec delta environnemental
  4. Évolution mensuelle : CTL/ATL/Forme
  5. Bubble chart : date × allure ajustée, taille = TRIMP, couleur = %FCM

Usage :
  python3 plot_training.py training_data.json
  python3 plot_training.py training_data.json --out ./graphs/
"""

import json, sys, os, argparse
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.dates as mdates
import numpy as np

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def pace_label(sec: int | None) -> str:
    if sec is None: return "N/A"
    return f"{sec//60}:{sec%60:02d}"

def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def to_dt(d: str) -> datetime:
    return datetime.strptime(d[:10], "%Y-%m-%d")

def filter_runs(acts: list[dict], min_dist_km: float = 3.0) -> list[dict]:
    """Exclut les très courtes sorties (échauffements isolés, etc.)."""
    return [a for a in acts if (a.get("distance_km") or 0) >= min_dist_km
            and a.get("hr_avg") and a.get("pace_raw_sec_per_km")]

# ──────────────────────────────────────────────
# GRAPHIQUE 1 & 2  — %FCM vs allure ajustée
# ──────────────────────────────────────────────
def plot_fcm_vs_pace(runs: list[dict], out_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("%FCM vs Allure ajustée (Enduraw)", fontsize=14, fontweight="bold")

    for ax, color_field, cmap_name, clabel, fname in [
        (axes[0], "env_temp_c",  "RdYlBu_r", "Température (°C)",     "fcm_vs_pace_temp.png"),
        (axes[1], "env_wind_kmh","coolwarm",  "Vent estimé (km/h)",   "fcm_vs_pace_vent.png"),
    ]:
        x_raw       = []   # allure brute  (min/km)
        x_adj       = []   # allure ajustée (min/km)
        y           = []   # %FCM
        c_vals      = []   # couleur
        labels      = []   # nom séance
        is_race     = []   # booléen course
        is_interval = []   # booléen: données issues du groupe d'intervalles

        for r in runs:
            iv = r.get("interval_data")
            pace_raw = r.get("pace_raw_sec_per_km")
            if iv and iv.get("pace_sec_per_km"):
                pace_adj = iv["pace_sec_per_km"]
                hr_pct   = iv.get("hr_pct_fcm")
            else:
                pace_adj = r.get("pace_adj_sec_per_km") or pace_raw
                hr_pct   = r.get("hr_pct_fcm")
            c_val = r.get(color_field)

            if pace_adj is None or hr_pct is None or c_val is None:
                continue

            x_raw.append((pace_raw or pace_adj) / 60)
            x_adj.append(pace_adj / 60)
            y.append(hr_pct)
            c_vals.append(c_val)
            labels.append(r.get("name", "")[:20])
            name_l = (r.get("name", "")).lower()
            is_race.append("course" in name_l or "lcdc" in name_l or "rp" in name_l)
            is_interval.append(iv is not None and iv.get("pace_sec_per_km") is not None)

        if not x_adj:
            ax.text(0.5, 0.5, "Données insuffisantes", ha="center", va="center",
                    transform=ax.transAxes)
            continue

        c_arr = np.array(c_vals)
        norm = mcolors.Normalize(vmin=c_arr.min(), vmax=c_arr.max())

        def _pick(lst, idxs):
            return [lst[i] for i in idxs]

        idx_norm = [i for i, (rc, iv) in enumerate(zip(is_race, is_interval)) if not rc and not iv]
        idx_iv   = [i for i, (rc, iv) in enumerate(zip(is_race, is_interval)) if not rc and iv]
        idx_race = [i for i, rc in enumerate(is_race) if rc]

        if idx_norm:
            sc = ax.scatter(_pick(x_adj, idx_norm), _pick(y, idx_norm),
                            c=_pick(c_vals, idx_norm), cmap=cmap_name, norm=norm,
                            s=80, alpha=0.8, edgecolors="k", linewidths=0.4,
                            label="Sortie facile/tempo")
        if idx_iv:
            ax.scatter(_pick(x_adj, idx_iv), _pick(y, idx_iv),
                       c=_pick(c_vals, idx_iv), cmap=cmap_name, norm=norm,
                       s=120, marker="D", alpha=0.9, edgecolors="white", linewidths=0.8,
                       zorder=4, label="Intervalles (portion seulement)")
        if idx_race:
            ax.scatter(_pick(x_adj, idx_race), _pick(y, idx_race),
                       c=_pick(c_vals, idx_race), cmap=cmap_name, norm=norm,
                       s=300, marker="*", edgecolors="gold", linewidths=1.5, zorder=5,
                       label="Course")
        ax.legend(fontsize=8, loc="lower right")

        # Zones FC horizontales (% FCM = 196, LTHR = 181)
        for pct, lbl, col in [(65, "Z1/Z2", "gray"), (75.5, "Z2/Z3", "blue"),
                               (82, "Z3/Z4", "orange"), (89.3, "Z4/Z5", "red")]:
            ax.axhline(pct, color=col, linestyle="--", linewidth=0.7, alpha=0.5)
            ax.text(ax.get_xlim()[0] if ax.get_xlim()[0] != 0 else 3.0,
                    pct + 0.3, lbl, fontsize=7, color=col)

        plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap_name), ax=ax, label=clabel)
        ax.set_xlabel("Allure ajustée (min/km)", fontsize=11)
        ax.set_ylabel("%FCM", fontsize=11)
        ax.invert_xaxis()   # plus rapide = droite
        ax.set_title(clabel, fontsize=11)
        ax.grid(True, alpha=0.3)

        # Ticks allure lisibles
        x_ticks = np.arange(3, 7, 0.5)
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f"{int(t)}:{int((t%1)*60):02d}" for t in x_ticks])

    plt.tight_layout()
    path = os.path.join(out_dir, "1_fcm_vs_allure.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  ✓ {path}")
    plt.close()


# ──────────────────────────────────────────────
# GRAPHIQUE 3  — Delta allure brute vs ajustée
# ──────────────────────────────────────────────
def plot_pace_delta(runs: list[dict], out_dir: str):
    """
    Montre le 'coût' environnemental de chaque séance :
    delta = allure brute - allure ajustée (en sec/km)
    Coloré par température, taille = distance.
    """
    dates, deltas, temps, dists, names = [], [], [], [], []

    for r in runs:
        p_raw = r.get("pace_raw_sec_per_km")
        p_adj = r.get("pace_adj_sec_per_km")
        t     = r.get("env_temp_c")
        d     = r.get("distance_km") or 5

        if p_raw is None or p_adj is None or t is None:
            continue
        delta = p_raw - p_adj   # positif = conditions difficiles (plus lent que si conditions idéales)
        dates.append(to_dt(r["date"]))
        deltas.append(delta)
        temps.append(t)
        dists.append(d)
        names.append(r.get("name", "")[:25])

    if not dates:
        print("  ⚠ Pas assez de données Enduraw pour graphique 3")
        return

    fig, ax = plt.subplots(figsize=(14, 6))
    norm = mcolors.Normalize(vmin=min(temps), vmax=max(temps))
    sc = ax.scatter(dates, deltas, c=temps, cmap="RdYlBu_r", norm=norm,
                    s=[d * 3 for d in dists], alpha=0.8, edgecolors="k", linewidths=0.4)
    plt.colorbar(sc, ax=ax, label="Température (°C)")
    ax.axhline(0, color="black", linewidth=1)
    ax.axhline(10, color="orange", linestyle="--", linewidth=0.8, alpha=0.7, label="+10s/km (conditions difficiles)")
    ax.axhline(-5, color="green", linestyle="--", linewidth=0.8, alpha=0.7, label="-5s/km (conditions favorables)")

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Δ allure brute − ajustée (s/km)\n(+ = conditions difficiles)", fontsize=10)
    ax.set_title("Coût environnemental par séance (taille = distance)", fontsize=13, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=30)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    path = os.path.join(out_dir, "2_delta_allure_env.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  ✓ {path}")
    plt.close()


# ──────────────────────────────────────────────
# GRAPHIQUE 4  — CTL / ATL / Forme
# ──────────────────────────────────────────────
def plot_ctl(acts: list[dict], wellness: list[dict], out_dir: str):
    """CTL / ATL / Forme + HRV (VFC) sur la même timeline."""
    # CTL/ATL depuis wellness timeline (couverture quotidienne)
    seen = {}
    for w in wellness:
        d = w.get("date", "")
        if d and w.get("ctl") is not None:
            seen[d] = w
    # Compléter avec les activités si wellness manquant
    for r in acts:
        d = r.get("date", "")
        if d and d not in seen and r.get("ctl") is not None:
            seen[d] = r

    dates = sorted(seen.keys())
    ctls  = [seen[d]["ctl"]  for d in dates]
    atls  = [seen[d]["atl"]  for d in dates]
    forms = [seen[d]["form"] for d in dates]
    dts   = [to_dt(d) for d in dates]

    # HRV depuis wellness timeline
    hrv_pairs = [(to_dt(w["date"]), float(w["hrv"])) for w in wellness if w.get("hrv") is not None]
    hrv_dts   = [p[0] for p in hrv_pairs]
    hrv_vals  = [p[1] for p in hrv_pairs]
    has_hrv   = len(hrv_vals) >= 3

    n_panels = 3 if has_hrv else 2
    heights  = [3, 2, 2] if has_hrv else [3, 2]
    fig, axes = plt.subplots(n_panels, 1, figsize=(14, 4 * n_panels + 1),
                             sharex=True, gridspec_kw={"height_ratios": heights})
    ax1, ax2 = axes[0], axes[1]
    ax3 = axes[2] if has_hrv else None
    fig.suptitle("Évolution CTL / ATL / Forme / VFC", fontsize=14, fontweight="bold")

    ax1.plot(dts, ctls, "b-", linewidth=2, label="CTL (Fitness)")
    ax1.plot(dts, atls, "r-", linewidth=2, label="ATL (Fatigue)")
    ax1.fill_between(dts, ctls, atls,
                     where=[a > c for a, c in zip(atls, ctls)],
                     color="red", alpha=0.15, label="Surcharge")
    race_dates = [to_dt(r["date"]) for r in acts if "lcdc" in r.get("name","").lower() or
                  ("course" in r.get("name","").lower() and r.get("distance_km", 0) < 7)]
    for rd in race_dates:
        ax1.axvline(rd, color="gold", linestyle="--", linewidth=2)
    ax1.set_ylabel("CTL / ATL", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(max(0, min(ctls + atls) - 5), max(ctls + atls) + 5)

    colors_form = ["green" if f and f >= 0 else "red" for f in forms]
    ax2.bar(dts, forms, color=colors_form, alpha=0.7, width=1.2)
    ax2.axhline(0,   color="black",  linewidth=0.8)
    ax2.axhline(-10, color="orange", linestyle="--", linewidth=0.8, alpha=0.6, label="Limite surcharge (−10)")
    ax2.axhline(5,   color="green",  linestyle="--", linewidth=0.8, alpha=0.6, label="Zone peak form (+5)")
    for rd in race_dates:
        ax2.axvline(rd, color="gold", linestyle="--", linewidth=2)
    ax2.set_ylabel("Forme (CTL − ATL)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    if has_hrv and ax3 is not None:
        ax3.scatter(hrv_dts, hrv_vals, s=18, color="purple", alpha=0.5, zorder=3, label="HRV (VFC)")
        # Moyenne mobile 7 jours
        if len(hrv_vals) >= 7:
            window = 7
            roll = np.convolve(hrv_vals, np.ones(window) / window, mode="valid")
            ax3.plot(hrv_dts[window - 1:], roll, color="purple", linewidth=2,
                     label="Moy. 7 jours", zorder=4)
        for rd in race_dates:
            ax3.axvline(rd, color="gold", linestyle="--", linewidth=2)
        ax3.set_ylabel("HRV / VFC (ms)", fontsize=11)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.3)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=30)

    path = os.path.join(out_dir, "3_ctl_atl_forme.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  ✓ {path}")
    plt.close()


# ──────────────────────────────────────────────
# GRAPHIQUE 5  — Bubble chart date × allure adj
# ──────────────────────────────────────────────
def plot_bubble(runs: list[dict], out_dir: str):
    """
    X = date, Y = allure ajustée (min/km), taille = TRIMP, couleur = %FCM.
    Permet de voir d'un coup l'intensité ET la charge de chaque séance.
    """
    dts, paces, trimps, fcm_pcts = [], [], [], []

    for r in runs:
        p = r.get("pace_adj_sec_per_km") or r.get("pace_raw_sec_per_km")
        t = r.get("trimp") or 50
        h = r.get("hr_pct_fcm")
        if p is None or h is None:
            continue
        dts.append(to_dt(r["date"]))
        paces.append(p / 60)
        trimps.append(max(t, 20))
        fcm_pcts.append(h)

    if not dts:
        return

    fig, ax = plt.subplots(figsize=(15, 7))
    norm = mcolors.Normalize(vmin=65, vmax=100)
    sc = ax.scatter(dts, paces, c=fcm_pcts, cmap="YlOrRd", norm=norm,
                    s=[t * 2 for t in trimps], alpha=0.75, edgecolors="k", linewidths=0.4)
    plt.colorbar(sc, ax=ax, label="%FCM")

    ax.invert_yaxis()  # allure rapide en haut
    ax.set_ylabel("Allure ajustée (min/km)", fontsize=11)
    ax.set_xlabel("Date", fontsize=11)
    ax.set_title("Séances : allure × date — taille = TRIMP, couleur = %FCM", fontsize=13, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())

    # Axe Y en format mm:ss
    y_ticks = np.arange(3, 7, 0.5)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{int(t)}:{int((t%1)*60):02d}" for t in y_ticks])

    plt.xticks(rotation=30)
    ax.grid(True, alpha=0.3)

    # Légende taille
    for sz, lbl in [(40, "TRIMP 20"), (100, "50"), (200, "100"), (400, "200")]:
        ax.scatter([], [], s=sz, c="gray", alpha=0.5, label=lbl, edgecolors="k", linewidths=0.4)
    ax.legend(title="TRIMP", fontsize=8, title_fontsize=9, loc="upper right")

    path = os.path.join(out_dir, "4_bubble_seances.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  ✓ {path}")
    plt.close()


# ──────────────────────────────────────────────
# GRAPHIQUE 5  — Distribution zones FC par séance d'interval
# ──────────────────────────────────────────────
ZONE_COLORS = ["#81C784", "#42A5F5", "#FFA726", "#EF5350", "#AB47BC"]
ZONE_NAMES  = ["Z1", "Z2", "Z3", "Z4", "Z5"]

def plot_zone_distribution(runs: list[dict], out_dir: str):
    """Barres horizontales empilées : temps par zone pour chaque séance d'intervalles.
    Permet de voir la vraie polarisation au lieu de la FC moyenne globale."""
    wk_runs = sorted(
        [r for r in runs if r.get("interval_data") and
         r["interval_data"].get("zone_distribution")],
        key=lambda r: r["date"],
    )
    if not wk_runs:
        print("  ⚠ Pas de données zone distribution (--fetch-intervals requis)")
        return

    labels = [f"{r['date'][5:]}  {r.get('name','')[:22]}" for r in wk_runs]

    fig, ax = plt.subplots(figsize=(14, max(4, len(wk_runs) * 0.55 + 2)))
    fig.suptitle("Distribution zones FC — séances d'intervalles\n(échauff. + répétitions + récup.)",
                 fontsize=13, fontweight="bold")

    lefts = [0.0] * len(wk_runs)
    for z, (col, zname) in enumerate(zip(ZONE_COLORS, ZONE_NAMES), 1):
        pcts = [r["interval_data"]["zone_distribution"].get(f"z{z}_pct", 0) for r in wk_runs]
        bars = ax.barh(labels, pcts, left=lefts, color=col, label=zname, alpha=0.88, height=0.6)
        for bar, pct, r in zip(bars, pcts, wk_runs):
            if pct < 5:
                continue
            zdist    = r["interval_data"]["zone_distribution"]
            pace     = zdist.get(f"z{z}_pace_sec_km")
            cx = bar.get_x() + bar.get_width() / 2
            cy = bar.get_y() + bar.get_height() / 2
            if pace and pct >= 12:
                pace_str = f"{pace//60}:{pace%60:02d}"
                ax.text(cx, cy + 0.12, f"{pct:.0f}%",
                        ha="center", va="center", fontsize=7, color="white", fontweight="bold")
                ax.text(cx, cy - 0.13, pace_str,
                        ha="center", va="center", fontsize=6.5, color="white", alpha=0.9)
            else:
                ax.text(cx, cy, f"{pct:.0f}%",
                        ha="center", va="center", fontsize=7.5, color="white", fontweight="bold")
        lefts = [l + p for l, p in zip(lefts, pcts)]

    ax.set_xlabel("% du temps total de séance", fontsize=11)
    ax.set_xlim(0, 100)
    ax.axvline(80, color="gray", linestyle="--", linewidth=1, alpha=0.6,
               label="80% Z1-Z2 (polarisé)")
    ax.legend(loc="lower right", fontsize=9, ncol=6)
    ax.grid(True, axis="x", alpha=0.3)
    ax.invert_yaxis()
    plt.tight_layout()

    path = os.path.join(out_dir, "5_zones_intervals.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  ✓ {path}")
    plt.close()


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", default="training_data.json")
    parser.add_argument("--out", default=".", help="Dossier de sortie pour les images")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print(f"\n📊 Chargement de {args.json_file}…")
    data = load(args.json_file)
    acts = data.get("activities", [])
    runs = filter_runs(acts)

    meta     = data.get("meta", {})
    wellness = data.get("wellness_timeline", [])
    print(f"   {meta.get('total_runs')} runs | Enduraw: {meta.get('with_enduraw')} | ECCC: {meta.get('with_eccc_weather')} | Intervalles: {meta.get('with_intervals', 'N/A')} | HRV: {meta.get('with_hrv', 'N/A')} jours")
    print(f"\n🎨 Génération des graphiques dans {args.out}/\n")

    plot_fcm_vs_pace(runs, args.out)
    plot_pace_delta(runs, args.out)
    plot_ctl(acts, wellness, args.out)
    plot_bubble(runs, args.out)
    plot_zone_distribution(runs, args.out)

    print(f"\n✅ 4 graphiques générés dans {args.out}/")
    print("   1_fcm_vs_allure.png   — %FCM vs allure (temp & vent)")
    print("   2_delta_allure_env.png — coût environnemental/séance")
    print("   3_ctl_atl_forme.png   — forme / fatigue / fitness")
    print("   4_bubble_seances.png  — vue d'ensemble intensité × charge")


if __name__ == "__main__":
    main()
