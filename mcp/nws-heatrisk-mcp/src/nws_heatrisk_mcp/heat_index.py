"""NWS heat-index regression (Rothfusz 1990).

The U.S. National Weather Service publishes its heat-index ("apparent
temperature") formula as the Rothfusz multiple regression equation, with
two adjustments applied at the low-humidity and high-humidity extremes.

Reference:
    https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml

The full procedure used in NWS products:

1. Compute a simplified average:
       HI_simple = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + RH * 0.094)
   averaged with T.
   If that value is below ~80 F, return it unchanged.

2. Otherwise, evaluate the Rothfusz regression in F + %RH:
       HI = -42.379
          +  2.04901523 * T
          + 10.14333127 * RH
          -  0.22475541 * T * RH
          -  0.00683783 * T**2
          -  0.05481717 * RH**2
          +  0.00122874 * T**2 * RH
          +  0.00085282 * T * RH**2
          -  0.00000199 * T**2 * RH**2

3. Low-humidity adjustment (RH < 13 % and 80 < T < 112):
       subtract ((13 - RH) / 4) * sqrt((17 - |T - 95|) / 17)

4. High-humidity adjustment (RH > 85 % and 80 < T < 87):
       add ((RH - 85) / 10) * ((87 - T) / 5)

All inputs and outputs are in Fahrenheit / percent.

Canonical NWS check values (from the WPC page above):
    T=80,  RH=40  -> ~80 F
    T=100, RH=50  -> ~119 F
    T=110, RH=40  -> ~136 F
"""

from __future__ import annotations

import math


def heat_index_f(temp_f: float, rh_percent: float) -> float:
    """NWS heat index in degrees Fahrenheit.

    Args:
        temp_f: Dry-bulb temperature, deg F.
        rh_percent: Relative humidity, 0-100.

    Returns:
        Apparent temperature, deg F, per the NWS Rothfusz regression
        with the standard low- and high-humidity adjustments.

    Raises:
        ValueError: if RH is outside [0, 100].
    """
    if rh_percent < 0 or rh_percent > 100:
        raise ValueError(f"rh_percent must be in [0, 100], got {rh_percent!r}")

    t = float(temp_f)
    rh = float(rh_percent)

    # Step 1: the simple average. This is what NWS uses when the
    # regression isn't warranted (cooler conditions).
    hi_simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    hi_avg = (hi_simple + t) / 2.0
    if hi_avg < 80.0:
        return hi_avg

    # Step 2: full Rothfusz regression.
    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )

    # Step 3: low-humidity adjustment.
    if rh < 13.0 and 80.0 <= t <= 112.0:
        hi -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t - 95.0)) / 17.0)

    # Step 4: high-humidity adjustment.
    if rh > 85.0 and 80.0 <= t <= 87.0:
        hi += ((rh - 85.0) / 10.0) * ((87.0 - t) / 5.0)

    return hi


def heat_index_category(hi_f: float) -> str:
    """NWS heat-index caution band for an apparent temperature.

    Bands per https://www.weather.gov/safety/heat-index :
        < 80     none
        80-90    Caution
        90-103   Extreme Caution
        103-124  Danger
        >= 125   Extreme Danger
    """
    if hi_f < 80.0:
        return "none"
    if hi_f < 90.0:
        return "Caution"
    if hi_f < 103.0:
        return "Extreme Caution"
    if hi_f < 125.0:
        return "Danger"
    return "Extreme Danger"
