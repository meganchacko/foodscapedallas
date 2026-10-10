# Data

`obesity.csv` is the UCI dataset "Estimation of Obesity Levels Based On Eating Habits and Physical Condition" (2,111 rows), downloaded unchanged from https://archive.ics.uci.edu/static/public/544/data.csv.

- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Citation:** Estimation of Obesity Levels Based On Eating Habits and Physical Condition [Dataset]. (2019). UCI Machine Learning Repository. https://doi.org/10.24432/C5H31Z
- **Paper:** Palechor, F. M., & De la Hoz Manotas, A. (2019). Dataset for estimation of obesity levels based on eating habits and physical condition in individuals from Colombia, Peru and Mexico. *Data in Brief*.
- **SHA-256:** `28b6991062855d3d15642e38b1aa9d1b32fb7abbb5abf5b096f1868cd706154b`

**Important:** per the dataset page, 77% of the rows were generated synthetically (SMOTE, to balance the classes) and 23% came from real survey responses. The label (`NObeyesdad`) was assigned from each person's BMI, which is why height and weight must not be model inputs.

The file is committed so training is reproducible and doesn't depend on UCI's servers being up.
