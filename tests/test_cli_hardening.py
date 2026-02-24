from __future__ import annotations

import csv
from pathlib import Path

import divrec.cli as cli

ISIN = "GB00B03MLX29"
RECORD_DATE = "2026-02-20"
PAY_DATE = "2026-03-05"
DPS = "0.3333"


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _run_and_paths(tmp_path: Path, run_id: str, internal: Path, crest: Path) -> tuple[int, Path]:
    outdir = tmp_path / "out"
    argv = [
        "run",
        "--isin",
        ISIN,
        "--record-date",
        RECORD_DATE,
        "--pay-date",
        PAY_DATE,
        "--dividend-per-share",
        DPS,
        "--internal",
        str(internal),
        "--crest",
        str(crest),
        "--outdir",
        str(outdir),
        "--run-id",
        run_id,
    ]
    rc = cli.main(argv)
    run_outdir = outdir / ISIN / f"{RECORD_DATE}_{PAY_DATE}" / run_id
    return rc, run_outdir


def test_cli_unknown_internal_product_code_is_input_error(tmp_path: Path) -> None:
    """
    TEST 1: Unknown internal product code -> INPUT_ERROR (exit code 3)
    """
    internal = tmp_path / "internal_unknown_product.csv"
    crest = tmp_path / "crest_valid.csv"

    # Internal CSV (one row) with unknown product_code 98 and matching account_number.
    _write_csv(
        internal,
        header=["isin", "record_date", "client_number", "product_code", "account_number", "shares", "crest_bucket"],
        rows=[
            [ISIN, RECORD_DATE, "11111111", "98", "1111111198", "10", "ISA"],
        ],
    )

    # Valid CREST CSV with required ISA/SIPP/GIA buckets.
    _write_csv(
        crest,
        header=["isin", "record_date", "pay_date", "crest_bucket", "shares", "dividend_per_share", "cash_credited"],
        rows=[
            [ISIN, RECORD_DATE, PAY_DATE, "ISA", "10", DPS, "3.33"],
            [ISIN, RECORD_DATE, PAY_DATE, "SIPP", "10", DPS, "3.33"],
            [ISIN, RECORD_DATE, PAY_DATE, "GIA", "10", DPS, "3.33"],
        ],
    )

    rc, run_outdir = _run_and_paths(tmp_path, "hardening_unknown_product", internal, crest)

    assert rc == 3
    assert run_outdir.exists()
    assert (run_outdir / "audit_log.jsonl").exists()
    assert (run_outdir / "run_summary.json").exists()

    # INPUT_ERROR: no credit or break report should be produced
    assert not (run_outdir / "credit_file.csv").exists()
    assert not (run_outdir / "break_report.csv").exists()


def test_cli_missing_crest_bucket_is_input_error(tmp_path: Path) -> None:
    """
    TEST 2: Missing CREST bucket -> INPUT_ERROR (exit code 3)
    """
    internal = tmp_path / "internal_valid.csv"
    crest = tmp_path / "crest_missing_bucket.csv"

    # Valid internal holdings with at least ISA, SIPP, GIA.
    # Use known product codes: 22 -> ISA, 70 -> SIPP, 97 -> GIA.
    _write_csv(
        internal,
        header=["isin", "record_date", "client_number", "product_code", "account_number", "shares", "crest_bucket"],
        rows=[
            [ISIN, RECORD_DATE, "11111111", "22", "1111111122", "100", "ISA"],
            [ISIN, RECORD_DATE, "22222222", "70", "2222222270", "50", "SIPP"],
            [ISIN, RECORD_DATE, "33333333", "97", "3333333397", "10", "GIA"],
        ],
    )

    # CREST snapshot missing required bucket (omit GIA)
    _write_csv(
        crest,
        header=["isin", "record_date", "pay_date", "crest_bucket", "shares", "dividend_per_share", "cash_credited"],
        rows=[
            [ISIN, RECORD_DATE, PAY_DATE, "ISA", "100", DPS, "33.33"],
            [ISIN, RECORD_DATE, PAY_DATE, "SIPP", "50", DPS, "16.67"],
            # GIA omitted on purpose
        ],
    )

    rc, run_outdir = _run_and_paths(tmp_path, "hardening_missing_bucket", internal, crest)

    assert rc == 3
    assert run_outdir.exists()
    assert (run_outdir / "audit_log.jsonl").exists()
    assert (run_outdir / "run_summary.json").exists()
    assert not (run_outdir / "credit_file.csv").exists()
    assert not (run_outdir / "break_report.csv").exists()


def test_cli_residual_exceeds_tolerance_is_fail(tmp_path: Path) -> None:
    """
    TEST 3: Residual out of tolerance (+0.02) -> FAIL (exit code 2)
    - Shares match across buckets.
    - DPS=0.3333.
    - ISA internal cash sums to 33.33, CREST ISA cash_credited is 33.35 (+0.02 residual).
    - Expect break_report contains RESIDUAL_EXCEEDS_TOLERANCE for ISA.
    """
    internal = tmp_path / "internal_residual_002.csv"
    crest = tmp_path / "crest_residual_002.csv"

    # Shares match exactly: ISA=100, SIPP=50, GIA=10
    _write_csv(
        internal,
        header=["isin", "record_date", "client_number", "product_code", "account_number", "shares", "crest_bucket"],
        rows=[
            # Single ISA account: 100 * 0.3333 -> 33.33 after 2dp rounding
            [ISIN, RECORD_DATE, "11111111", "22", "1111111122", "100", "ISA"],
            [ISIN, RECORD_DATE, "22222222", "70", "2222222270", "50", "SIPP"],
            [ISIN, RECORD_DATE, "33333333", "97", "3333333397", "10", "GIA"],
        ],
    )

    # CREST has matching shares but ISA cash is +0.02 higher than internal total
    _write_csv(
        crest,
        header=["isin", "record_date", "pay_date", "crest_bucket", "shares", "dividend_per_share", "cash_credited"],
        rows=[
            [ISIN, RECORD_DATE, PAY_DATE, "ISA", "100", DPS, "33.35"],  # +0.02 residual vs 33.33
            [ISIN, RECORD_DATE, PAY_DATE, "SIPP", "50", DPS, "16.67"],
            [ISIN, RECORD_DATE, PAY_DATE, "GIA", "10", DPS, "3.33"],
        ],
    )

    rc, run_outdir = _run_and_paths(tmp_path, "hardening_residual_002", internal, crest)

    assert rc == 2
    assert run_outdir.exists()
    assert (run_outdir / "audit_log.jsonl").exists()
    assert (run_outdir / "run_summary.json").exists()

    # FAIL: break_report exists; credit_file does not
    assert (run_outdir / "break_report.csv").exists()
    assert not (run_outdir / "credit_file.csv").exists()

    # break_report contains required row
    found = False
    with (run_outdir / "break_report.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("break_type") == "RESIDUAL_EXCEEDS_TOLERANCE" and row.get("crest_bucket") == "ISA":
                found = True
                break
    assert found, "Expected RESIDUAL_EXCEEDS_TOLERANCE for crest_bucket=ISA in break_report.csv"