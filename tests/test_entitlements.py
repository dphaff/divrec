from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from decimal import Decimal

from divrec.calc.aggregation import (
    aggregate_cash_by_bucket,
    aggregate_internal_shares_by_bucket,
)
from divrec.calc.entitlements import compute_client_credit_lines
from divrec.domain.models import InternalHolding


def _make_internal_holding(
    *,
    client_number: str,
    product_code: int,
    account_number: str,
    shares: int,
) -> InternalHolding:
    """
    Create InternalHolding instances in a way that won't break if the dataclass
    gains extra required fields later.

    Strategy:
    - populate known fields when present
    - for any other required fields with no default, fill with a reasonable dummy
    """
    if not is_dataclass(InternalHolding):
        # Fallback: assume constructor matches the v1 signature
        return InternalHolding(
            client_number=client_number,
            product_code=product_code,
            account_number=account_number,
            shares=shares,
        )

    provided = {
        "client_number": client_number,
        "product_code": product_code,
        "account_number": account_number,
        "shares": shares,
    }

    kwargs = {}
    for f in fields(InternalHolding):
        if f.name in provided:
            kwargs[f.name] = provided[f.name]
            continue

        if f.default is not MISSING:
            kwargs[f.name] = f.default
            continue

        if f.default_factory is not MISSING:  # type: ignore[comparison-overlap]
            kwargs[f.name] = f.default_factory()  # type: ignore[misc]
            continue

        # required, no default: fill minimal dummy values
        if f.type in (int,):
            kwargs[f.name] = 0
        elif f.type in (str,):
            kwargs[f.name] = ""
        else:
            # last-resort dummy
            kwargs[f.name] = None

    return InternalHolding(**kwargs)


def test_compute_client_credit_lines_cash_and_bucket_mapping_mixed_products() -> None:
    dps = Decimal("0.3333")

    holdings = [
        _make_internal_holding(
            client_number="C1", product_code=22, account_number="A1", shares=1
        ),  # ISA
        _make_internal_holding(
            client_number="C2", product_code=70, account_number="A2", shares=2
        ),  # SIPP
        _make_internal_holding(
            client_number="C3", product_code=97, account_number="A3", shares=15
        ),  # GIA
    ]

    lines = compute_client_credit_lines(
        holdings=holdings,
        run_id="RUN-1",
        isin="GB0000000001",
        record_date="2026-01-15",
        pay_date="2026-02-01",
        dividend_per_share=dps,
    )

    assert [ln.line_type for ln in lines] == ["CLIENT", "CLIENT", "CLIENT"]
    assert [ln.crest_bucket for ln in lines] == ["ISA", "SIPP", "GIA"]

    # Rounding edges with 0.3333:
    # 1 * 0.3333 = 0.3333 -> 0.33
    # 2 * 0.3333 = 0.6666 -> 0.67
    # 15 * 0.3333 = 4.9995 -> 5.00
    assert [ln.cash_credited for ln in lines] == [
        Decimal("0.33"),
        Decimal("0.67"),
        Decimal("5.00"),
    ]


def test_aggregate_internal_shares_by_bucket_sums_across_products_in_same_bucket() -> None:
    holdings = [
        _make_internal_holding(
            client_number="C1", product_code=22, account_number="A1", shares=10
        ),  # ISA
        _make_internal_holding(
            client_number="C2", product_code=25, account_number="A2", shares=5
        ),  # ISA
        _make_internal_holding(
            client_number="C3", product_code=70, account_number="A3", shares=7
        ),  # SIPP
    ]

    totals = aggregate_internal_shares_by_bucket(holdings)

    assert totals["ISA"] == 15
    assert totals["SIPP"] == 7
    assert totals["GIA"] == 0  # key must exist


def test_aggregate_cash_by_bucket_sums_rounded_cash_correctly() -> None:
    dps = Decimal("0.3333")
    holdings = [
        _make_internal_holding(
            client_number="C1", product_code=22, account_number="A1", shares=1
        ),  # ISA -> 0.33
        _make_internal_holding(
            client_number="C2", product_code=22, account_number="A2", shares=2
        ),  # ISA -> 0.67
        _make_internal_holding(
            client_number="C3", product_code=70, account_number="A3", shares=3
        ),  # SIPP -> 1.00 (0.9999 -> 1.00)
    ]

    lines = compute_client_credit_lines(
        holdings=holdings,
        run_id="RUN-2",
        isin="GB0000000002",
        record_date="2026-01-15",
        pay_date="2026-02-01",
        dividend_per_share=dps,
    )

    cash_totals = aggregate_cash_by_bucket(lines)

    assert cash_totals["ISA"] == Decimal("1.00")  # 0.33 + 0.67
    assert cash_totals["SIPP"] == Decimal("1.00")
    assert cash_totals["GIA"] == Decimal("0.00")  # key must exist