import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (f1_score, mean_absolute_error, mean_squared_error, precision_score, recall_score)
from common import (OUT_DIR, LOCAL_TZ, EDA_HOUSES, TRAIN_HOUSES, TEST_HOUSE, ON_W, load_minutes, common_window)

FEATURES = ["aggregate_now", "aggregate_1min_ago", "aggregate_5min_ago", "aggregate_15min_ago", "aggregate_5min_mean", "hour_sin", "hour_cos", "weekend"]

def build_table(house, minutes):
    total = minutes["aggregate_w"]
    local = minutes.index.tz_convert(LOCAL_TZ)
    hour = local.hour.to_numpy() + local.minute.to_numpy() / 60
    x = pd.DataFrame({
        "aggregate_now": total,
        "aggregate_1min_ago": total.shift(1),
        "aggregate_5min_ago": total.shift(5),
        "aggregate_15min_ago": total.shift(15),
        "aggregate_5min_mean": total.rolling(5).mean(),
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "weekend": (local.dayofweek.to_numpy() >= 5).astype(int),
    }, index=minutes.index)
    keep = (minutes["washer_w"].notna() & ~minutes["issue"] & x.notna().all(axis=1)).to_numpy()
    return x[keep].assign(
        washer_w=minutes["washer_w"].to_numpy()[keep],
        hour=local.hour.to_numpy()[keep],
        house=house,
    )

def score(actual, predicted):
    on_actual = actual >= ON_W
    on_predicted = predicted >= ON_W
    error = np.abs(actual - predicted)
    return {
        "MAE_all_minutes_W": mean_absolute_error(actual, predicted),
        "RMSE_W": np.sqrt(mean_squared_error(actual, predicted)),
        "MAE_when_washer_on_W": error[on_actual].mean(),
        "energy_actual_kWh": actual.sum() / 60 / 1000,
        "energy_estimated_kWh": predicted.sum() / 60 / 1000,
        "energy_error_pct": 100 * (predicted.sum() - actual.sum()) / actual.sum(),
        "on_precision": precision_score(on_actual, on_predicted, zero_division=0),
        "on_recall": recall_score(on_actual, on_predicted, zero_division=0),
        "on_f1": f1_score(on_actual, on_predicted, zero_division=0),
    }

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    minutes = common_window({h: load_minutes(h) for h in EDA_HOUSES})
    print(f"Common period (UTC): {minutes[1].index[0]} to {minutes[1].index[-1]}")
    tables = {h: build_table(h, minutes[h]) for h in EDA_HOUSES}
    train = pd.concat([tables[h] for h in TRAIN_HOUSES])
    test = tables[TEST_HOUSE]
    assert TEST_HOUSE not in set(train["house"]), "test house leaked into training"
    print(f"Training rows: {len(train):,} (Houses {TRAIN_HOUSES}); "
          f"test rows: {len(test):,} (House {TEST_HOUSE})")
    model = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.1, early_stopping=False, random_state=0)
    model.fit(train[FEATURES], train["washer_w"])
    profile = train.groupby("hour")["washer_w"].mean()
    test = test.assign(
        always_off_w=0.0,
        usage_profile_w=test["hour"].map(profile).fillna(0.0),
        model_w=np.clip(model.predict(test[FEATURES]), 0, None),
    )
    actual = test["washer_w"].to_numpy()
    results = pd.DataFrame({
        "always_off": score(actual, test["always_off_w"].to_numpy()),
        "usage_profile": score(actual, test["usage_profile_w"].to_numpy()),
        "gradient_boosting": score(actual, test["model_w"].to_numpy()),
    }).T.round(3)
    results.to_csv(OUT_DIR / "req3_metrics.csv")
    print(results.to_string())
    on_actual = actual >= ON_W
    on_model = test["model_w"].to_numpy() >= ON_W
    whole_house = test["aggregate_now"].to_numpy()
    groups = {
        "false alarm (model says on, washer off)": on_model & ~on_actual,
        "miss (washer on, model says off)": ~on_model & on_actual,
        "correct on (both on)": on_model & on_actual,
    }
    failure = pd.DataFrame({
        name: {
            "minutes": int(mask.sum()),
            "median_whole_house_w": float(np.median(whole_house[mask])) if mask.any() else np.nan,
            "pct_whole_house_over_1000w": float(100 * np.mean(whole_house[mask] > 1000))
                                          if mask.any() else np.nan,
        }
        for name, mask in groups.items()
    }).T.round(1)
    failure.to_csv(OUT_DIR / "req3_failure_check.csv")
    print(failure.to_string())
    full = minutes[TEST_HOUSE].join(test[["usage_profile_w", "model_w"]])
    local_day = full.index.tz_convert(LOCAL_TZ).tz_localize(None).normalize()
    on_per_day = pd.Series((full["washer_w"] >= ON_W).to_numpy(), index=local_day)
    day = on_per_day.groupby(level=0).sum().idxmax()
    shown = full[local_day == day]
    t = shown.index.tz_convert(LOCAL_TZ).tz_localize(None)
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.plot(t, shown["washer_w"], color="black", lw=1.5, label="Actual washing machine")
    ax.plot(t, shown["model_w"], color="tab:orange", lw=1.2, label="Gradient boosting estimate")
    ax.plot(t, shown["usage_profile_w"], color="0.6", lw=1, ls="--", label="Usage-profile baseline")
    ax.set_ylabel("Watts")
    ax.set_xlabel("Time of day (London)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_title(f"House {TEST_HOUSE} (never seen in training), {pd.Timestamp(day).date()}")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "req3_actual_vs_predicted.png", dpi=130)
    plt.close(fig)
    print(f"Outputs written to {OUT_DIR}")

if __name__ == "__main__":
    main()
