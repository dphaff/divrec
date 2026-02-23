from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def round_half_up(value: Decimal, places: int = 2) -> Decimal:
    """
    Quantize `value` to `places` decimal places using HALF-UP rounding.

    - Uses Decimal quantize (never float).
    - Preserves sign for negative values.
    - Works for values with fewer decimals (pads with trailing zeros as needed).
    """
    if not isinstance(value, Decimal):
        raise TypeError("value must be a Decimal")
    if not isinstance(places, int):
        raise TypeError("places must be an int")

    # places=2 -> Decimal("0.01"); places=0 -> Decimal("1"); places=4 -> Decimal("0.0001")
    exponent = Decimal("1").scaleb(-places)
    return value.quantize(exponent, rounding=ROUND_HALF_UP)