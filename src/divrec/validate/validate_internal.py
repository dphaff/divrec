from __future__ import annotations

from divrec.domain.mapping import ALLOWED_PRODUCT_CODES, make_account_number
from divrec.domain.models import InternalHolding


def validate_internal_holdings(holdings: list[InternalHolding]) -> None:
    if not holdings:
        raise ValueError("EMPTY_INTERNAL")

    seen_keys: set[tuple[str, str, int]] = set()

    for h in holdings:
        if len(h.client_number) != 8 or not h.client_number.isdigit():
            raise ValueError("BAD_CLIENT_NUMBER")

        if h.product_code not in ALLOWED_PRODUCT_CODES:
            raise ValueError("UNKNOWN_PRODUCT_CODE")

        expected_account = make_account_number(h.client_number, h.product_code)
        if h.account_number != expected_account:
            raise ValueError("BAD_ACCOUNT_NUMBER")

        if not isinstance(h.shares, int) or h.shares < 1:
            raise ValueError("BAD_SHARES")

        key = (h.isin, h.client_number, h.product_code)
        if key in seen_keys:
            raise ValueError("DUPLICATE_INTERNAL_KEY")
        seen_keys.add(key)
