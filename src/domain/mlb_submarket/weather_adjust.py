"""Weather adjustment for HR rate (wind, temperature, humidity).

SPEC-R Plan 2 T6. Empirical multipliers based on:
- Wind: +1% per mph toward CF, max +/-20% at +/-20mph.
- Temperature: 60°F baseline; +1.5% per 10°F above, symmetric below.
- Humidity: high humidity -> -0.5% per 10% above 50% (drag increases).

Output clipped to [0.5, 1.5] to bound model risk.
"""
from __future__ import annotations

_MIN_MULT = 0.5
_MAX_MULT = 1.5


def weather_hr_multiplier(wind_mph_to_cf: float, temp_f: float, humidity_pct: float) -> float:
    """Compute HR rate multiplier from weather conditions.

    Args:
        wind_mph_to_cf: wind speed in mph, positive = blowing toward center field
            (HR-friendly), negative = blowing in (HR-suppressing).
        temp_f: ambient temperature in Fahrenheit.
        humidity_pct: relative humidity 0-100.

    Returns:
        Multiplier in [0.5, 1.5]. 1.0 = neutral.
    """
    wind_factor = 1.0 + 0.01 * wind_mph_to_cf        # +/-1% per mph
    temp_factor = 1.0 + 0.0015 * (temp_f - 60.0)     # +1.5% per 10°F above 60
    humid_factor = 1.0 - 0.0005 * max(0, humidity_pct - 50)  # -0.5% per 10% above 50
    mult = wind_factor * temp_factor * humid_factor
    return max(_MIN_MULT, min(_MAX_MULT, mult))
