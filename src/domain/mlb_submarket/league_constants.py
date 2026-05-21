"""MLB league-average PA outcome rates (2023-2025 Fangraphs average).

SPEC-R Plan 2 T2. Source: Fangraphs splits.
"""

LEAGUE_PA_RATES: dict[str, float] = {
    "K": 0.225,            # strikeout
    "BB": 0.085,           # walk
    "HBP": 0.011,          # hit by pitch
    "HR": 0.030,           # home run
    "1B": 0.140,           # single
    "2B": 0.045,           # double
    "3B": 0.004,           # triple
    "OUT_IN_PLAY": 0.460,  # contact out (incl. groundouts, flyouts, lineouts)
}
# Sum check: 0.225+0.085+0.011+0.030+0.140+0.045+0.004+0.460 = 1.000
