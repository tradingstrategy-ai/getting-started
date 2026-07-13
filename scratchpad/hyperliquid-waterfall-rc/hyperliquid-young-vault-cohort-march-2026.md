# Hyperliquid young vault cohort, March 2026

This note investigates whether the spike in age-ramp eligible vaults around March 2026 was caused by suspicious Hyperliquid vault data, missing Trading Strategy rows, or a real cohort effect.

The short conclusion is that the main March 2026 spike does not look like ordinary missing local rows. It looks more like a cohort of young vaults whose local history begins together at zero TVL, and which then pass the notebook's minimum age gate together.

## Context

The notebook under investigation is:

- `03-backtest-25000-initial-capital.ipynb`

The strategy uses an `age_ramp` signal. In the current notebook settings:

- `min_age = 0.075` years, about 27.4 days
- `age_ramp_period = 0.75` years

The number of age-eligible vaults jumped around this period:

| Date | Age-included pair count |
| --- | ---: |
| 2026-03-07 | 89 |
| 2026-03-08 | 89 |
| 2026-03-09 | 98 |
| 2026-03-10 | 98 |
| 2026-03-11 | 98 |
| 2026-03-12 | 98 |

The broader trading pair universe stayed flat at 120 pairs, so this was not caused by a sudden increase in locally available trading pairs.

## Local Trading Strategy data

The relevant raw local data source was:

- `~/.cache/tradingstrategy/vaults/downloads/vault-price-history.parquet`

The young vaults added to the raw signal set around 2026-03-10 included:

| Vault | Local first row | Local missing days | Max local gap | First local TVL |
| --- | --- | ---: | ---: | ---: |
| AI ATM | 2026-02-09 | 0 | 1 day | 0.0 |
| Orion | 2026-02-09 | 0 | 1 day | 0.0 |
| Trader D | 2026-02-09 | 0 | 1 day | 0.0 |
| BredoStrategy | 2026-02-09 | 0 | 1 day | 0.0 |
| DaoScience Quant | 2026-02-09 | 0 | 1 day | 0.0 |

These vaults do not show local daily gaps after their first observed row. The suspicious common feature is instead that they all start on the same local date with zero TVL.

Because the age ramp currently counts age from the first observed row, these vaults start ageing from a zero-TVL discovery or launch row. Around 2026-03-09 and 2026-03-10 they cross the `min_age` threshold together, creating a cohort effect.

## Hyperliquid API cross-reference

The Hyperliquid API was checked with the official `vaultDetails` info endpoint:

- <https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint>

The API recognised the queried vault addresses and returned vault metadata such as:

- `allowDeposits`
- `isClosed`
- `followers`
- `leaderFraction`
- `leaderCommission`
- `apr`
- `maxDistributable`
- `maxWithdrawable`
- portfolio history periods such as `day`, `week`, `month`, and `allTime`

For the young cohort, the current Hyperliquid API generally confirms that the vaults exist. However, the API's `allTime` portfolio history does not always start as early as the local Trading Strategy data.

Examples:

| Vault | Local first row | Hyperliquid API all-time first point | Observation |
| --- | --- | --- | --- |
| AI ATM | 2026-02-09 | 2026-03-04 | API history starts later than local data |
| DaoScience Quant | 2026-02-09 | 2026-02-18 | API history starts later than local data |
| Crypto Plaza Relative Momentum Edge | 2025-05-28 | 2025-05-28 | API and local start dates match |
| Titan Vault | 2025-05-21 | 2025-05-21 | API and local start dates match |

This means Hyperliquid's current `vaultDetails` all-time portfolio series is useful as a current-state and sanity-check endpoint, but it is not a perfect full-history comparator for vault inception.

## Suspicious vaults

### Dinoshi

`Dinoshi` looks genuinely suspicious and should be excluded or flagged by data quality logic.

Observed issues:

- Local first row: 2026-02-09
- Local last row: 2026-04-10
- Local data has only about 60 days of history
- Hyperliquid currently reports `isClosed: true`
- TVL moved sharply around the March cohort date
- Local TVL was about 2,300 on 2026-03-09 and about 8,662 on 2026-03-10

This vault should not be treated the same way as an active, continuously observable vault.

### C.A.T

`C.A.T` is also noisy, but it was removed around this point rather than added.

Observed issues:

- Many missing local days
- Max local gap around 7 days
- Very large early share-price move
- TVL fell below the strategy threshold around 2026-03-10

This makes it a data-quality concern, but it is not the primary cause of the March young-vault eligibility spike.

### Crypto Plaza Relative Momentum Edge and Titan Vault

These two vaults were involved in selection churn around the same date, but they are not part of the young 2026-02-09 cohort.

They are older vaults with sparse older local history. Their Hyperliquid API all-time first points match the local first dates, so they do not point to the same young-vault age-gate issue.

## Interpretation

The March 2026 spike appears to be mainly caused by the age gate, not by missing rows in local Trading Strategy data.

The mechanism is:

1. Several vaults first appear locally on 2026-02-09.
2. Their first local TVL is zero.
3. The age ramp counts from the first observed row.
4. Roughly 27.4 days later, they pass `min_age` together.
5. This increases the number of age-eligible vaults around 2026-03-09 and 2026-03-10.

This is not necessarily a data gap bug, but it is a modelling problem. A zero-TVL discovery row is a weak definition of when a vault became investable.

## Recommended changes

Use a stronger vault-age and data-quality definition for Hyperliquid vaults.

Suggested filters:

- Calculate vault age from the first meaningful TVL point, not the first observed row.
- Define the first meaningful point as the first day where TVL is above a minimum floor, or the first day of sustained non-zero TVL.
- Exclude vaults whose local history ends before the backtest period being evaluated.
- Exclude or down-rank vaults that Hyperliquid currently reports as `isClosed: true`.
- Require `allowDeposits = true` where available.
- Reject or flag vaults with extreme early share-price moves.
- Require a minimum number of consecutive daily samples after first meaningful TVL.
- Add deterministic tie-breaking when many age-ramp signals are equal.

The most important change is to stop ageing vaults from a zero-TVL first row. That would reduce the artificial cohort effect and make the strategy less sensitive to scraper discovery dates.
