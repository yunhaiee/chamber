| Person | Kind | Box passed | Median box time | Claude passed | d1 priv min-max | d1 judgment max |
|---|---|---|---|---|---|---|
| maya | summarize_deposition | 10/12 | 3215ms | - | 0.94-0.96 | 0.29 |
| maya | extract_dates | 12/12 | 466ms | - | 0.94-0.97 | 0.08 |
| maya | privilege_tag | 8/12 | 232ms | - | 0.05-0.94 | 0.67 |
| maya | draft_letter | 12/12 | 1781ms | - | 0.73-0.75 | 0.13 |
| maya | public_research | 0/12 | 3216ms | 11/12 | 0.12-0.41 | 0.48 |
| maya | advice | not graded | - | - | 0.12-0.80 | 0.97 |
| daniel | summarize_instrument | 11/12 | 2586ms | - | 0.89-0.94 | 0.10 |
| daniel | extract_beneficiaries | 12/12 | 545ms | - | 0.91-0.93 | 0.37 |
| daniel | compute_distribution | 0/12 | 795ms | - | 0.90-0.91 | 0.20 |
| daniel | draft_client_letter | 12/12 | 1418ms | - | 0.86-0.89 | 0.22 |
| daniel | public_research | 0/12 | 1407ms | 12/12 | 0.10-0.65 | 0.51 |
| daniel | advice | not graded | - | - | 0.15-0.39 | 0.91 |

Privileged scored public by d1 alone at 0.30: 0 of 92
Lowest privileged score: 0.64. Advice judgment 0.70-0.97; everything else max 0.67
d1 chose the right kind: 144 of 144
Public research false alarms at 0.30: 5 of 24
Depositions 1-7, runs passed: [3, 3, 2, 3, 3, 3, 3] of 3 each
Twist failed: 10 of 10
Leak test on bench payloads: 0 hits over 48 payloads
