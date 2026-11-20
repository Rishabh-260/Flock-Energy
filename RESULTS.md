
# Results
 
## Requirement 1: cleaning the raw House 1 data
 
The full checks, cleaning rules and remaining concerns are in DATA.md. The main results are:
 
- The two raw files hold 8,518,763 rows. After removing 1,211,048 repeated timestamps, 7,307,715 readings remain. 191,889 timestamps appear in both files, and for those the Part 2 row is kept.
- The readings are not evenly spaced. About 51% of gaps between readings fall outside 6 to 8 seconds, and 4,040 gaps are longer than 60 seconds. The longest is about 41.6 days.
- The cleaned data is one-minute averages. Gaps of up to 2 minutes are filled, and longer gaps are left empty and listed in `outputs/req1_outages.csv`.
`req1_before_after.png` shows the whole house, Appliance 1 and Appliance 5 (the washing machine) for one busy day. The raw readings are grey and the cleaned one-minute averages are blue.
 
## Requirement 2: washing-machine use
 
### Homes and period
 
Houses 1, 2, 3 and 5. The washer channels are in `common.py`. Common period: 2013-10-09 13:06 to 2015-05-28 08:05 UTC, which is 857,940 minutes (about 596 days) for each home.
 
### Availability and data quality
 
From `outputs/req2_house_summary.csv`:
 
| House | Channel | Missing time (%) | Longest gap (h) | Flagged minutes (%) | Zero time (% of usable) | Off time (% of usable) | Cycles (per week) | Median cycle (min) | Median peak (W) | Median energy (Wh) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Appliance5 | 12.3 | 998.4 | 1.9 | 98.1 | 98.7 | 460 (5.4) | 31 | 2,264 | 215 |
| 2 | Appliance2 | 25.4 | 1,488.6 | 1.4 | 95.1 | 96.0 | 439 (5.2) | 82 | 2,076 | 504 |
| 3 | Appliance6 | 11.4 | 998.4 | 6.4 | 94.2 | 95.5 | 845 (9.9) | 49 | 1,874 | 388 |
| 5 | Appliance3 | 8.8 | 207.6 | 7.8 | 52.6 | 94.1 | 1,061 (12.5) | 28 | 494 | 130 |
 
The washer is on for only 1.3% to 5.9% of usable minutes, and off or near zero for the rest. House 2 has the most missing time, including one gap of about 62 days. Houses 1 and 3 share the same longest gap. Each home is compared over the same dates, but House 2 has the least usable data, so its figures rest on less evidence.
 
House 5 looks different from the other three. Its channel reads exactly zero in only 52.6% of usable minutes, against 94% to 98% elsewhere. It has the most cycles, and its median peak is 494 W, about a quarter of the 1,874 to 2,264 W seen in the other homes. Its channel may not capture the washer in the same way.
 
### Cycle rule
 
A minute is on when the washer uses at least 20 W. A cycle runs from its first on-minute to its last. A pause of up to 5 minutes does not end it. A pause is any minutes that are not on, including missing or flagged minutes. Cycles shorter than 5 minutes are dropped. Missing and flagged minutes are never counted as off. The full rule is in README.md, Step 2.
 
### Usage patterns
 
From `outputs/req2_usage_by_hour.csv` and `outputs/req2_usage_by_day.csv`. Shares are the percentage of usable minutes with the washer on.
 
| House | Busiest hours | Busiest days | Quietest day |
|---|---|---|---|
| 1 | 11:00 (5.4%), 10:00 (4.6%), 12:00 (4.3%) | Wednesday (1.9%), Tuesday (1.5%) | Saturday (0.9%) |
| 2 | 10:00 (9.2%), 14:00 (8.9%), 9:00 (8.7%) | Monday (5.2%) | Friday (3.6%) |
| 3 | 10:00 (14.8%), 9:00 (14.4%), 11:00 (12.6%) | Tuesday (7.2%), Monday (6.9%) | Saturday (2.1%) |
| 5 | 12:00 (9.7%), 13:00 (9.6%), 10:00 (9.5%), 19:00 (8.1%) | Saturday (14.0%), Sunday (9.2%) | Tuesday (1.3%) |
 
**Mornings.** The clearest pattern is a late-morning peak. Averaged over the four homes, the washer is most often on at 10:00 (9.5% of minutes), then at 11:00 and 9:00. Houses 1 to 3 give the same peak without House 5. House 1 almost never runs the washer after 6 pm.
 
**Evenings.** House 2 has a second period of use from about 3 pm to 9 pm, at roughly 4% to 8% of minutes. House 5 has an evening peak at 7 pm (8.1%). House 3 has some evening use, but less than House 2.
 
**Days.** The day-of-week pattern is not consistent. Houses 1 and 3 use the washer most early in the week and least on Saturday. House 2 is roughly flat across the week. House 5 is the only home that peaks at weekends. Averaged over the four homes, Saturday is the busiest day, but that result is driven by House 5. Without House 5, Saturday is the quietest day. The day-of-week pattern should not be relied on from these four homes.
 
**Overnight.** House 5 shows washer use between midnight and 4 am, at about 3% to 5% of minutes, which the other homes rarely show. This is unusual for a washer and suggests the channel may be picking up other loads, which fits the House 5 concerns above.
 
These are patterns across four homes. They do not show why households do their laundry at those times.
 
## Requirement 3: estimating washer power
 
### Set-up
 
- **Training:** Houses 1, 2 and 3, 2,050,421 usable minutes.
- **Test:** House 5, 706,639 usable minutes. House 5 is never used for training.
- **Period:** the common period above.
- **Model:** gradient boosting regressor with 8 inputs (README.md, Step 3).
### Results on House 5
 
From `outputs/req3_metrics.csv`:
 
| Method | MAE, all minutes (W) | RMSE (W) | MAE when on (W) | Energy error (%) | On precision | On recall | On F1 |
|---|---|---|---|---|---|---|---|
| Always off | 17.1 | 135.1 | 267.7 | −100.0 | 0.000 | 0.000 | 0.000 |
| Usage profile | 27.0 | 134.1 | 250.1 | −17.5 | 0.082 | 0.514 | 0.141 |
| Gradient boosting | 24.8 | 130.3 | 244.5 | −19.1 | 0.202 | 0.316 | 0.247 |
 
Over the test period, the washer used 201.9 kWh. The model estimated 163.4 kWh, and the usage profile estimated 166.7 kWh.
 
### Failure cases
 
From `outputs/req3_failure_check.csv`:
 
| Minutes | Count | Median whole-house power (W) | Share over 1 kW |
|---|---|---|---|
| False alarm (model says on, washer off) | 52,031 | 1,504 | 59.7% |
| Miss (washer on, model says off) | 28,574 | 741 | 26.6% |
| Correct on (both on) | 13,193 | 2,419 | 75.9% |
 
**False alarms** happen mostly when the whole house is drawing a lot of power. Six in ten are above 1 kW, so the model appears to treat high total load as a sign that the washer is running. Other high-power appliances, such as a kettle, heater, oven or dryer, would produce this pattern.
 
**Misses** happen mostly when the whole house is drawing little power, with a median of 741 W. A likely explanation is that House 5's washer draws much less than the training washers. Its median peak is about a quarter of theirs, so the washer's share of the total is small. This is a likely explanation rather than something I have tested.
 
### Interpretation
 
The model beats the usage-profile baseline on every metric except recall. Its overall MAE is lower (24.8 W against 27.0 W), its RMSE is lower (130.3 W against 134.1 W), and its on-precision (0.20 against 0.08) and F1 (0.25 against 0.14) are both higher. The profile finds more of the washing (recall 0.51 against 0.32), but most of its on-calls are wrong.
 
Against always-off, the model does better on RMSE (130.3 W against 135.1 W) and on error during washing (244.5 W against 267.7 W). It does worse on overall MAE (24.8 W against 17.1 W). Always-off wins on overall MAE because the washer is off for about 94% of the minutes, so predicting zero is almost always close. Overall MAE therefore says little about whether a model finds the washer at all. The RMSE gain of about 4% is modest.
 
On House 5 the model is not reliable. It says the washer is on for 65,224 minutes, but it really was on for 41,767. About 80% of its on-calls are wrong, and it finds about a third of the real washing minutes. Its energy estimate is 19% low. Neither baseline is good enough for energy totals on this home either.
 
The likely causes are the two described under failure cases: a washer signature in House 5 that differs from the training homes, and other high-power appliances in the whole-house total. Re-running with a different test home would show which matters more.
 