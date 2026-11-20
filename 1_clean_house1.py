import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from common import (RAW_DIR, OUT_DIR, WASHER, MAX_FILL_MINUTES, MAX_APPLIANCE_W, MAX_AGGREGATE_W, missing_run_length)

CHANNELS = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
EPOCH = pd.Timestamp("1970-01-01")

def limit_for(channel):
    return MAX_AGGREGATE_W if channel == "Aggregate" else MAX_APPLIANCE_W

def read_part(path, part_number):
    df = pd.read_csv(path)
    unix = pd.to_numeric(df["Unix"], errors="coerce")
    time = pd.to_datetime(df["Time"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    values = df[CHANNELS].apply(pd.to_numeric, errors="coerce")
    seconds_apart = ((time - EPOCH).dt.total_seconds() - unix).abs()
    checks = {
        "file": path.name,
        "rows": len(df),
        "unix_unreadable": int(unix.isna().sum()),
        "time_unreadable": int(time.isna().sum()),
        "time_and_unix_over_1s_apart": int((seconds_apart > 1).sum()),
        "rows_earlier_than_previous_row": int((unix.diff() < 0).sum()),
        "repeated_timestamps": int(unix.duplicated().sum()),
        "missing_values": {c: int(values[c].isna().sum()) for c in CHANNELS},
        "negative_values": {c: int((values[c] < 0).sum()) for c in CHANNELS},
        "above_limit": {c: int((values[c] > limit_for(c)).sum()) for c in CHANNELS},
    }
    data = values.assign(Unix=unix, part=part_number).dropna(subset=["Unix"])
    return data, checks

def list_runs(flag):
    run = (flag != flag.shift()).cumsum()
    rows = []
    for _, block in flag.groupby(run):
        if block.iloc[0]:
            rows.append({
                "start_utc": block.index[0],
                "end_utc": block.index[-1] + pd.Timedelta(minutes=1),
                "minutes": len(block),
            })
    return pd.DataFrame(rows, columns=["start_utc", "end_utc", "minutes"])

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    part1, checks1 = read_part(RAW_DIR / "RAW_House1_Part1.csv", 1)
    part2, checks2 = read_part(RAW_DIR / "RAW_House1_Part2.csv", 2)
    raw = pd.concat([part1, part2], ignore_index=True)
    raw["Unix"] = raw["Unix"].astype("int64")
    raw["row"] = np.arange(len(raw))
    ordered = raw.sort_values(["Unix", "part", "row"])
    unique = ordered.drop_duplicates("Unix", keep="last")
    shared = np.intersect1d(part1["Unix"].to_numpy(), part2["Unix"].to_numpy())
    df = unique[CHANNELS].copy()
    df.index = pd.to_datetime(unique["Unix"].to_numpy(), unit="s", utc=True)
    gaps = unique["Unix"].diff()
    intervals = {
        "most_common_seconds": {str(int(k)): int(v) for k, v in gaps.value_counts().head(5).items()},
        "outside_6_to_8_seconds": int(((gaps < 6) | (gaps > 8)).sum()),
        "gaps_over_60_seconds": int((gaps > 60).sum()),
        "longest_gap_seconds": int(gaps.max()),
    }
    readings = df.copy()
    impossible = {}
    for c in CHANNELS:
        bad = (readings[c] < 0) | (readings[c] > limit_for(c))
        impossible[c] = int(bad.sum())
        readings.loc[bad, c] = np.nan
    minutes = readings.resample("1min").mean()
    filled = {}
    for c in CHANNELS:
        missing = minutes[c].isna()
        interpolated = minutes[c].interpolate(limit_area="inside")
        short = missing & (missing_run_length(missing) <= MAX_FILL_MINUTES) & interpolated.notna()
        filled[c] = int(short.sum())
        minutes[c] = minutes[c].where(~short, interpolated)
    outages = list_runs(minutes["Aggregate"].isna())
    outages.to_csv(OUT_DIR / "req1_outages.csv", index=False)
    minutes.index.name = "time_utc"
    minutes.to_csv(OUT_DIR / "req1_house1_1min.csv.gz", float_format="%.2f")
    busiest = df.index.floor("D").value_counts().idxmax()
    day_end = busiest + pd.Timedelta(days=1)
    raw_day = df[(df.index >= busiest) & (df.index < day_end)]
    clean_day = minutes[(minutes.index >= busiest) & (minutes.index < day_end)]
    plot_channels = ["Aggregate", "Appliance1", WASHER[1]]
    titles = ["Whole house (Aggregate)", "Appliance 1",
              f"{WASHER[1]}: washing machine (per Refit.txt)"]
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    for ax, channel, title in zip(axes, plot_channels, titles):
        ax.plot(raw_day.index, raw_day[channel], color="0.6", lw=0.6, label="Raw readings (about every 8 s)")
        ax.plot(clean_day.index, clean_day[channel], color="tab:blue", lw=1.3, label="Cleaned, 1-minute average")
        ax.set_title(title, loc="left")
        ax.set_ylabel("Watts")
        ax.grid(alpha=0.3)
    axes[0].legend(loc="upper right", frameon=False)
    axes[-1].set_xlabel("Time (UTC)")
    fig.suptitle(f"House 1 before and after cleaning, {busiest.date()}")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "req1_before_after.png", dpi=130)
    plt.close(fig)
    report = {
        "part_checks": [checks1, checks2],
        "combined": {
            "rows_in_both_files": len(raw),
            "rows_after_removing_repeats": len(unique),
            "rows_removed_as_repeats": len(raw) - len(unique),
            "timestamps_present_in_both_files": int(len(shared)),
            "coverage_utc": [str(df.index.min()), str(df.index.max())],
            "intervals": intervals,
        },
        "impossible_values_set_to_missing": impossible,
        "gaps_filled_minutes": filled,
        "outages_over_2_minutes": int(len(outages)),
        "outage_minutes": int(outages["minutes"].sum()),
        "missing_minutes_after_cleaning": {c: int(minutes[c].isna().sum()) for c in CHANNELS},
        "minutes_in_output": int(len(minutes)),
        "before_after_plot_day_utc": str(busiest.date()),
    }
    (OUT_DIR / "req1_quality_checks.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report["combined"], indent=2, default=str))
    print(f"Outputs written to {OUT_DIR}")

if __name__ == "__main__":
    main()
