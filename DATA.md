
# Data
 
## The dataset
 
REFIT Electrical Load Measurements, from the University of Strathclyde (Murray et al., 2017).
 
- 20 homes in the UK, recorded over about two years (2013 to 2015).
- Readings are active power in watts, nominally taken every 8 seconds.
- Each home has a whole-house channel (`Aggregate`) and appliance channels (`Appliance1` to `Appliance9`). The mapping from channel to appliance is in `Refit.txt`, which comes with the dataset.
- The cleaned files add an `Issues` column. `Issues = 1` marks a reading that the dataset documentation flags as inconsistent with the whole-house total.
## Files used
 
| Requirement | Files | Period covered (UTC) |
|---|---|---|
| 1 | `RAW_House1_Part1.csv`, `RAW_House1_Part2.csv` | 2013-10-09 14:06:17 to 2015-07-10 11:56:32 (both files combined) |
| 2 and 3 | `CLEAN_House1`, `CLEAN_House2`, `CLEAN_House3`, `CLEAN_House5` | 2013-10-09 13:06 to 2015-05-28 08:05 (the period all four homes share) |
 
## Requirement 1: what the checks found
 
Across both raw House 1 files:
 
- **Rows.** The two files hold 8,518,763 rows in total. After removing repeated timestamps, 7,307,715 readings remain. 1,211,048 rows were removed as repeats, and 191,889 of the repeated timestamps appear in both files.
- **Order.** Both files are sorted by Unix time before they are combined.
- **Time between readings.** The nominal interval is 8 seconds, but the combined file is not evenly spaced. The most common gaps are 7 seconds (1,723,366 times), 2 seconds (1,229,144), 6 seconds (1,097,095), 8 seconds (762,820) and 13 seconds (452,585). About 51% of gaps (3,724,433) fall outside 6 to 8 seconds. Gaps longer than 60 seconds occur 4,040 times, and the longest is 3,594,414 seconds (about 41.6 days).
The 2-second and 13-second gaps probably come from combining two exports that are not sampled on exactly the same clock. Because the timing is irregular, the cleaning averages readings into one-minute bins instead of assuming a fixed 8-second grid.
 
## Cleaning rules
 
| Problem | Rule | Why |
|---|---|---|
| Timestamps | Unix time is the reference. The `Time` text is checked against it. | Unix time is unambiguous. |
| Order | Rows are sorted by time before anything else. | Some rows are out of order. |
| Repeated timestamps | Keep the Part 2 row. Within one file, keep the later row. | Part 1 can record an unavailable sensor as zero, so Part 2 is preferred when both files have the same moment. |
| Negative readings | Set to missing. | Power cannot be negative. |
| Whole-house above 20 kW, or appliance above 4 kW | Set to missing. | These are well above what a UK home draws. A kettle is about 3 kW. |
| Zeros | Kept. | A zero usually means the appliance is switched off. |
| Gaps of 2 minutes or fewer | Filled by a straight line between the readings either side. | Short gaps are most likely a few dropped readings. |
| Gaps longer than 2 minutes | Left empty and listed in `req1_outages.csv`. | Filling a long gap would invent load. |
| Resampling | One-minute mean, in UTC. | Matches the brief, and handles the irregular timing. |
 
## Remaining concerns
 
- **Irregular timing.** About half of the gaps between readings are outside 6 to 8 seconds, so the nominal 8-second spacing cannot be assumed. One-minute means reduce this problem but do not remove it.
- **Zeros in Part 1.** Zeros may hide unavailable sensors, which cannot be told apart from true off readings.
- **Judgement calls.** The impossible-value limits and the 2-minute fill are choices. Different values would change the counts.
- **Long gaps.** Gaps longer than 2 minutes stay empty, so some hours have no usable House 1 data.
## Data concerns for Requirements 2 and 3
 
- **Missing data.** Missing minutes range from 8.8% (House 5) to 25.4% (House 2). House 2 has a gap of 1,488.6 hours (about 62 days). Houses 1 and 3 share the same longest gap, 998.4 hours, which suggests a common outage.
- **Flagged minutes.** `Issues = 1` covers 1.4% to 7.8% of minutes. House 5 has the most, followed by House 3.
- **House 5's washer channel.** It reads exactly zero in only 52.6% of usable minutes, against 94% to 98% in the other homes. Its median cycle peak is 494 W, against 1,874 to 2,264 W elsewhere. The channel may not capture the washer in the same way as the other homes. This matters because House 5 is the test home in Requirement 3.
 
