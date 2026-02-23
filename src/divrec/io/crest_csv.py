from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from divrec.domain.models import CrestBucketSnapshot


_REQUIRED_COLUMNS: tuple[str, ...] = (
    "isin",
    "record_date",
    "pay_date",
    "crest_bucket",
    "shares",
    "dividend_per_share",
    "cash_credited",
)


def _strip(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_crest_snapshot_csv(path: Path) -> list[CrestBucketSnapshot]:
    """Read a CREST bucket snapshot CSV into domain rows.

    Raises:
        ValueError("MISSING_COLUMN") if any required column is missing.
        ValueError("BAD_SHARES"|"BAD_RATE"|"BAD_CASH") for parse failures.
    """

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        fieldnames = [c.strip() for c in (reader.fieldnames or [])]
        missing = [c for c in _REQUIRED_COLUMNS if c not in fieldnames]
        if missing:
            raise ValueError("MISSING_COLUMN")

        out: list[CrestBucketSnapshot] = []
        for row in reader:
            isin = _strip(row.get("isin"))
            record_date = _strip(row.get("record_date"))
            pay_date = _strip(row.get("pay_date"))
            crest_bucket = _strip(row.get("crest_bucket"))

            shares_raw = _strip(row.get("shares"))
            try:
                shares = int(shares_raw)
            except (TypeError, ValueError):
                raise ValueError("BAD_SHARES")

            rate_raw = _strip(row.get("dividend_per_share"))
            try:
                dividend_per_share = Decimal(rate_raw)
            except (InvalidOperation, ValueError):
                raise ValueError("BAD_RATE")

            cash_raw = _strip(row.get("cash_credited"))
            try:
                cash_credited = Decimal(cash_raw)
            except (InvalidOperation, ValueError):
                raise ValueError("BAD_CASH")

            out.append(
                CrestBucketSnapshot(
                    isin=isin,
                    record_date=record_date,
                    pay_date=pay_date,
                    crest_bucket=crest_bucket,  # validated later
                    shares=shares,
                    dividend_per_share=dividend_per_share,
                    cash_credited=cash_credited,
                )
            )

    return out