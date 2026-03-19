# Self-Improvement Report
_Generated: 2026-03-19 18:19 UTC_

## Core Metrics
| Metric | Value |
|--------|-------|
| Total predictions | 5 |
| Resolved | 138 |
| Win rate | 93.5% |
| Brier score | 0.1385 |
| Avg prediction error | 0.353 |
| Avg edge (trades) | 0.160 |

## By Category
| Category | Count | Win Rate | Brier | Avg Error |
|----------|-------|----------|-------|-----------|
| unknown | 138 | 93% | 0.138 | 0.353 |

## By Confidence
| Confidence | Count | Win Rate | Brier | Avg Error |
|------------|-------|----------|-------|-----------|
| unknown | 138 | 93% | 0.138 | 0.353 |

## By Edge Range
| Range | Count | Win Rate | Brier | Avg Error |
|-------|-------|----------|-------|-----------|
| 0-5% | 71 | 99% | 0.127 | 0.342 |
| 10-15% | 11 | 91% | 0.182 | 0.405 |
| 15%+ | 34 | 85% | 0.145 | 0.364 |
| 5-10% | 22 | 91% | 0.142 | 0.346 |

## Proposed Experiment
- **Parameter:** `edge.min_edge`
- **Current:** `0.06`
- **Proposed:** `0.05`
- **Reason:** Win rate 93% is strong. Lowering min_edge from 0.06 to 0.05 to capture more opportunities.
