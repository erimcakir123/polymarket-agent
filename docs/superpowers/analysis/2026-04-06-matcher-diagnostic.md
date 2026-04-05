# Matcher Diagnostic — 2026-04-05 22:44 UTC

## Summary

- Scout entries in 2h window: **34**
- Polymarket markets in 2h window: **22**
- Matched: **3**
- Unmatched: **19**
- Match rate: **13.6%**

## Unmatched by category

| Category | Count | Description |
|---|---|---|
| `fuzzy_name_mismatch_candidate` | 19 | Both teams exist as a head-to-head market; matcher *should* have found a scout entry but didn't. **Likely fuzzy-matching gap.** |

## Samples per category

### `fuzzy_name_mismatch_candidate` (19 cases)

- `nhl-nj-mon-2026-04-05                              | Devils vs. Canadiens`
- `bra2-ath-afc-2026-04-05-ath                        | Will Athletic Club win on 2026-04-05?`
- `bra2-ath-afc-2026-04-05-afc                        | Will América FC win on 2026-04-05?`
- `bra-mir-bra-2026-04-05-mir                         | Will Mirassol FC win on 2026-04-05?`
- `bra-mir-bra-2026-04-05-bra                         | Will Red Bull Bragantino win on 2026-04-05?`

## Scout entries without a Polymarket match

Out of 34 scout entries in the 2h window, **31** have no Polymarket counterpart. These are either niche leagues Polymarket doesn't list, or matcher-side fuzzy failures (if Polymarket DID list the match).

- `[basketball]` Cleveland Cavaliers vs Indiana Pacers @ 2026-04-05T22:00
- `[basketball]` Minnesota Timberwolves vs Charlotte Hornets @ 2026-04-05T23:00
- `[basketball]` New Orleans Pelicans vs Orlando Magic @ 2026-04-05T23:00
- `[basketball]` Dallas Mavericks vs Los Angeles Lakers @ 2026-04-05T23:30
- `[hockey]` Ottawa Senators vs Carolina Hurricanes @ 2026-04-05T21:00
- `[hockey]` Montreal Canadiens vs New Jersey Devils @ 2026-04-05T23:00
- `[soccer]` Bahia vs Palmeiras @ 2026-04-05T22:30
- `[soccer]` Corinthians vs Internacional @ 2026-04-05T22:30
- `[soccer]` Mirassol vs Red Bull Bragantino @ 2026-04-05T23:00
- `[soccer]` Grêmio vs Remo @ 2026-04-05T23:30
- `[soccer]` Novorizontino vs CRB @ 2026-04-05T21:00
- `[soccer]` Athletic vs América Mineiro @ 2026-04-05T23:00
- `[soccer]` Botafogo-SP vs São Bernardo @ 2026-04-05T23:30
- `[soccer]` River Plate vs Belgrano (Córdoba) @ 2026-04-05T21:00
- `[soccer]` Central Córdoba (Santiago del Estero) vs Newell's Old Boys @ 2026-04-05T23:30
- `[soccer]` Cúcuta Deportivo vs América de Cali @ 2026-04-05T21:00
- `[soccer]` Universidad de Chile vs La Serena @ 2026-04-05T22:00
- `[soccer]` Universitario de Vinto vs The Strongest @ 2026-04-05T21:15
- `[soccer]` Liverpool vs Deportivo Maldonado @ 2026-04-05T21:30
- `[soccer]` Macará vs Aucas @ 2026-04-05T23:10
- ... and 11 more

## Conclusion

**19** markets are candidates for a matcher patch. These are head-to-head markets where Polymarket and the scout both *should* know the teams but fuzzy matching failed. Review the `fuzzy_name_mismatch_candidate` samples above and open a follow-up matcher patch plan.
