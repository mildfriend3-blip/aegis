# AEGIS Adaptive Attack Report

The adaptive attacker mutates each attack and reports whether *any* variant still lands. A defence can read 0% statically and still fall to an attacker who searches.

## 1. Adaptive bypass rate by defence

| Defence | Bypass rate (lower=better) | Attacks |
|---|---|---|
| none | 100.0% | 17 |
| full |  17.6% | 17 |
| hardened |   0.0% | 17 |

## 2. What beats each defence

- **none**: original (17)
- **full**: output-encoding:base64 (2), payload-encoding:base64+output-encoding:base64 (1)
- **hardened**: nothing bypassed it.

## 3. Bypass rate by defence and objective

| Defence | destructive_sql | exfil_email | exfil_http | secret_leak_response |
|---|---|---|---|---|
| none | 100.0% | 100.0% | 100.0% | 100.0% |
| full |   0.0% |   0.0% |   0.0% | 100.0% |
| hardened |   0.0% |   0.0% |   0.0% |   0.0% |
