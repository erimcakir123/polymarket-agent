# Polymarket Bimodal Classification — 2026-05-23

## Methodology

- **Source**: Polymarket public APIs (`gamma-api.polymarket.com/markets` + `clob.polymarket.com/prices-history`).
- **CRITICAL CONSTRAINT**: Public price-history API floor is **60 seconds**. Sub-minute (5s) tick data is NOT available via public endpoints.
- **Adapted bands**:
  - **instant** = >=30% drop within <=60s (single 1-min bar) — SL polling at 5s CANNOT catch reliably
  - **borderline** = 61-300s (2-5 bars) — SL may catch
  - **kademeli** = >300s — SL catches reliably
- **Sampling**: Up to 15 markets per (sport_tag × market_type) cell, filtered for closed + volume>=50, sorted by volume desc.
- **Decision rule**:
  - BIMODAL if instant>=30% OR median_drop_window<=60s
  - NON_BIMODAL if kademeli>=60% AND instant<20%
  - Else AMBIGUOUS (defaults to BIMODAL for safety)

## Per-Cell Summary

| Sport | Market | n | instant% | borderline% | kademeli% | no_sig_drop% | median_window_s | decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| mlb | moneyline | 14 | 0.0 | 0.0 | 78.6 | 21.4 | 1379 | **NON_BIMODAL** |
| mlb | nrfi | 13 | 0.0 | 15.4 | 69.2 | 15.4 | 959 | **NON_BIMODAL** |
| mlb | run_line | 15 | 0.0 | 6.7 | 93.3 | 0.0 | 1080 | **NON_BIMODAL** |
| mlb | totals | 15 | 0.0 | 13.3 | 73.3 | 13.3 | 1080 | **NON_BIMODAL** |
| nba | 1h_moneyline | 1 | 0.0 | 0.0 | 100.0 | 0.0 | 959 | **INSUFFICIENT_DATA** |
| nba | moneyline | 1 | 0.0 | 0.0 | 100.0 | 0.0 | 7188 | **INSUFFICIENT_DATA** |
| nba | spread | 8 | 0.0 | 0.0 | 100.0 | 0.0 | 4081 | **NON_BIMODAL** |
| nba | totals | 9 | 0.0 | 0.0 | 66.7 | 33.3 | 2760 | **NON_BIMODAL** |
| wnba | moneyline | 3 | 0.0 | 0.0 | 100.0 | 0.0 | 4260 | **INSUFFICIENT_DATA** |
| wnba | spread | 8 | 12.5 | 37.5 | 50.0 | 0.0 | 390 | **AMBIGUOUS_DEFAULT_BIMODAL** |
| wnba | totals | 9 | 0.0 | 11.1 | 88.9 | 0.0 | 2219 | **NON_BIMODAL** |
| nhl | moneyline | 1 | 0.0 | 0.0 | 100.0 | 0.0 | 2579 | **INSUFFICIENT_DATA** |
| nhl | spread | 1 | 0.0 | 0.0 | 100.0 | 0.0 | 2103 | **INSUFFICIENT_DATA** |
| nhl | totals | 4 | 0.0 | 0.0 | 100.0 | 0.0 | 5999 | **INSUFFICIENT_DATA** |
| atp | first_set_winner | 15 | 0.0 | 6.7 | 73.3 | 20.0 | 2098 | **NON_BIMODAL** |
| atp | match_total_games | 15 | 0.0 | 6.7 | 40.0 | 53.3 | 5400 | **AMBIGUOUS_DEFAULT_BIMODAL** |
| atp | moneyline | 15 | 0.0 | 0.0 | 66.7 | 33.3 | 4892 | **NON_BIMODAL** |
| atp | set_handicap | 12 | 0.0 | 0.0 | 66.7 | 33.3 | 6002 | **NON_BIMODAL** |
| atp | set_totals | 15 | 0.0 | 13.3 | 60.0 | 26.7 | 3585 | **NON_BIMODAL** |
| wta | first_set_winner | 9 | 0.0 | 0.0 | 66.7 | 33.3 | 2706 | **NON_BIMODAL** |
| wta | match_total_games | 15 | 0.0 | 0.0 | 66.7 | 33.3 | 1503 | **NON_BIMODAL** |
| wta | moneyline | 14 | 0.0 | 0.0 | 71.4 | 28.6 | 2336 | **NON_BIMODAL** |
| wta | set_handicap | 11 | 0.0 | 0.0 | 54.5 | 45.5 | 7500 | **AMBIGUOUS_DEFAULT_BIMODAL** |
| wta | set_totals | 15 | 6.7 | 0.0 | 53.3 | 40.0 | 4199 | **AMBIGUOUS_DEFAULT_BIMODAL** |

## Recommended `bimodal_market_types` per sport

```python
# Paste into sport_rules.py
BIMODAL_MARKET_TYPES = {
    "atp": ["match_total_games"],
    "wnba": ["spread"],
    "wta": ["set_handicap", "set_totals"],
}
```

## Cells with insufficient data (n<5)

- nba / 1h_moneyline: n=1
- nba / moneyline: n=1
- wnba / moneyline: n=3
- nhl / moneyline: n=1
- nhl / spread: n=1
- nhl / totals: n=4

## Sample slugs per cell

### mlb / moneyline (n=14)
- `mlb-pit-tor-2026-05-22`
- `mlb-min-bos-2026-05-22`
- `mlb-hou-chc-2026-05-22`
- `mlb-tb-nyy-2026-05-22`
- `mlb-col-ari-2026-05-22`
- _...+9 more_

### mlb / nrfi (n=13)
- `mlb-cws-sf-2026-05-22-nrfi`
- `mlb-cle-phi-2026-05-22-nrfi`
- `mlb-hou-chc-2026-05-22-nrfi`
- `mlb-nym-mia-2026-05-22-nrfi`
- `mlb-lad-mil-2026-05-22-nrfi`
- _...+8 more_

### mlb / run_line (n=15)
- `mlb-cle-phi-2026-05-22-spread-home-1pt5`
- `mlb-wsh-atl-2026-05-22-spread-home-1pt5`
- `mlb-tex-laa-2026-05-22-spread-away-1pt5`
- `mlb-pit-tor-2026-05-22-spread-home-1pt5`
- `mlb-lad-mil-2026-05-22-spread-home-3pt5`
- _...+10 more_

### mlb / totals (n=15)
- `mlb-hou-chc-2026-05-22-total-7pt5`
- `mlb-cle-phi-2026-05-22-total-6pt5`
- `mlb-det-bal-2026-05-22-total-8pt5`
- `mlb-hou-chc-2026-05-22-total-6pt5`
- `mlb-cle-phi-2026-05-22-total-7pt5`
- _...+10 more_

### nba / 1h_moneyline (n=1)
- `nba-okc-sas-2026-05-22-1h-moneyline`

### nba / moneyline (n=1)
- `nba-okc-sas-2026-05-22`

### nba / spread (n=8)
- `nba-okc-sas-2026-05-22-spread-home-2pt5`
- `nba-okc-sas-2026-05-22-spread-home-1pt5`
- `nba-okc-sas-2026-05-22-spread-home-5pt5`
- `nba-okc-sas-2026-05-22-spread-away-3pt5`
- `nba-okc-sas-2026-05-22-spread-away-9pt5`
- _...+3 more_

### nba / totals (n=9)
- `nba-okc-sas-2026-05-22-total-217pt5`
- `nba-okc-sas-2026-05-22-total-219pt5`
- `nba-okc-sas-2026-05-22-total-216pt5`
- `nba-okc-sas-2026-05-22-total-215pt5`
- `nba-okc-sas-2026-05-22-total-207pt5`
- _...+4 more_

### wnba / moneyline (n=3)
- `wnba-gsv-ind-2026-05-22`
- `wnba-conn-sea-2026-05-22`
- `wnba-dal-atl-2026-05-22`

### wnba / spread (n=8)
- `wnba-dal-atl-2026-05-22-spread-home-5pt5`
- `wnba-gsv-ind-2026-05-22-spread-home-6pt5`
- `wnba-dal-atl-2026-05-22-spread-home-4pt5`
- `wnba-gsv-ind-2026-05-22-spread-home-7pt5`
- `wnba-conn-sea-2026-05-22-spread-home-1pt5`
- _...+3 more_

### wnba / totals (n=9)
- `wnba-gsv-ind-2026-05-22-total-168pt5`
- `wnba-dal-atl-2026-05-22-total-173pt5`
- `wnba-gsv-ind-2026-05-22-total-167pt5`
- `wnba-gsv-ind-2026-05-22-total-166pt5`
- `wnba-dal-atl-2026-05-22-total-172pt5`
- _...+4 more_

### nhl / moneyline (n=1)
- `nhl-las-col-2026-05-22`

### nhl / spread (n=1)
- `nhl-las-col-2026-05-22-spread-home-1pt5`

### nhl / totals (n=4)
- `nhl-las-col-2026-05-22-total-6pt5`
- `nhl-las-col-2026-05-22-total-5pt5`
- `nhl-las-col-2026-05-22-total-4pt5`
- `nhl-las-col-2026-05-22-total-7pt5`

### atp / first_set_winner (n=15)
- `atp-buse-paul-2026-05-23-first-set-winner-Buse-vs-Paul`
- `atp-buse-paul-2026-05-23-first-set-winner-Buse-vs-Paul`
- `atp-ruud-navone-2026-05-22-first-set-winner-Ruud-vs-Navone`
- `atp-gojo-rodiono-2026-05-22-first-set-winner-Gojo-vs-Rodionov`
- `atp-tien-bublik-2026-05-22-first-set-winner-Tien-vs-Bublik`
- _...+10 more_

### atp / match_total_games (n=15)
- `atp-minaur-paul-2026-05-22-match-total-22pt5`
- `atp-minaur-paul-2026-05-22-match-total-23pt5`
- `atp-ivashka-biryuko-2026-05-23-match-total-21pt5`
- `atp-tien-bublik-2026-05-22-match-total-21pt5`
- `atp-kovacev-buse-2026-05-22-match-total-21pt5`
- _...+10 more_

### atp / moneyline (n=15)
- `atp-tien-bublik-2026-05-22`
- `atp-minaur-paul-2026-05-22`
- `atp-ruud-navone-2026-05-22`
- `atp-herbert-riedi-2026-05-22`
- `atp-ivashka-biryuko-2026-05-23`
- _...+10 more_

### atp / set_handicap (n=12)
- `atp-ruud-navone-2026-05-22-set-handicap-home-1pt5`
- `atp-gentzsc-safiull-2026-05-22-set-handicap-away-1pt5`
- `atp-kovacev-buse-2026-05-22-set-handicap-away-1pt5`
- `atp-herbert-riedi-2026-05-22-set-handicap-away-1pt5`
- `atp-minaur-paul-2026-05-22-set-handicap-home-1pt5`
- _...+7 more_

### atp / set_totals (n=15)
- `atp-nedic-sanchis-2026-05-23-first-set-total-8pt5`
- `atp-nedic-sanchis-2026-05-23-first-set-total-9pt5`
- `atp-gojo-rodiono-2026-05-22-set-totals-2pt5`
- `atp-minaur-paul-2026-05-22-set-totals-2pt5`
- `atp-tien-bublik-2026-05-22-set-totals-2pt5`
- _...+10 more_

### wta / first_set_winner (n=9)
- `wta-mboko-cristia-2026-05-22-first-set-winner-Mboko-vs-Cristian`
- `wta-mboko-navarro-2026-05-23-first-set-winner-Mboko-vs-Navarro`
- `wta-kalinin-marcink-2026-05-23-first-set-winner-Kalinina-vs-Marcinko`
- `wta-navarro-annli-2026-05-22-first-set-winner-Navarro-vs-Li`
- `wta-teichma-marcink-2026-05-22-first-set-winner-Teichmann-vs-Marcinko`
- _...+4 more_

### wta / match_total_games (n=15)
- `wta-mboko-navarro-2026-05-23-match-total-21pt5`
- `wta-tan-fruhvir-2026-05-22-match-total-21pt5`
- `wta-mboko-cristia-2026-05-22-match-total-22pt5`
- `wta-navarro-annli-2026-05-22-match-total-21pt5`
- `wta-kalinin-marcink-2026-05-23-match-total-22pt5`
- _...+10 more_

### wta / moneyline (n=14)
- `wta-mboko-cristia-2026-05-22`
- `wta-mboko-navarro-2026-05-23`
- `wta-navarro-annli-2026-05-22`
- `wta-zavatsk-bronzet-2026-05-22`
- `wta-kuderme-wan-2026-05-22`
- _...+9 more_

### wta / set_handicap (n=11)
- `wta-sasnovi-ribera-2026-05-22-set-handicap-home-1pt5`
- `wta-mboko-cristia-2026-05-22-set-handicap-home-1pt5`
- `wta-mboko-navarro-2026-05-23-set-handicap-home-1pt5`
- `wta-teichma-marcink-2026-05-22-set-handicap-away-1pt5`
- `wta-marista-quevedo-2026-05-22-set-handicap-away-1pt5`
- _...+6 more_

### wta / set_totals (n=15)
- `wta-mboko-cristia-2026-05-22-first-set-total-8pt5`
- `wta-mboko-navarro-2026-05-23-first-set-total-8pt5`
- `wta-zavatsk-bronzet-2026-05-22-set-totals-2pt5`
- `wta-kuderme-wan-2026-05-22-first-set-total-8pt5`
- `wta-kuderme-wan-2026-05-22-first-set-total-10pt5`
- _...+10 more_
