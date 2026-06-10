#!/usr/bin/env python3
"""
Collecte des données d'entraînement course à pied → training_data.json

Source :
  - Intervals.icu API  : activités, FC, allures, CTL/ATL, TRIMP, wellness

Usage :
  export INTERVALS_ATHLETE_ID="882231"
  export INTERVALS_API_KEY="xxxxxxxxxxxxxxxx"
  python3 fetch_training_data.py

  # Période personnalisée :
  python3 fetch_training_data.py --start 2025-12-01 --end 2026-06-09 --out mon_fichier.json

Credentials Intervals.icu → https://intervals.icu/settings  (bas de page, section API)
"""

import os, sys, json, time, argparse
from datetime import date, datetime

try:
    import requests
except ImportError:
    sys.exit("❌  Installe d'abord les dépendances :  pip install -r requirements.txt")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
FCM_DEFAULT      = 196       # FC max (bpm) — mesuré en course
LTHR_DEFAULT     = 181       # Seuil lactate (bpm)
ACTIVITY_TYPES   = ("Run", "VirtualRun")

# ─────────────────────────────────────────────
# INTERVALS.ICU  API
# ─────────────────────────────────────────────
def _icu_session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.auth = ("API_KEY", api_key)
    s.headers.update({"User-Agent": "training-analyzer/1.0"})
    return s


def _icu_get(session: requests.Session, url: str, params: dict = None) -> dict | list:
    r = session.get(url, params=params, timeout=30)
    if r.status_code == 401:
        sys.exit("❌  Clé API invalide (401). Vérifie INTERVALS_API_KEY sur https://intervals.icu/settings")
    if r.status_code == 403:
        sys.exit("❌  Accès refusé (403). Vérifie INTERVALS_ATHLETE_ID et INTERVALS_API_KEY.")
    if r.status_code == 404:
        sys.exit(f"❌  Ressource introuvable (404) : {url}\n   Vérifie que INTERVALS_ATHLETE_ID est correct (ex: 882231, sans 'i').")
    r.raise_for_status()
    return r.json()


def fetch_activities(session, athlete_id: str, start: str, end: str) -> list[dict]:
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
    print(f"  → GET {url}")
    data = _icu_get(session, url, {"oldest": start, "newest": end})
    return data if isinstance(data, list) else data.get("activities", [])


def fetch_wellness(session, athlete_id: str, start: str, end: str) -> dict[str, dict]:
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness"
    print(f"  → GET {url}")
    records = _icu_get(session, url, {"oldest": start, "newest": end})
    if isinstance(records, list):
        return {r["id"]: r for r in records}
    return {}


def fetch_activity_intervals(session, activity_id: str) -> dict:
    """Récupère icu_groups (résumés par groupe) et icu_intervals (segments individuels).
    Retourne {} si absent ou erreur."""
    url = f"https://intervals.icu/api/v1/activity/{activity_id}/intervals"
    try:
        r = session.get(url, timeout=20)
        if r.status_code in (404, 204):
            return {}
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return {
                "groups":    data.get("icu_groups")    or [],
                "intervals": data.get("icu_intervals") or [],
            }
        return {}
    except Exception:
        return {}


def compute_zone_distribution(icu_intervals: list, lthr: int) -> dict:
    """Calcule le temps (s et %) + allure moyenne pondérée par zone FC."""
    zone_secs  = {z: 0   for z in range(1, 6)}
    zone_speed = {z: []  for z in range(1, 6)}   # liste de (durée_s, speed_m/s)
    for iv in icu_intervals:
        h = iv.get("average_heartrate")
        t = iv.get("moving_time") or iv.get("elapsed_time") or 0
        s = iv.get("average_speed")
        if h and t:
            z = hr_zone(h, lthr)
            if z:
                zone_secs[z] += int(t)
                if s and float(s) > 0:
                    zone_speed[z].append((int(t), float(s)))
    total = sum(zone_secs.values())
    if total == 0:
        return {}
    result = {
        "total_sec": total,
        **{f"z{z}_sec": zone_secs[z] for z in range(1, 6)},
        **{f"z{z}_pct": round(zone_secs[z] / total * 100, 1) for z in range(1, 6)},
    }
    # Allure moyenne pondérée par zone (secondes / km)
    for z in range(1, 6):
        pairs = zone_speed[z]
        if pairs:
            tot_t  = sum(t for t, s in pairs)
            wavg_s = sum(t * s for t, s in pairs) / tot_t if tot_t > 0 else None
            if wavg_s and wavg_s > 0:
                result[f"z{z}_pace_sec_km"] = round(1000 / wavg_s)
    return result


def extract_interval_group(groups: list, intervals: list,
                           act_hr_avg, fcm: int, lthr: int) -> dict | None:
    """Identifie le groupe d'intervalles de qualité parmi les icu_groups.

    icu_groups est déjà une liste de résumés (warmup / intervals / cooldown).
    On prend celui avec le HR max, et on le retourne seulement si son HR
    dépasse sensiblement la FC globale de la séance (+5 bpm min).
    Calcule aussi la distribution de zones à partir des segments icu_intervals.
    """
    if not groups:
        return None

    best = max(
        (g for g in groups if g.get("average_heartrate")),
        key=lambda g: float(g.get("average_heartrate", 0)),
        default=None,
    )
    if best is None:
        return None

    best_hr = float(best.get("average_heartrate", 0))
    min_hr  = (float(act_hr_avg) + 5) if act_hr_avg else 140
    if best_hr < min_hr:
        return None

    t = best.get("moving_time") or best.get("elapsed_time") or 0
    d = best.get("distance") or 0
    pace_sec = round(t / (d / 1000)) if d > 0 else None

    result = {
        "hr_avg":          int(round(best_hr)),
        "hr_pct_fcm":      round(best_hr / fcm * 100, 1),
        "pace_sec_per_km": pace_sec,
        "duration_sec":    int(t) if t else None,
        "label":           str(best.get("id") or "interval"),
        "reps":            best.get("count"),
    }
    # Distribution zones FC sur toute la séance (échauff + intervals + récup)
    zdist = compute_zone_distribution(intervals, lthr)
    if zdist:
        result["zone_distribution"] = zdist
    return result


# ─────────────────────────────────────────────
# ZONES FC
# ─────────────────────────────────────────────
def hr_zone(hr, lthr: int = LTHR_DEFAULT) -> int | None:
    if hr is None: return None
    p = hr / lthr
    if p < 0.70: return 1
    if p < 0.82: return 2
    if p < 0.89: return 3
    if p < 0.97: return 4
    return 5

# ─────────────────────────────────────────────
# ASSEMBLAGE  d'un record JSON par activité
# ─────────────────────────────────────────────
def build_record(act: dict, wellness: dict,
                 fcm: int, lthr: int, interval_data: dict = None) -> dict:
    act_date = (act.get("start_date_local") or act.get("start_date", ""))[:10]
    w  = wellness.get(act_date, {})

    moving_s = act.get("moving_time") or act.get("elapsed_time") or 0
    dist_m   = act.get("distance") or 0
    dist_km  = round(dist_m / 1000, 3) if dist_m else None
    pace_sec = round(moving_s / (dist_m / 1000)) if dist_m else None

    hr_avg  = act.get("average_heartrate") or act.get("avg_hr")
    hr_max  = act.get("max_heartrate")     or act.get("max_hr")
    hr_pct  = round(hr_avg / fcm * 100, 1) if hr_avg else None

    # CTL / ATL depuis wellness si absent de l'activité
    ctl = act.get("ctl") or w.get("ctl")
    atl = act.get("atl") or w.get("atl")

    return {
        "id":    act.get("id"),
        "date":  act_date,
        "name":  act.get("name", ""),
        "type":  act.get("type") or act.get("sport_type", ""),

        "distance_km":  dist_km,
        "duration_min": round(moving_s / 60, 1) if moving_s else None,
        "elevation_m":  act.get("total_elevation_gain"),
        "cadence":      act.get("average_cadence"),
        "weight_kg":    act.get("athlete_weight"),

        "pace_raw_sec_per_km": pace_sec,
        "speed_ms":            round(act.get("average_speed", 0) or 0, 3) or None,

        "hr_avg":      int(hr_avg) if hr_avg else None,
        "hr_max":      int(hr_max) if hr_max else None,
        "hr_pct_fcm":  hr_pct,
        "hr_zone":     hr_zone(int(hr_avg) if hr_avg else None, lthr),
        "fcm":         fcm,
        "lthr":        lthr,

        "ctl":      ctl,
        "atl":      atl,
        "form":     round(ctl - atl, 2) if ctl and atl else None,
        "trimp":    act.get("trimp") or act.get("hr_load"),
        "intensity": act.get("intensity"),
        "rpe":      act.get("perceived_exertion"),

        "hrv":       w.get("hrv") or w.get("hrvSDNN"),
        "resting_hr": w.get("restingHR"),
        "sleep_h":   round(w["sleepSecs"] / 3600, 2) if w.get("sleepSecs") else w.get("sleep"),
        "vo2max":    w.get("vo2max"),

        # Groupe d'intervalles de qualité (None si sortie facile ou --fetch-intervals non utilisé)
        "interval_data": interval_data,
    }

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Collecte données entraînement → JSON")
    p.add_argument("--start",    default="2025-12-01")
    p.add_argument("--end",      default=date.today().isoformat())
    p.add_argument("--out",      default="training_data.json")
    p.add_argument("--fcm",      type=int, default=FCM_DEFAULT)
    p.add_argument("--lthr",     type=int, default=LTHR_DEFAULT)
    p.add_argument("--fetch-intervals", action="store_true",
                   help="Télécharger les données d'intervalles (~0.2s/activité)")
    args = p.parse_args()

    athlete_id = os.environ.get("INTERVALS_ATHLETE_ID", "").strip()
    api_key    = os.environ.get("INTERVALS_API_KEY",    "").strip()

    if not athlete_id or not api_key:
        print("❌  Variables d'environnement manquantes.\n")
        print("   Sur Linux/Mac :")
        print('     export INTERVALS_ATHLETE_ID="882231"')
        print('     export INTERVALS_API_KEY="ton_api_key"')
        print("\n   Sur Windows (PowerShell) :")
        print('     $env:INTERVALS_ATHLETE_ID="882231"')
        print('     $env:INTERVALS_API_KEY="ton_api_key"')
        print("\n   Clé API → https://intervals.icu/settings (bas de page, section API)")
        sys.exit(1)

    print(f"\n📥 Collecte : {args.start} → {args.end}  |  athlète {athlete_id}\n")

    session = _icu_session(api_key)

    print("1/3  Activités…")
    all_acts = fetch_activities(session, athlete_id, args.start, args.end)
    runs = [a for a in all_acts if a.get("type") in ACTIVITY_TYPES]
    print(f"     {len(all_acts)} activités | {len(runs)} runs/virtual runs")

    print("\n2/3  Wellness…")
    wellness = fetch_wellness(session, athlete_id, args.start, args.end)
    print(f"     {len(wellness)} jours")

    interval_map = {}
    if args.fetch_intervals:
        n_total = len(runs)
        print(f"\n3/3  Intervalles ({n_total} activités)…")
        for i, act in enumerate(runs, 1):
            act_id = act.get("id")
            if act_id:
                raw    = fetch_activity_intervals(session, str(act_id))
                act_hr = act.get("average_heartrate") or act.get("avg_hr")
                interval_map[act_id] = extract_interval_group(
                    raw.get("groups", []), raw.get("intervals", []),
                    act_hr, args.fcm, args.lthr,
                )
            if i % 20 == 0 or i == n_total:
                print(f"     {i}/{n_total}")
            time.sleep(0.2)
        n_iv = sum(1 for v in interval_map.values() if v is not None)
        print(f"     {n_iv} workouts avec groupe d'intervalles identifié")
    else:
        print("\n3/3  Intervalles ignorés (ajoute --fetch-intervals pour les inclure)")

    print("\n🔧 Assemblage…")
    records = [build_record(a, wellness, args.fcm, args.lthr,
                            interval_map.get(a.get("id")))
               for a in sorted(runs, key=lambda a: (a.get("start_date_local") or a.get("start_date", "")))]

    n_intervals = sum(1 for r in records if r.get("interval_data"))

    # Timeline wellness : une entrée par jour avec données HRV / FC repos / sommeil
    wellness_timeline = []
    for d, w in sorted(wellness.items()):
        hrv = w.get("hrv") or w.get("hrvSDNN")
        rhr = w.get("restingHR")
        slp = round(w["sleepSecs"] / 3600, 2) if w.get("sleepSecs") else w.get("sleep")
        ctl = w.get("ctl")
        atl = w.get("atl")
        if any(v is not None for v in (hrv, rhr, slp, ctl, atl)):
            wellness_timeline.append({
                "date":        d,
                "hrv":         hrv,
                "resting_hr":  rhr,
                "sleep_h":     slp,
                "ctl":         ctl,
                "atl":         atl,
                "form":        round(ctl - atl, 2) if ctl and atl else None,
            })

    n_hrv = sum(1 for w in wellness_timeline if w["hrv"] is not None)

    output = {
        "meta": {
            "generated_at":      datetime.now().isoformat(),
            "athlete_id":        athlete_id,
            "period_start":      args.start,
            "period_end":        args.end,
            "total_runs":        len(records),
            "with_intervals":    n_intervals,
            "with_hrv":          n_hrv,
            "fcm_bpm":           args.fcm,
            "lthr_bpm":          args.lthr,
        },
        "activities":        records,
        "wellness_timeline": wellness_timeline,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ {args.out}")
    print(f"   {len(records)} runs  |  {n_intervals} intervalles  |  {n_hrv} jours HRV")


if __name__ == "__main__":
    main()
