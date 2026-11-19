# Roadmap (draft for the author to revise)

This is a starting draft. Dates, partners and scope are for Joseph Egbemhenghe
to set; nothing here has been agreed with any outside party.

## Stage 1. Data (months 1 to 4)
- CDC's finalized annual series back to 2000 (AtlasPlus export), replacing the
  NNDSS weekly-table counts. Twelve years is the main limit on the learner.
- County-level counts, and breakdowns by sex and age group.
- Congenital syphilis.
- National Inpatient Sample: hospital stays coded A50-A53 (syphilis) and
  A55-A56, A74 (chlamydial infection), obtained under the AHRQ data use
  agreement, to add a severity and cost layer the case counts lack.
- Testing volume, if a usable source exists, to separate screening from incidence.

## Stage 2. Model (months 3 to 9)
- Sex and age structure; a higher-activity group so the model is not pinned
  to the epidemic threshold and scenario sizes become believable.
- Separate undiagnosed from diagnosed infection.
- Source every fixed rate from the literature.
- Re-test the fractional order on monthly or quarterly data, where memory
  effects are more likely to be identifiable.

## Stage 3. Learning (months 4 to 10)
- Retrain the learner on the longer series and add covariates.
- Explicit handling of reporting shocks such as 2020.
- Calibrated error bands (the current ones cover about 70%, not 80%).
- Fix the evaluation plan before each change, and keep the most recent years
  as an untouched test set.
- Target: beat "next year equals this year" one year ahead at state level.

## Stage 4. Users and review (months 9 to 18)
- Show the tool to epidemiologists at state or local health departments and
  record what they would need from it.
- Submit the method and backtest for peer review.

## Stage 5. Maintenance
- Annual data refresh and re-run of the backtest.
- Versioned releases with a DOI for each.
