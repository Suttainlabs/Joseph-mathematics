# Roadmap (draft for the author to revise)

This is a starting draft. Dates, partners and scope are for Joseph Egbemhenghe
to set; nothing here has been agreed with any outside party.

## Stage 1. Better data (months 1 to 4)
- Replace NNDSS weekly-table counts with CDC's finalized annual series
  (AtlasPlus export), extending back to 2000.
- Add county-level counts and breakdowns by sex and age group.
- Add congenital syphilis.
- Decide whether National Inpatient Sample data add anything; if so, obtain it
  under the AHRQ data use agreement.

## Stage 2. Better models (months 3 to 9)
- Time-varying contact and screening rates, including the 2020 disruption.
- Separate undiagnosed from diagnosed infection; use testing volume if available.
- Hierarchical (partial pooling) fit across states.
- Source every fixed rate from the literature.
- Uncertainty intervals by bootstrap or Bayesian fitting.
- Re-test the fractional order on monthly or quarterly data, where memory
  effects are more likely to be identifiable.
- Target: beat persistence on one-year-ahead state forecasts.

## Stage 3. Machine-learning component (months 6 to 12)
- Gradient-boosted or neural forecaster on the same data as a comparison.
- Hybrid: learn the residuals of the mechanistic model.
- Report all forecasters against the same backtest.

## Stage 4. Users and review (months 9 to 18)
- Show the tool to epidemiologists at state or local health departments and
  record what they would need from it.
- Submit the method and backtest for peer review.
- Enter forecasts in an open forecasting exercise if one exists for STIs.

## Stage 5. Maintenance
- Annual data refresh and re-run of the backtest.
- Versioned releases with a DOI for each.
