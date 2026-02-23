from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

# Ensure `src/` is importable when running `pytest` from repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from divrec.domain.models import CrestBucketSnapshot, CreditLine, InternalHolding, make_account_number
from divrec.recon.reconcile import reconcile_run


def _crest_rows(*, isa_cash: str, sipp_cash: str, gia_cash: str, dps: str = "0.10"):
    return [
        CrestBucketSnapshot(
            isin="GB00DUMMY0000",
            record_date="2026-01-01",
            pay_date="2026-01-15",
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal(dps),
            cash_credited=Decimal(isa_cash),
        ),
        CrestBucketSnapshot(
            isin="GB00DUMMY0000",
            record_date="2026-01-01",
            pay_date="2026-01-15",
            crest_bucket="SIPP",
            shares=200,
            dividend_per_share=Decimal(dps),
            cash_credited=Decimal(sipp_cash),
        ),
        CrestBucketSnapshot(
            isin="GB00DUMMY0000",
            record_date="2026-01-01",
            pay_date="2026-01-15",
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal(dps),
            cash_credited=Decimal(gia_cash),
        ),
    ]


def test_pass_one_residual_in_isa_only_creates_house_rounding_line():
    run_id = "RUN1"
    isin = "GB00TEST0001"
    record_date = "2026-01-01"
    pay_date = "2026-01-15"

    internal_holdings = [
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="11111111",
            product_code=22,
            account_number=make_account_number("11111111", 22),
            crest_bucket="ISA",
            shares=100,
        ),
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="22222222",
            product_code=70,
            account_number=make_account_number("22222222", 70),
            crest_bucket="SIPP",
            shares=200,
        ),
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="33333333",
            product_code=97,
            account_number=make_account_number("33333333", 97),
            crest_bucket="GIA",
            shares=300,
        ),
    ]

    # CREST cash: ISA is +0.01 higher than internal pre-cash.
    crest_rows = [
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("10.01"),
        ),
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="SIPP",
            shares=200,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("20.00"),
        ),
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("30.00"),
        ),
    ]

    client_lines = [
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="11111111",
            product_code=22,
            account_number=make_account_number("11111111", 22),
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("10.00"),
            line_type="CLIENT",
        ),
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="22222222",
            product_code=70,
            account_number=make_account_number("22222222", 70),
            crest_bucket="SIPP",
            shares=200,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("20.00"),
            line_type="CLIENT",
        ),
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="33333333",
            product_code=97,
            account_number=make_account_number("33333333", 97),
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("30.00"),
            line_type="CLIENT",
        ),
    ]

    recon, final_lines, breaks = reconcile_run(
        run_id=run_id,
        isin=isin,
        record_date=record_date,
        pay_date=pay_date,
        internal_holdings=internal_holdings,
        crest_rows=crest_rows,
        client_lines=client_lines,
        residual_tolerance=Decimal("0.01"),
    )

    assert recon.pass_run is True
    assert recon.fail_reasons == []
    assert breaks == []

    house_lines = [ln for ln in final_lines if ln.line_type == "HOUSE_ROUNDING"]
    assert len(house_lines) == 1
    hl = house_lines[0]
    assert hl.crest_bucket == "ISA"
    assert hl.product_code == 22
    assert hl.client_number == "55555555"
    assert hl.cash_credited == Decimal("0.01")
    assert hl.shares == 0

    assert len(final_lines) == len(client_lines) + 1


def test_fail_shares_mismatch_in_sipp_outputs_no_lines_and_breaks():
    run_id = "RUN2"
    isin = "GB00TEST0002"
    record_date = "2026-01-01"
    pay_date = "2026-01-15"

    internal_holdings = [
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="11111111",
            product_code=22,
            account_number=make_account_number("11111111", 22),
            crest_bucket="ISA",
            shares=100,
        ),
        # mismatch: CREST expects 200
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="22222222",
            product_code=70,
            account_number=make_account_number("22222222", 70),
            crest_bucket="SIPP",
            shares=199,
        ),
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="33333333",
            product_code=97,
            account_number=make_account_number("33333333", 97),
            crest_bucket="GIA",
            shares=300,
        ),
    ]

    crest_rows = [
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("10.00"),
        ),
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="SIPP",
            shares=200,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("20.00"),
        ),
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("30.00"),
        ),
    ]

    client_lines = [
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="11111111",
            product_code=22,
            account_number=make_account_number("11111111", 22),
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("10.00"),
            line_type="CLIENT",
        ),
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="22222222",
            product_code=70,
            account_number=make_account_number("22222222", 70),
            crest_bucket="SIPP",
            shares=199,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("20.00"),
            line_type="CLIENT",
        ),
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="33333333",
            product_code=97,
            account_number=make_account_number("33333333", 97),
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("30.00"),
            line_type="CLIENT",
        ),
    ]

    recon, final_lines, breaks = reconcile_run(
        run_id=run_id,
        isin=isin,
        record_date=record_date,
        pay_date=pay_date,
        internal_holdings=internal_holdings,
        crest_rows=crest_rows,
        client_lines=client_lines,
    )

    assert recon.pass_run is False
    assert final_lines == []
    assert any(b.break_type == "SHARES_MISMATCH" and b.crest_bucket == "SIPP" for b in breaks)
    assert "SHARES_MISMATCH:SIPP" in recon.fail_reasons


def test_fail_residual_out_of_tolerance_in_gia_outputs_no_lines_and_breaks():
    run_id = "RUN3"
    isin = "GB00TEST0003"
    record_date = "2026-01-01"
    pay_date = "2026-01-15"

    internal_holdings = [
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="11111111",
            product_code=22,
            account_number=make_account_number("11111111", 22),
            crest_bucket="ISA",
            shares=100,
        ),
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="22222222",
            product_code=70,
            account_number=make_account_number("22222222", 70),
            crest_bucket="SIPP",
            shares=200,
        ),
        InternalHolding(
            isin=isin,
            record_date=record_date,
            client_number="33333333",
            product_code=97,
            account_number=make_account_number("33333333", 97),
            crest_bucket="GIA",
            shares=300,
        ),
    ]

    # GIA is +0.02 higher than internal -> exceeds 0.01 tolerance.
    crest_rows = [
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("10.00"),
        ),
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="SIPP",
            shares=200,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("20.00"),
        ),
        CrestBucketSnapshot(
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("30.02"),
        ),
    ]

    client_lines = [
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="11111111",
            product_code=22,
            account_number=make_account_number("11111111", 22),
            crest_bucket="ISA",
            shares=100,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("10.00"),
            line_type="CLIENT",
        ),
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="22222222",
            product_code=70,
            account_number=make_account_number("22222222", 70),
            crest_bucket="SIPP",
            shares=200,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("20.00"),
            line_type="CLIENT",
        ),
        CreditLine(
            run_id=run_id,
            isin=isin,
            record_date=record_date,
            pay_date=pay_date,
            client_number="33333333",
            product_code=97,
            account_number=make_account_number("33333333", 97),
            crest_bucket="GIA",
            shares=300,
            dividend_per_share=Decimal("0.10"),
            cash_credited=Decimal("30.00"),
            line_type="CLIENT",
        ),
    ]

    recon, final_lines, breaks = reconcile_run(
        run_id=run_id,
        isin=isin,
        record_date=record_date,
        pay_date=pay_date,
        internal_holdings=internal_holdings,
        crest_rows=crest_rows,
        client_lines=client_lines,
        residual_tolerance=Decimal("0.01"),
    )

    assert recon.pass_run is False
    assert final_lines == []
    assert any(
        b.break_type == "RESIDUAL_EXCEEDS_TOLERANCE" and b.crest_bucket == "GIA" for b in breaks
    )
    assert "RESIDUAL_EXCEEDS_TOLERANCE:GIA" in recon.fail_reasons