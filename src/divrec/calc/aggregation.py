from __future__ import annotations

from decimal import Decimal

from divrec.domain.mapping import bucket_for_product
from divrec.domain.models import CreditLine, CrestBucket, InternalHolding

_ALL_BUCKETS: tuple[CrestBucket, CrestBucket, CrestBucket] = ("ISA", "SIPP", "GIA")


def aggregate_internal_shares_by_bucket(holdings: list[InternalHolding]) -> dict[CrestBucket, int]:
    totals: dict[CrestBucket, int] = {b: 0 for b in _ALL_BUCKETS}
    for h in holdings:
        totals[bucket_for_product(h.product_code)] += h.shares
    return totals


def aggregate_cash_by_bucket(lines: list[CreditLine]) -> dict[CrestBucket, Decimal]:
    totals: dict[CrestBucket, Decimal] = {b: Decimal("0.00") for b in _ALL_BUCKETS}
    for ln in lines:
        totals[ln.crest_bucket] += ln.cash_credited
    return totals