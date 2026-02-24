from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ISIN = "GB00B03MLX29"
RECORD_DATE = "2026-02-20"
PAY_DATE = "2026-03-05"
DPS = "0.3333"


def _run_cli(tmp_path: Path, internal_csv: str, crest_csv: str, run_id: str) -> tuple[int, Path]:
    outdir = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "divrec.cli",
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
        internal_csv,
        "--crest",
        crest_csv,
        "--outdir",
        str(outdir),
        "--run-id",
        run_id,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    run_outdir = outdir / ISIN / f"{RECORD_DATE}_{PAY_DATE}" / run_id
    return r.returncode, run_outdir


def test_cli_golden_pass(tmp_path: Path) -> None:
    rc, run_outdir = _run_cli(
        tmp_path=tmp_path,
        internal_csv="data/pass_internal.csv",
        crest_csv="data/pass_crest.csv",
        run_id="demo_pass",
    )
    assert rc == 0

    credit = run_outdir / "credit_file.csv"
    recon = run_outdir / "recon_report.csv"
    brk = run_outdir / "break_report.csv"
    audit = run_outdir / "audit_log.jsonl"
    summary = run_outdir / "run_summary.json"

    assert credit.exists()
    assert recon.exists()
    assert audit.exists()
    assert summary.exists()
    assert not brk.exists()

    # Must contain HOUSE_ROUNDING line with client_number=55555555, product_code=22, cash_credited=0.01
    found = False
    with credit.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (
                row.get("line_type") == "HOUSE_ROUNDING"
                and row.get("client_number") == "55555555"
                and row.get("product_code") == "22"
                and row.get("cash_credited") == "0.01"
            ):
                found = True
                break
    assert found, "Expected HOUSE_ROUNDING 0.01 line for client 55555555 / product 22"


def test_cli_golden_fail(tmp_path: Path) -> None:
    rc, run_outdir = _run_cli(
        tmp_path=tmp_path,
        internal_csv="data/fail_internal.csv",
        crest_csv="data/fail_crest.csv",
        run_id="demo_fail",
    )
    assert rc == 2

    credit = run_outdir / "credit_file.csv"
    recon = run_outdir / "recon_report.csv"
    brk = run_outdir / "break_report.csv"
    audit = run_outdir / "audit_log.jsonl"
    summary = run_outdir / "run_summary.json"

    assert not credit.exists()
    assert recon.exists()
    assert brk.exists()
    assert audit.exists()
    assert summary.exists()

    found = False
    with brk.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("break_type") == "SHARES_MISMATCH" and row.get("crest_bucket") == "SIPP":
                found = True
                break
    assert found, "Expected SHARES_MISMATCH for crest_bucket=SIPP in break_report.csv"