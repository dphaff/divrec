from __future__ import annotations

from decimal import Decimal
from typing import Final

from divrec.domain.models import (
    BucketReconResult,
    CrestBucket,
    CrestBucketSnapshot,
    CreditLine,
    InternalHolding,
    RunReconResult,
    aggregate_cash_by_bucket,
    aggregate_internal_shares_by_bucket,
    make_account_number,
)
from divrec.recon.breaks import BreakRow


HOUSE_CLIENT: Final[str] = "55555555"
HOUSE_PRODUCT_BY_BUCKET: Final[dict[CrestBucket, int]] = {"ISA": 22, "SIPP": 70, "GIA": 97}


def reconcile_run(
    run_id: str,
    isin: str,
    record_date: str,
    pay_date: str,
    internal_holdings: list[InternalHolding],
    crest_rows: list[CrestBucketSnapshot],
    client_lines: list[CreditLine],
    residual_tolerance: Decimal = Decimal("0.01"),
) -> tuple[RunReconResult, list[CreditLine], list[BreakRow]]:
    """Reconcile a run against CREST for shares and cash residuals (v1).

    Returns:
      (recon_result, final_credit_lines, breaks)
    """

    crest_by_bucket: dict[str, CrestBucketSnapshot] = {r.crest_bucket: r for r in crest_rows}
    expected = {"ISA", "SIPP", "GIA"}
    if set(crest_by_bucket.keys()) != expected:
        raise ValueError("MISSING_BUCKET")

    internal_shares = aggregate_internal_shares_by_bucket(internal_holdings)
    internal_cash_pre = aggregate_cash_by_bucket(client_lines)

    bucket_results: list[BucketReconResult] = []
    breaks: list[BreakRow] = []
    fail_reasons: list[str] = []

    for bucket in ("ISA", "SIPP", "GIA"):
        crest_row = crest_by_bucket[bucket]
        crest_shares = int(crest_row.shares)
        crest_cash = crest_row.cash_credited  # <-- FIXED (was crest_row.cash)

        int_shares = int(internal_shares[bucket])
        int_cash_pre = internal_cash_pre[bucket]
        shares_diff = int_shares - crest_shares

        residual = crest_cash - int_cash_pre
        eligible = abs(residual) <= residual_tolerance
        int_cash_post = int_cash_pre + (residual if eligible else Decimal("0.00"))
        cash_diff_post = crest_cash - int_cash_post
        pass_bucket = (int_shares == crest_shares) and eligible

        bucket_results.append(
            BucketReconResult(
                crest_bucket=bucket,
                crest_shares=crest_shares,
                internal_shares=int_shares,
                shares_diff=shares_diff,
                crest_cash=crest_cash,
                internal_cash_pre_residual=int_cash_pre,
                residual_to_house=residual,
                internal_cash_post_residual=int_cash_post,
                cash_diff_post_residual=cash_diff_post,
                pass_bucket=pass_bucket,
            )
        )

        if int_shares != crest_shares:
            breaks.append(
                BreakRow(
                    run_id=run_id,
                    isin=isin,
                    crest_bucket=bucket,
                    break_type="SHARES_MISMATCH",
                    details=f"shares_diff={shares_diff}",
                    crest_value=str(crest_shares),
                    internal_value=str(int_shares),
                )
            )
            fail_reasons.append(f"SHARES_MISMATCH:{bucket}")

        if not eligible:
            breaks.append(
                BreakRow(
                    run_id=run_id,
                    isin=isin,
                    crest_bucket=bucket,
                    break_type="RESIDUAL_EXCEEDS_TOLERANCE",
                    details=f"residual={residual} tolerance={residual_tolerance}",
                    crest_value=str(crest_cash),
                    internal_value=str(int_cash_pre),
                )
            )
            fail_reasons.append(f"RESIDUAL_EXCEEDS_TOLERANCE:{bucket}")

    pass_run = all(br.pass_bucket for br in bucket_results)
    recon = RunReconResult(
        run_id=run_id,
        isin=isin,
        record_date=record_date,
        pay_date=pay_date,
        bucket_results=bucket_results,
        pass_run=pass_run,
        fail_reasons=fail_reasons,
    )

    if not pass_run:
        return recon, [], breaks

    house_lines: list[CreditLine] = []
    for br in bucket_results:
        if br.residual_to_house == Decimal("0.00"):
            continue
        product_code = HOUSE_PRODUCT_BY_BUCKET[br.crest_bucket]
        house_lines.append(
            CreditLine(
                run_id=run_id,
                isin=isin,
                record_date=record_date,
                pay_date=pay_date,
                client_number=HOUSE_CLIENT,
                product_code=product_code,
                account_number=make_account_number(HOUSE_CLIENT, product_code),
                crest_bucket=br.crest_bucket,
                shares=0,
                dividend_per_share=crest_by_bucket[br.crest_bucket].dividend_per_share,
                cash_credited=br.residual_to_house,
                line_type="HOUSE_ROUNDING",
            )
        )

    final_credit_lines = list(client_lines) + house_lines
    return recon, final_credit_lines, []