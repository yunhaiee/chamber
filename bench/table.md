| Person | Kind | Box passed | Median box time | Claude passed | d1 priv min-max | d1 judgment max |
|---|---|---|---|---|---|---|
| maya | summarize_deposition | 1/12 | 5815ms | - | 0.94-0.96 | 0.29 |
| maya | extract_dates | 8/12 | 684ms | - | 0.94-0.97 | 0.08 |
| maya | privilege_tag | 5/12 | 444ms | - | 0.05-0.94 | 0.67 |
| maya | draft_letter | 12/12 | 2033ms | - | 0.73-0.75 | 0.13 |
| maya | public_research | 0/12 | 8922ms | 11/12 | 0.12-0.41 | 0.48 |
| maya | advice | not graded | - | - | 0.12-0.80 | 0.97 |
| daniel | summarize_instrument | 11/12 | 1471ms | - | 0.89-0.94 | 0.10 |
| daniel | extract_beneficiaries | 12/12 | 625ms | - | 0.91-0.93 | 0.37 |
| daniel | compute_distribution | 0/12 | 7556ms | - | 0.90-0.91 | 0.20 |
| daniel | draft_client_letter | 12/12 | 1392ms | - | 0.86-0.89 | 0.22 |
| daniel | public_research | 0/12 | 11446ms | 12/12 | 0.10-0.65 | 0.51 |
| daniel | advice | not graded | - | - | 0.15-0.39 | 0.91 |

Privileged scored public by d1 alone at 0.30: 4 of 96
Public research false alarms at 0.30: 5 of 24
Depositions 1-7, runs passed: [0, 0, 0, 1, 0, 0, 3] of 3 each
Twist failed: 8 of 10
Leak test on bench payloads: 0 hits over 24 payloads
