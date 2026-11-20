# Washing machines from whole-home power (REFIT)

A small, reproducible analysis of washing-machine use in four UK homes, using the REFIT dataset. There are three scripts, one per requirement, and one file of shared settings:

1. `1_clean_house1.py` cleans the raw House 1 data and resamples it to 1-minute values (Requirement 1).
2. `2_washing_machine_eda.py` describes how the washing machine is used in four homes (Requirement 2).
3. `3_disaggregation.py` estimates the washing machine's power from the whole-house total, and tests the estimate on a home the model never saw (Requirement 3).

The findings are in `DATA.md`, `RESULTS.md` and `Recommendation.md`.

## Files

| File | What it is |
|---|---|
| `common.py` | Settings (file paths, which channel is the washer, thresholds) and shared functions. |
| `1_clean_house1.py` | Requirement 1 |
| `2_washing_machine_eda.py` | Requirement 2 |
| `3_disaggregation.py` | Requirement 3 |
| `DATA.md` | Dataset facts, cleaning rules and what the checks found |
| `RESULTS.md` | Results, plots and interpretation |
| `Recommendation.md` | Utility-facing summary, and the Section 4 answers |
| `requirements.txt` | Python packages |

## Setup

You need Python 3.10 or newer.

```
pip install -r requirements.txt
```

Create two folders and copy the dataset files into them:

```
data/raw/     RAW_House1_Part1.csv, RAW_House1_Part2.csv     (from REFIT_RAW_081116.7z)
data/clean/   CLEAN_House1.csv, CLEAN_House2.csv,
              CLEAN_House3.csv, CLEAN_House5.csv             (from CLEAN_REFIT_081116.7z)
```

## Run

From the project folder, run the three scripts in order:

```
python 1_clean_house1.py
python 2_washing_machine_eda.py
python 3_disaggregation.py
```

Each script prints its main numbers and writes tables and plots to `outputs/`. Requirement 1 reads about four million rows per raw file, so it needs a few gigabytes of memory. Each script should take a few minutes.

Requirement 1 is a separate exercise on the raw data. Requirements 2 and 3 use the official cleaned files, as the brief asks.

## Settings

All numbers that affect the results are at the top of `common.py`:

| Setting | Value | What it means |
|---|---|---|
| `WASHER` | see file | the channel that is the washing machine in each house |
| `ON_W` | 20 W | a minute counts as "on" at or above this power |
| `MAX_PAUSE_MINUTES` | 5 | a pause this short or shorter does not end a cycle |
| `MIN_CYCLE_MINUTES` | 5 | cycles shorter than this are ignored |
| `MAX_FILL_MINUTES` | 2 | missing gaps this short are filled |
| `MAX_AGGREGATE_W`, `MAX_APPLIANCE_W` | 20,000 W, 4,000 W | readings above these are treated as impossible |

## Step 1: cleaning the raw House 1 data

1. **Check.** Each file is checked for timestamps that cannot be read, timestamps that disagree with the Unix time by more than a second, rows out of order, repeated timestamps, missing values, negative readings and readings above the limits. Gaps between readings are also measured. The results are saved to `outputs/req1_quality_checks.json`.
2. **Sort and remove repeats.** Rows are sorted by time. If two rows have the same timestamp, the Part 2 row is kept, because Part 1 can record unavailable sensors as zero. Within one file, the later row is kept.
3. **Remove impossible values.** Negative readings, whole-house readings above 20 kW and appliance readings above 4 kW become missing. Zeros are kept, because an appliance reading of zero usually means it is switched off.
4. **Average to 1 minute.** Readings are averaged into one-minute bins in UTC.
5. **Handle gaps.** A run of up to 2 missing minutes is filled by a straight line between the readings on either side. Longer gaps stay empty and are listed in `outputs/req1_outages.csv`. Filling them would invent load that may not have happened.

`outputs/req1_before_after.png` shows the whole house and two appliances on one busy day, with the raw readings in grey and the cleaned minutes in blue.

## Step 2: how the washing machine is used

**The cycle rule.** A minute is "on" if the washer uses at least 20 W. A cycle starts at an on-minute and carries on through pauses of up to 5 minutes. A pause is any minutes that are not on. The cycle ends when the washer has been off for longer than 5 minutes. Short pauses, such as a drum stop or a drain, stay inside one cycle. Cycles shorter than 5 minutes are ignored.

In plain words: the washer is running until it stays quiet for more than five minutes.

Missing and flagged minutes (`Issues = 1`) are never counted as "off" in the statistics. Inside a cycle they count as part of a pause, so a single bad reading does not split one wash into two.

This rule finds cycle-like operating periods. It does not identify each wash programme. A long pause or a threshold that is set differently could split or merge some programmes.

**The comparison.** All four homes are compared over the dates on which all four have data.

**What the outputs show.** A summary table for each house (missing time, zero and off time, number of cycles, typical cycle length, peak power and energy), a list of every detected cycle, usage by hour and by day of week, and four plots.

## Step 3: estimating the washing machine's power

**Inputs.** The model sees only the whole-house power now, 1, 5 and 15 minutes ago, the average over the last 5 minutes, the time of day, and whether it is a weekend. Time of day is encoded as a sine and a cosine, so that 23:59 and 00:00 are treated as neighbours. The washing machine's own readings are never inputs.

**Model.** Gradient boosting. It builds many small decision trees one after another, and each tree corrects the mistakes of the ones before it. It is a standard, well-understood choice for tables of numbers, and it needs little tuning.

**Split.** The model trains on Houses 1, 2 and 3 and is tested on House 5. Holding out a whole house tests whether the model works in a home it has never seen. Splitting randomly by time within one house would look better than it is, because neighbouring minutes are almost identical. The script checks that House 5 is absent from the training data.

**Baselines.** A model should be compared with something simple:
- *Always off:* predicts 0 W for every minute.
- *Usage profile:* predicts the average washer power for each hour of the day, learned from the training houses only.

**Metrics.**
- *MAE and RMSE (watts).* MAE is the average size of the error. RMSE gives extra weight to large misses.
- *MAE when the washer is on.* This measures error during the minutes that matter most.
- *Energy error (%).* The estimated energy over the test period compared with the actual energy. This is the number that matters for bills and savings.
- *On/off precision, recall and F1 at 20 W.* These measure whether the model knows when the washer is running. Plain accuracy would be misleading, because the washer is off for most of the time.

## Assumptions and trade-offs

- Timestamps are in UTC. Time of day and day of week use London time.
- The thresholds (20 W, the 5-minute pause, the 2-minute fill, and the impossible-value limits) are reasonable choices, not measured properties of the washer.
- The model uses the whole-house total only. Another appliance running at the same time, such as a kettle, heater or dryer, can look like the washer.
- One train/test split is simple, but it tests on a single home. Leave-one-house-out testing would be a stronger check.
- Averaging to 1 minute smooths out short events.

## Possible improvements

- Leave-one-house-out testing across all four homes, to see how much the results depend on which home is tested.
- Use more of the 20 homes in the dataset.
- Tune thresholds on a validation home, not on the test home.
- Check detected cycles against labelled wash programmes, or against a smart plug on the washer.
- Compare the regression with a simpler on/off classifier.

## AI tools used

Claude helped draft and review the code and the documents.
