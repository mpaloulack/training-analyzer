# Training Analyzer

Analyse tes données d'entraînement course à pied en croisant trois sources :

- **[Intervals.icu](https://intervals.icu)** — activités, FC, allures, CTL/ATL, TRIMP, wellness (HRV)
- **[Enduraw](https://www.enduraw.com)** *(plugin Garmin)* — allure ajustée + coût vent/chaleur/dénivellé
- **[Environnement Canada](https://climate.weather.gc.ca)** — température et rafales journalières (station McTavish, Montréal)

Génère un fichier JSON réutilisable et 5 graphiques matplotlib.

---

## Graphiques

| Fichier | Contenu |
|---------|---------|
| `1_fcm_vs_allure.png` | %FCmax vs allure ajustée, coloré par température **et** par vent — sorties faciles (cercle), intervalles (diamant ◆), courses (étoile ★) |
| `2_delta_allure_env.png` | Coût environnemental par séance (allure brute − ajustée), coloré par température |
| `3_ctl_atl_forme.png` | CTL / ATL / Forme + HRV (VFC) sur la même timeline |
| `4_bubble_seances.png` | Vue d'ensemble : date × allure, taille = TRIMP, couleur = %FCmax |
| `5_zones_intervals.png` | Distribution zones FC par séance d'intervalles — avec l'allure moyenne par zone à l'intérieur de chaque bande |

---

## Installation

### Prérequis

- Python 3.11+
- pip

```bash
pip install -r requirements.txt
```

### Credentials Intervals.icu

```bash
cp .env.example .env
# Ouvre .env et remplis :
#   INTERVALS_ATHLETE_ID=ton_id      ← intervals.icu/settings → bas de page → API
#   INTERVALS_API_KEY=ton_api_key
```

L'ID athlète et la clé API se trouvent sur **https://intervals.icu/settings** (bas de page, section "API").

---

## Utilisation

### Tout-en-un (recommandé)

```bash
bash run.sh
```

Le script charge `.env`, installe les dépendances, collecte les données et génère les graphiques.

Pour inclure la décomposition par intervalles (graphique 5) :

```bash
FETCH_INTERVALS=1 bash run.sh
```

### Étape par étape

```bash
# Linux / Mac
export INTERVALS_ATHLETE_ID="ton_id"
export INTERVALS_API_KEY="ton_api_key"

# Windows PowerShell
$env:INTERVALS_ATHLETE_ID="ton_id"
$env:INTERVALS_API_KEY="ton_api_key"

# 1. Collecter les données (6 derniers mois)
python3 fetch_training_data.py --start 2025-12-01 --end 2026-06-10

# 2. Avec intervalles (plus lent — ~0.2 s/activité)
python3 fetch_training_data.py --start 2025-12-01 --end 2026-06-10 --fetch-intervals

# 3. Générer les graphiques
python3 plot_training.py training_data.json --out graphs/
```

### Options `fetch_training_data.py`

| Option | Défaut | Description |
|--------|--------|-------------|
| `--start` | `2025-12-01` | Date début `YYYY-MM-DD` |
| `--end` | aujourd'hui | Date fin |
| `--out` | `training_data.json` | Fichier JSON de sortie |
| `--fcm` | `196` | FC max (bpm) — mesurée en course |
| `--lthr` | `181` | Seuil lactate (bpm) |
| `--no-eccc` | — | Ignorer la météo Environnement Canada |
| `--fetch-intervals` | — | Télécharger les intervalles (~30 s pour 130 séances) |

### Variables `.env` optionnelles

```dotenv
INTERVALS_ATHLETE_ID=ton_id
INTERVALS_API_KEY=ton_api_key

# Physiologie (optionnel — utilise les défauts du script sinon)
FCM=196
LTHR=181

# Activer les intervalles via run.sh
FETCH_INTERVALS=1
```

---

## Structure du JSON

```jsonc
{
  "meta": {
    "total_runs": 133,
    "with_enduraw": 52,
    "with_eccc_weather": 124,
    "with_intervals": 8,
    "with_hrv": 180,
    "fcm_bpm": 196,
    "lthr_bpm": 181
  },
  "activities": [
    {
      "id": "iXXXXXXXXX",
      "date": "2026-06-07",
      "name": "7*1400 3'45=>3'25",
      "distance_km": 18.36,
      "pace_raw_sec_per_km": 263,
      "pace_adj_sec_per_km": 255,   // allure Enduraw (conditions standard)
      "hr_avg": 158,
      "hr_pct_fcm": 80.6,
      "hr_zone": 3,
      "ctl": 52.1,
      "atl": 58.4,
      "form": -6.3,
      "trimp": 189,
      "enduraw": { "available": true, "temp_c": 21.0, "wind_kmh": 12.0, ... },
      "eccc_weather": { "mean_temp_c": 20.5, "max_gust_kmh": 30 },
      "env_temp_c": 21.0,
      "env_wind_kmh": 12.0,
      "interval_data": {            // null si --fetch-intervals non utilisé
        "hr_avg": 170,
        "hr_pct_fcm": 86.7,
        "pace_sec_per_km": 216,     // 3:36/km — portion intervalles seulement
        "reps": 7,
        "label": "300s@170bpm92rpm",
        "zone_distribution": {
          "total_sec": 4800,
          "z2_sec": 1662, "z2_pct": 34.6, "z2_pace_sec_km": 295,
          "z3_sec": 906,  "z3_pct": 18.9, "z3_pace_sec_km": 310,
          "z4_sec": 2100, "z4_pct": 43.8, "z4_pace_sec_km": 216,
          "z5_sec": 132,  "z5_pct": 2.7,  "z5_pace_sec_km": 198
        }
      }
    }
  ],
  "wellness_timeline": [
    {
      "date": "2026-06-07",
      "hrv": 48.2,
      "resting_hr": 42,
      "sleep_h": 7.5,
      "ctl": 52.1,
      "atl": 58.4,
      "form": -6.3
    }
  ]
}
```

---

## Zones FC

Basées sur le LTHR (seuil lactate) et la FCmax :

| Zone | % LTHR | % FCmax (FCmax=196) | Caractéristique |
|------|--------|---------------------|-----------------|
| Z1 | < 70% | < 65% | Récupération active |
| Z2 | 70–82% | 65–75.5% | Endurance fondamentale |
| Z3 | 82–89% | 75.5–82% | Tempo / seuil aérobie |
| Z4 | 89–97% | 82–89.3% | Seuil lactate |
| Z5 | > 97% | > 89.3% | VO2max / sprint |

---

## Sources météo

| Source | Priorité | Couverture | Données |
|--------|----------|------------|---------|
| **Enduraw** | 1 (plus précis) | ~40% des séances | Temp. + vent mesurés pendant la course |
| **Environnement Canada** | 2 (fallback) | ~100% | Temp. moy. journalière + rafale max (station McTavish, Montréal) |

---

## Fichiers

```
training-analyzer/
├── fetch_training_data.py   collecte → training_data.json
├── plot_training.py         graphiques depuis le JSON
├── run.sh                   script tout-en-un
├── requirements.txt         dépendances Python
├── .env.example             template credentials (ne pas committer .env)
├── debug_intervals.py       diagnostic API intervals (développement)
└── README.md                ce fichier
```

Les fichiers `training_data.json`, `graphs/` et `.env` sont dans `.gitignore` — ils contiennent des données personnelles.
