#!/usr/bin/env python3
"""Diagnostic: trouve le bon endpoint API pour les intervalles d'une activité."""
import os, sys, json
try:
    import requests
except ImportError:
    sys.exit("pip install requests")

api_key    = os.environ.get("INTERVALS_API_KEY", "").strip()
athlete_id = os.environ.get("INTERVALS_ATHLETE_ID", "").strip()
if not api_key or not athlete_id:
    sys.exit("❌ INTERVALS_API_KEY et INTERVALS_ATHLETE_ID requis")

s = requests.Session()
s.auth = ("API_KEY", api_key)

ACT_ID  = "i155088440"  # 7*1400
ACT_NUM = ACT_ID.lstrip("i")  # 155088440

CANDIDATES = [
    # Variantes avec / sans préfixe "i", sous-ressources possibles
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities/{ACT_ID}/intervals",
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities/{ACT_NUM}/intervals",
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities/{ACT_ID}/laps",
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities/{ACT_NUM}/laps",
    # Activité complète (peut contenir des intervalles intégrés)
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities/{ACT_ID}",
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities/{ACT_NUM}",
    # Variante sans athlete_id dans le chemin
    f"https://intervals.icu/api/v1/activity/{ACT_ID}/intervals",
    f"https://intervals.icu/api/v1/activity/{ACT_ID}",
]

# Affiche le contenu détaillé du bon endpoint
url_good = f"https://intervals.icu/api/v1/activity/{ACT_ID}/intervals"
r = s.get(url_good, timeout=15)
data = r.json()
print(f"=== icu_groups ({len(data.get('icu_groups', []))} entrées) ===")
for g in data.get("icu_groups", []):
    print(json.dumps(g, indent=2, default=str))
    print()
print(f"=== icu_intervals (premier) ===")
if data.get("icu_intervals"):
    print(json.dumps(data["icu_intervals"][0], indent=2, default=str))
print()
print("="*60)

for url in CANDIDATES:
    r = s.get(url, timeout=15)
    status = r.status_code
    mark = "✅" if status == 200 else "❌"
    print(f"{mark} {status}  {url}")
    if status == 200:
        try:
            data = r.json()
            if isinstance(data, list):
                print(f"       → liste de {len(data)} éléments")
                if data and isinstance(data[0], dict):
                    print(f"         keys: {list(data[0].keys())[:12]}")
                    # Cherche des champs HR ou allure
                    hr_keys = [k for k in data[0] if "heart" in k.lower() or "hr" in k.lower()]
                    print(f"         HR keys: {hr_keys}")
                    # Cherche des intervals intégrés
                    for entry in data[:2]:
                        hr = entry.get("average_heartrate") or entry.get("avg_hr")
                        t  = entry.get("moving_time") or entry.get("elapsed_time")
                        d  = entry.get("distance")
                        print(f"         → HR={hr} t={t}s d={d}m")
            elif isinstance(data, dict):
                keys = list(data.keys())
                print(f"       → dict keys: {keys[:20]}")
                # Cherche des clés liées aux intervalles
                for k in keys:
                    if any(x in k.lower() for x in ("interval", "lap", "segment", "group")):
                        v = data[k]
                        print(f"         intervals key '{k}': type={type(v).__name__}, len={len(v) if isinstance(v,(list,dict)) else v}")
        except Exception as e:
            print(f"       JSON error: {e}")
