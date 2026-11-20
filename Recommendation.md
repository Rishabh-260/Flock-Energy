# Recommendation
 
## The opportunity
 
In the four homes studied, the washer is on for only 1.3% to 5.9% of usable minutes, and it runs about 5 to 12 times a week per home. Use is concentrated in the late morning: averaged over the four homes, the washer is most often on at 10:00. Houses 1 to 3 show the same peak without House 5. Evening use is much less common, but House 2 runs its washer from about 3 pm to 9 pm, and House 5 peaks at 7 pm. A utility could test an opt-in message or a delayed-start reminder that encourages households to run laundry outside the utility's high-demand window. That window should be agreed with the utility before the pilot (see below). The opportunity depends on when the window falls. If the utility's peak is in the morning, most of the homes studied are relevant. If it is in the evening, the relevant homes are House 2 and House 5, which both run washers in the evening, while House 1 almost never does. House 5's evening use should be checked against its washer channel before it is used to size the opportunity. Moving load away from a peak can reduce the demand the utility has to meet at that time. It does not reduce the energy a wash needs, so a pilot has to measure both.
 
Because each home washes only a few times a week, the amount of load that could move is small in each home. A pilot would need enough homes, and should target homes that wash most often.
 
## Suitable uses and limits of the model
 
The model is not yet suitable for individual households or for energy totals. On House 5, it misses about two-thirds of the minutes when the washer is running (recall 0.32). About 80% of its on-calls are wrong (precision 0.20). Its energy estimate is 19% low. It is also weaker than always-off on overall error. It could perhaps help rank homes for a metered pilot, but only after it has been tested on more homes.
 
## Limits
 
- **Overlapping signatures.** A whole-house reading adds up every appliance. A kettle, heater or dryer can look like the washer, and the failure analysis in RESULTS.md shows this happening.
- **Missing and flagged data.** Between 8.8% and 25.4% of minutes are missing in the selected homes, and between 1.4% and 7.8% are flagged. Gaps can change cycle counts.
- **Household differences.** The washer in House 5 draws about a quarter as much power at its peak as the washers in the other homes. A model trained on three homes does not transfer well to the fourth, and the House 5 channel should be checked before any results are trusted.
- **UK homes, not India.** The results should not transfer directly. Washing machines differ: front-loading machines are more common in the UK, while top-loading machines are widely used in India. Laundry habits differ too, and many households wash by hand or on a different schedule. Peak demand in India is often driven by air conditioning in summer, which is not a factor in these UK homes. Tariffs and the smart-meter data available also differ. Before offering anything locally, validate with Indian smart-meter data and labelled washer readings from a range of households.
