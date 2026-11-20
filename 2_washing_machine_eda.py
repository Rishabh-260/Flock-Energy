import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from common import (OUT_DIR, LOCAL_TZ, WASHER, EDA_HOUSES, ON_W, load_minutes, common_window, find_cycles, missing_run_length)

HOUSE_FOR_TRACE = 5

def summarise(house, minutes, cycles):
    power = minutes["washer_w"]
    usable = power.notna() & ~minutes["issue"]
    weeks = len(minutes) / (7 * 1440)
    return {
        "house": house,
        "channel": WASHER[house],
        "minutes": len(minutes),
        "missing_pct": 100 * power.isna().mean(),
        "longest_missing_hours": missing_run_length(power.isna()).max() / 60,
        "issue_pct": 100 * minutes["issue"].mean(),
        "zero_pct_of_usable": 100 * (usable & (power == 0)).sum() / usable.sum(),
        "off_pct_of_usable": 100 * (usable & (power < ON_W)).sum() / usable.sum(),
        "cycles": len(cycles),
        "cycles_per_week": len(cycles) / weeks,
        "median_cycle_min": cycles["duration_min"].median(),
        "median_peak_w": cycles["peak_w"].median(),
        "median_energy_wh": cycles["energy_wh"].median(),
    }

def usage_tables(minutes_by_house):
    parts = []
    for house, minutes in minutes_by_house.items():
        local = minutes.index.tz_convert(LOCAL_TZ)
        usable = (minutes["washer_w"].notna() & ~minutes["issue"]).to_numpy()
        on = usable & (minutes["washer_w"] >= ON_W).to_numpy()
        parts.append(pd.DataFrame({
            "house": house,
            "hour": local.hour.to_numpy(),
            "weekday": local.dayofweek.to_numpy(),
            "usable": usable,
            "on": on,
        }))
    rows = pd.concat(parts)
    rows = rows[rows["usable"]]
    by_hour = rows.groupby(["hour", "house"])["on"].mean().unstack("house") * 100
    by_day = rows.groupby(["weekday", "house"])["on"].mean().unstack("house") * 100
    by_hour.columns = [f"House {h}" for h in by_hour.columns]
    by_day.columns = [f"House {h}" for h in by_day.columns]
    return by_hour, by_day

def busiest_day(minutes):
    local_day = minutes.index.tz_convert(LOCAL_TZ).tz_localize(None).normalize()
    on = (minutes["washer_w"] >= ON_W).to_numpy()
    return pd.Series(on, index=local_day).groupby(level=0).sum().idxmax()

def plot_day(minutes, house):
    day = busiest_day(minutes)
    local_day = minutes.index.tz_convert(LOCAL_TZ).tz_localize(None).normalize()
    part = minutes[local_day == day]
    t = part.index.tz_convert(LOCAL_TZ).tz_localize(None)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    top.plot(t, part["aggregate_w"], color="0.3", lw=0.8)
    top.set_ylabel("Whole house (W)")
    bottom.plot(t, part["washer_w"], color="tab:orange", lw=1.2)
    bottom.axhline(ON_W, color="red", ls="--", lw=0.8, label=f"{ON_W} W threshold")
    bottom.set_ylabel("Washing machine (W)")
    bottom.set_xlabel("Time of day (London)")
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    bottom.legend(frameon=False)
    fig.suptitle(f"House {house}, {day.date()}: whole-house and washing-machine power")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "req2_24h_trace.png", dpi=130)
    plt.close(fig)

def plot_one_cycle(minutes, cycles):
    house = max(cycles, key=lambda h: len(cycles[h]))
    found = cycles[house]
    if found.empty:
        return
    median = found["energy_wh"].median()
    cycle = found.iloc[(found["energy_wh"] - median).abs().argmin()]
    pad = pd.Timedelta(minutes=30)
    window = minutes[house].loc[cycle["start_utc"] - pad: cycle["end_utc"] + pad]
    t = window.index.tz_convert(LOCAL_TZ).tz_localize(None)
    start = cycle["start_utc"].tz_convert(LOCAL_TZ).tz_localize(None)
    end = cycle["end_utc"].tz_convert(LOCAL_TZ).tz_localize(None)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(t, window["washer_w"], color="tab:orange", lw=1.3, label="Washing machine (W)")
    ax.axvspan(start, end, color="gold", alpha=0.3, label="Detected cycle")
    ax.axhline(ON_W, color="red", ls="--", lw=0.8, label=f"{ON_W} W threshold")
    ax.set_title(f"House {house}, a typical cycle: {int(cycle['duration_min'])} min, "
                 f"{cycle['energy_wh']:.0f} Wh, peak {cycle['peak_w']:.0f} W")
    ax.set_ylabel("Watts")
    ax.set_xlabel("Time of day (London)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "req2_one_cycle.png", dpi=130)
    plt.close(fig)

def plot_cross_house(cycles):
    houses = list(cycles)
    positions = range(1, len(houses) + 1)
    labels = [f"House {h}" for h in houses]
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))
    left.boxplot([cycles[h]["duration_min"] for h in houses], showfliers=False)
    left.set_xticks(list(positions), labels)
    left.set(ylabel="Minutes", title="Cycle length (start to end)")
    right.boxplot([cycles[h]["energy_wh"] for h in houses], showfliers=False)
    right.set_xticks(list(positions), labels)
    right.set(ylabel="Wh", title="Energy per cycle")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "req2_cross_house.png", dpi=130)
    plt.close(fig)

def plot_usage(by_hour, by_day):
    day_names = dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]))
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 4.5))
    by_hour.plot(ax=left)
    left.set(xlabel="Hour of day (London time)", ylabel="% of minutes washer is on", title="By hour")
    by_day.rename(index=day_names).plot.bar(ax=right, rot=0)
    right.set(xlabel="Day of week", ylabel="% of minutes washer is on", title="By day")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "req2_usage_patterns.png", dpi=130)
    plt.close(fig)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    minutes = common_window({h: load_minutes(h) for h in EDA_HOUSES})
    cycles = {h: find_cycles(minutes[h]) for h in EDA_HOUSES}
    summary = pd.DataFrame([summarise(h, minutes[h], cycles[h]) for h in EDA_HOUSES]).round(2)
    summary.to_csv(OUT_DIR / "req2_house_summary.csv", index=False)
    pd.concat([c.assign(house=h) for h, c in cycles.items()]).to_csv(OUT_DIR / "req2_cycles.csv", index=False)
    by_hour, by_day = usage_tables(minutes)
    by_hour.round(2).to_csv(OUT_DIR / "req2_usage_by_hour.csv")
    by_day.round(2).to_csv(OUT_DIR / "req2_usage_by_day.csv")
    plot_day(minutes[HOUSE_FOR_TRACE], HOUSE_FOR_TRACE)
    plot_one_cycle(minutes, cycles)
    plot_cross_house(cycles)
    plot_usage(by_hour, by_day)
    print(f"Common period (UTC): {minutes[1].index[0]} to {minutes[1].index[-1]}")
    print(summary.to_string(index=False))
    print(f"Outputs written to {OUT_DIR}")

if __name__ == "__main__":
    main()
