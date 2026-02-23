from __future__ import annotations

from decimal import Decimal

from divrec.domain.models import CrestBucketSnapshot


_ALLOWED_BUCKETS: tuple[str, ...] = ("ISA", "SIPP", "GIA")


def validate_crest_snapshot(rows: list[CrestBucketSnapshot]) -> None:
    """Validate CREST bucket snapshot rules (v1).

    Raises ValueError("<CODE>") at the first encountered issue.
    """

    isins = {r.isin for r in rows}
    if len(isins) > 1:
        raise ValueError("MULTI_ISIN_CREST")

    seen: set[tuple[str, str]] = set()
    for r in rows:
        if r.crest_bucket not in _ALLOWED_BUCKETS:
            raise ValueError("BAD_BUCKET")

        key = (r.isin, r.crest_bucket)
        if key in seen:
            raise ValueError("DUPLICATE_BUCKET_ROW")
        seen.add(key)

        if not isinstance(r.shares, int) or r.shares < 0:
            raise ValueError("BAD_SHARES")

        if not isinstance(r.dividend_per_share, Decimal) or r.dividend_per_share < 0:
            raise ValueError("BAD_RATE")
        if not isinstance(r.cash_credited, Decimal) or r.cash_credited < 0:
            raise ValueError("BAD_CASH")

    buckets_present = {r.crest_bucket for r in rows}
    expected = set(_ALLOWED_BUCKETS)
    if buckets_present != expected:
        raise ValueError("MISSING_BUCKET")

    rate0 = rows[0].dividend_per_share
    for r in rows[1:]:
        if r.dividend_per_share != rate0:
            raise ValueError("RATE_MISMATCH_ACROSS_BUCKETS")