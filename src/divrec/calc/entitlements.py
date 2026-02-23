from __future__ import annotations

from decimal import Decimal

from divrec.calc.rounding import round_half_up
from divrec.domain.mapping import bucket_for_product
from divrec.domain.models import CreditLine, InternalHolding


def compute_client_credit_lines(
    holdings: list[InternalHolding],
    run_id: str,
    isin: str,
    record_date: str,
    pay_date: str,
    dividend_per_share: Decimal,
) -> list[CreditLine]:
    lines: list[CreditLine] = []

    for h in holdings:
        raw_cash = Decimal(h.shares) * dividend_per_share
        cash_credited = round_half_up(raw_cash, 2)

        lines.append(
            CreditLine(
                run_id=run_id,
                isin=isin,
                record_date=record_date,
                pay_date=pay_date,
                client_number=h.client_number,
                product_code=h.product_code,
                account_number=h.account_number,
                crest_bucket=bucket_for_product(h.product_code),
                shares=h.shares,
                dividend_per_share=dividend_per_share,
                cash_credited=cash_credited,
                line_type="CLIENT",
            )
        )

    return lines