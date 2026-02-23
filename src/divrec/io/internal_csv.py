from __future__ import annotations

import csv
from pathlib import Path

from divrec.domain.models import InternalHolding


REQUIRED_COLUMNS: set[str] = {
    "isin",
    "record_date",
    "client_number",
    "product_code",
    "account_number",
    "shares",
}


def _safe_int(value: str, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_internal_holdings_csv(path: Path) -> list[InternalHolding]:
    """Read internal holdings from a CSV.

    Notes:
    - Only enforces presence of required columns.
    - Performs basic parsing (strip + int conversion) but does not validate business rules.
    """

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        fieldnames = reader.fieldnames or []
        present = {name.strip() for name in fieldnames if name is not None}
        if not REQUIRED_COLUMNS.issubset(present):
            raise ValueError("MISSING_COLUMN")

        holdings: list[InternalHolding] = []
        for row in reader:
            # DictReader keys are the raw header names; normalise access by stripping.
            normalised = {k.strip(): (v if v is not None else "") for k, v in row.items() if k is not None}

            isin = str(normalised.get("isin", "")).strip()
            record_date = str(normalised.get("record_date", "")).strip()
            client_number = str(normalised.get("client_number", "")).strip()
            account_number = str(normalised.get("account_number", "")).strip()

            product_code = _safe_int(str(normalised.get("product_code", "")).strip(), default=-1)
            shares = _safe_int(str(normalised.get("shares", "")).strip(), default=-1)

            holdings.append(
                InternalHolding(
                    isin=isin,
                    record_date=record_date,
                    client_number=client_number,
                    product_code=product_code,
                    account_number=account_number,
                    shares=shares,
                )
            )

        return holdings