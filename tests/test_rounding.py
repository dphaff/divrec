from decimal import Decimal

import pytest

from divrec.calc.rounding import round_half_up


@pytest.mark.parametrize(
    "inp, places, expected",
    [
        (Decimal("0.004"), 2, Decimal("0.00")),
        (Decimal("0.005"), 2, Decimal("0.01")),
        (Decimal("1.004"), 2, Decimal("1.00")),
        (Decimal("1.005"), 2, Decimal("1.01")),
        (Decimal("1.015"), 2, Decimal("1.02")),
        (Decimal("-0.005"), 2, Decimal("-0.01")),
    ],
)
def test_round_half_up_2dp_cases(inp: Decimal, places: int, expected: Decimal) -> None:
    assert round_half_up(inp, places=places) == expected


def test_round_half_up_4dp_shares_rate_case() -> None:
    shares = Decimal("3")
    rate = Decimal("0.3333")  # 4dp
    raw = shares * rate       # 0.9999 exactly in Decimal
    assert raw == Decimal("0.9999")
    assert round_half_up(raw, places=2) == Decimal("1.00")


def test_round_half_up_handles_fewer_decimals() -> None:
    assert round_half_up(Decimal("1"), places=2) == Decimal("1.00")
    assert round_half_up(Decimal("1.2"), places=2) == Decimal("1.20")