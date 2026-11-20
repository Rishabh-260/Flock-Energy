from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "outputs"
LOCAL_TZ = "Europe/London"

WASHER = {1: "Appliance5", 2: "Appliance2", 3: "Appliance6", 5: "Appliance3"}
EDA_HOUSES = [1, 2, 3, 5]
TRAIN_HOUSES = [1, 2, 3]
TEST_HOUSE = 5

MAX_FILL_MINUTES = 2
MAX_APPLIANCE_W = 4000
MAX_AGGREGATE_W = 20000

ON_W = 20
MAX_PAUSE_MINUTES = 5
MIN_CYCLE_MINUTES = 5

def load_minutes(house):
    channel = WASHER[house]
    raw = pd.read_csv(CLEAN_DIR / f"CLEAN_House{house}.csv", usecols=["Unix", "Aggregate", channel, "Issues"])
    raw.index = pd.to_datetime(raw["Unix"].to_numpy(), unit="s", utc=True)
    return pd.DataFrame({
        "aggregate_w": raw["Aggregate"].resample("1min").mean(),
        "washer_w": raw[channel].resample("1min").mean(),
        "issue": raw["Issues"].resample("1min").max().fillna(0).astype(bool),
    })

def common_window(frames):
    start = max(f.index.min() for f in frames.values())
    end = min(f.index.max() for f in frames.values())
    return {house: f.loc[start:end] for house, f in frames.items()}

def missing_run_length(missing):
    run = (missing != missing.shift()).cumsum()
    length = missing.groupby(run).transform("sum").astype(int)
    return length.where(missing, 0)

def find_cycles(minutes):
    power = minutes["washer_w"].to_numpy()
    unknown = np.isnan(power) | minutes["issue"].to_numpy()
    on_minutes = np.flatnonzero(~unknown & (power >= ON_W))
    spans = []
    start = previous = None
    for i in on_minutes:
        if start is None:
            start = i
        elif i - previous - 1 > MAX_PAUSE_MINUTES:
            spans.append((start, previous))
            start = i
        previous = i
    if start is not None:
        spans.append((start, previous))
    rows = []
    for first, last in spans:
        length = last - first + 1
        if length < MIN_CYCLE_MINUTES:
            continue
        segment = power[first:last + 1]
        rows.append({
            "start_utc": minutes.index[first],
            "end_utc": minutes.index[last] + pd.Timedelta(minutes=1),
            "duration_min": length,
            "peak_w": float(np.nanmax(segment)),
            "energy_wh": float(np.nansum(segment) / 60),
        })
    return pd.DataFrame(rows, columns=["start_utc", "end_utc", "duration_min", "peak_w", "energy_wh"])
