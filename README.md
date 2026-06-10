# Training Analyzer

Analyzes your running training data from **[Intervals.icu](https://intervals.icu)** — activities, HR, paces, CTL/ATL, TRIMP, wellness (HRV).

Produces a reusable `training_data.json` file.

---

## Installation

### Requirements

- Python 3.11+
- pip

```bash
pip install -r requirements.txt
```

### Intervals.icu credentials

```bash
cp .env.example .env
# Open .env and fill in:
#   INTERVALS_ATHLETE_ID=your_id      ← intervals.icu/settings → bottom → API
#   INTERVALS_API_KEY=your_api_key
```

Your athlete ID and API key are on **https://intervals.icu/settings** (bottom of the page, "API" section).

---

## Usage

### All-in-one (recommended)

```bash
bash run.sh
```

The script loads `.env`, installs dependencies, and collects the data.

To include the per-interval breakdown:

```bash
FETCH_INTERVALS=1 bash run.sh
```

### Step by step

```bash
# Linux / Mac
export INTERVALS_ATHLETE_ID="your_id"
export INTERVALS_API_KEY="your_api_key"

# Windows PowerShell
$env:INTERVALS_ATHLETE_ID="your_id"
$env:INTERVALS_API_KEY="your_api_key"

# 1. Collect the data (last 6 months)
python3 fetch_training_data.py --start 2025-12-01 --end 2026-06-10

# 2. With intervals (slower — ~0.2 s/activity)
python3 fetch_training_data.py --start 2025-12-01 --end 2026-06-10 --fetch-intervals
```

### `fetch_training_data.py` options

| Option | Default | Description |
|--------|---------|-------------|
| `--start` | `2025-12-01` | Start date `YYYY-MM-DD` |
| `--end` | today | End date |
| `--out` | `training_data.json` | Output JSON file |
| `--fcm` | `196` | Max HR (bpm) — measured running |
| `--lthr` | `181` | Lactate threshold HR (bpm) |
| `--fetch-intervals` | — | Download interval data (~30 s for 130 sessions) |

### Optional `.env` variables

```dotenv
INTERVALS_ATHLETE_ID=your_id
INTERVALS_API_KEY=your_api_key

# Physiology (optional — falls back to the script defaults)
FCM=196
LTHR=181

# Enable intervals via run.sh
FETCH_INTERVALS=1
```

---

## JSON structure

```jsonc
{
  "meta": {
    "total_runs": 133,
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
      "hr_avg": 158,
      "hr_pct_fcm": 80.6,
      "hr_zone": 3,
      "ctl": 52.1,
      "atl": 58.4,
      "form": -6.3,
      "trimp": 189,
      "interval_data": {            // null unless --fetch-intervals is used
        "hr_avg": 170,
        "hr_pct_fcm": 86.7,
        "pace_sec_per_km": 216,     // 3:36/km — interval portion only
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

## HR zones

Based on LTHR (lactate threshold) and max HR:

| Zone | % LTHR | % HRmax (HRmax=196) | Characteristic |
|------|--------|---------------------|----------------|
| Z1 | < 70% | < 65% | Active recovery |
| Z2 | 70–82% | 65–75.5% | Base endurance |
| Z3 | 82–89% | 75.5–82% | Tempo / aerobic threshold |
| Z4 | 89–97% | 82–89.3% | Lactate threshold |
| Z5 | > 97% | > 89.3% | VO2max / sprint |

---

## Files

```
training-analyzer/
├── fetch_training_data.py   collect → training_data.json
├── run.sh                   all-in-one script
├── requirements.txt         Python dependencies
├── .env.example             credentials template (do not commit .env)
├── debug_intervals.py       intervals API diagnostics (development)
└── README.md                this file
```

`training_data.json` and `.env` are in `.gitignore` — they contain personal data.
