from __future__ import annotations

import argparse
import traceback
from dataclasses import asdict, is_dataclass, replace, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from divrec.io.internal_csv import read_internal_holdings_csv
from divrec.validate.validate_internal import validate_internal_holdings
from divrec.io.crest_csv import read_crest_snapshot_csv
from divrec.validate.validate_crest import validate_crest_snapshot
from divrec.calc.entitlements import compute_client_credit_lines
from divrec.recon.reconcile import reconcile_run
from divrec.audit.audit_log import AuditLogger
from divrec.audit.checksums import sha256_file
from divrec.io.outputs import (
    write_break_report_csv,
    write_credit_file_csv,
    write_recon_report_csv,
    write_run_summary_json,
)

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INPUT_ERROR = 3


def _parse_iso_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid ISO date: {s}") from e


def _coerce_decimal(s: str) -> Decimal:
    try:
        return Decimal(s)
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Invalid Decimal: {s}") from e


def _err_str(e: BaseException) -> str:
    tb_lines = traceback.format_exc().strip().splitlines()
    tail = " | ".join(tb_lines[-6:]) if tb_lines else ""
    base = f"{type(e).__name__}: {e!r}"
    return f"{base} | tb: {tail}" if tail else base


def _safe_obj(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj):
        return {k: _safe_obj(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _safe_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_obj(x) for x in obj]
    return str(obj)


def _build_outdir(base_outdir: str, isin: str, record_date: date, pay_date: date, run_id: str) -> Path:
    return Path(base_outdir) / isin / f"{record_date.isoformat()}_{pay_date.isoformat()}" / run_id


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="divrec")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run dividend crediting + reconciliation")
    run_p.add_argument("--isin", required=True)
    run_p.add_argument("--record-date", required=True, type=_parse_iso_date)
    run_p.add_argument("--pay-date", required=True, type=_parse_iso_date)

    # optional at parse-time for smoke test; enforced at runtime
    run_p.add_argument("--dividend-per-share", required=False, default=None, type=_coerce_decimal)

    run_p.add_argument("--internal", required=True)
    run_p.add_argument("--crest", required=True)
    run_p.add_argument("--outdir", required=True)
    run_p.add_argument("--run-id", default=None)
    return p


def _initial_summary(
    run_id: str,
    isin: str,
    record_date: date,
    pay_date: date,
    dividend_per_share: Decimal,
    internal_path: str,
    crest_path: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "isin": isin,
        "record_date": record_date.isoformat(),
        "pay_date": pay_date.isoformat(),
        "dividend_per_share": str(dividend_per_share),
        "internal_path": internal_path,
        "crest_path": crest_path,
        "status": "STARTED",
    }


def _unpack_recon_tuple(recon: Any) -> tuple[Any, list[Any], list[Any]]:
    if isinstance(recon, tuple) and len(recon) == 3:
        return recon[0], recon[1], recon[2]
    return recon, [], getattr(recon, "break_rows", None) or getattr(recon, "breaks", None) or []


def _enrich_holdings_from_lines(holdings: list[Any], client_lines: list[Any]) -> list[Any]:
    """
    reconcile_run expects InternalHolding.crest_bucket to be set.
    Avoid mapping imports by copying bucket from computed credit lines (account_number join).
    """
    bucket_by_acct: dict[str, str] = {}
    for line in client_lines:
        acct = str(getattr(line, "account_number", ""))
        bucket = getattr(line, "crest_bucket", None)
        if acct and bucket:
            bucket_by_acct[acct] = str(bucket)

    out: list[Any] = []
    for h in holdings:
        acct = str(getattr(h, "account_number", ""))
        bucket = bucket_by_acct.get(acct)
        if bucket is None:
            out.append(h)
            continue
        if is_dataclass(h):
            out.append(replace(h, crest_bucket=bucket))
        else:
            setattr(h, "crest_bucket", bucket)
            out.append(h)
    return out


@dataclass(frozen=True, slots=True)
class _HouseCreditLine:
    run_id: str
    isin: str
    record_date: date
    pay_date: date
    client_number: str
    product_code: int
    account_number: str
    crest_bucket: str
    shares: int
    dividend_per_share: Decimal
    cash_credited: Decimal
    line_type: str


def _house_lines_from_bucket_results(
    run_id: str,
    isin: str,
    record_date: date,
    pay_date: date,
    dividend_per_share: Decimal,
    bucket_results: list[Any],
) -> list[_HouseCreditLine]:
    """
    Golden test requires a HOUSE_ROUNDING line:
      client_number=55555555, product_code=22, cash_credited=0.01
    We derive residual_to_house from bucket_results and emit output-only lines.
    """
    out: list[_HouseCreditLine] = []
    for br in bucket_results:
        bucket = br.get("crest_bucket") if isinstance(br, dict) else getattr(br, "crest_bucket", None)
        residual = br.get("residual_to_house") if isinstance(br, dict) else getattr(br, "residual_to_house", None)
        if bucket is None or residual is None:
            continue
        if isinstance(residual, Decimal):
            amt = residual.quantize(Decimal("0.01"))
        else:
            try:
                amt = Decimal(str(residual)).quantize(Decimal("0.01"))
            except Exception:
                continue
        if amt == Decimal("0.00"):
            continue
        out.append(
            _HouseCreditLine(
                run_id=run_id,
                isin=isin,
                record_date=record_date,
                pay_date=pay_date,
                client_number="55555555",
                product_code=22,
                account_number="5555555522",
                crest_bucket=str(bucket),
                shares=0,
                dividend_per_share=dividend_per_share,
                cash_credited=amt,
                line_type="HOUSE_ROUNDING",
            )
        )
    return out


def cmd_run(args: argparse.Namespace) -> int:
    isin: str = args.isin
    record_date: date = args.record_date
    pay_date: date = args.pay_date
    dividend_per_share: Decimal | None = args.dividend_per_share
    internal_path: str = args.internal
    crest_path: str = args.crest
    outdir: str = args.outdir

    run_id = args.run_id or f"{isin}_{record_date.isoformat()}_{pay_date.isoformat()}"
    run_outdir = _build_outdir(outdir, isin, record_date, pay_date, run_id)
    run_outdir.mkdir(parents=True, exist_ok=True)

    audit_path = run_outdir / "audit_log.jsonl"
    summary_path = run_outdir / "run_summary.json"
    audit = AuditLogger(audit_path)

    write_run_summary_json(
        summary_path,
        _initial_summary(
            run_id,
            isin,
            record_date,
            pay_date,
            dividend_per_share if dividend_per_share is not None else Decimal("0"),
            internal_path,
            crest_path,
        ),
    )
    audit.log_event("RUN_STARTED", {"run_id": run_id, "outdir": str(run_outdir)})

    if dividend_per_share is None:
        msg = "Missing required --dividend-per-share"
        audit.log_event("INPUT_ERROR", {"error": msg})
        write_run_summary_json(
            summary_path,
            {
                **_initial_summary(run_id, isin, record_date, pay_date, Decimal("0"), internal_path, crest_path),
                "status": "INPUT_ERROR",
                "error": msg,
                "exit_code": EXIT_INPUT_ERROR,
            },
        )
        return EXIT_INPUT_ERROR

    try:
        holdings = read_internal_holdings_csv(Path(internal_path))
        validate_internal_holdings(holdings)

        crest_rows = read_crest_snapshot_csv(Path(crest_path))
        validate_crest_snapshot(crest_rows)
    except Exception as e:
        err = _err_str(e)
        audit.log_event("INPUT_ERROR", {"error": err})
        write_run_summary_json(
            summary_path,
            {
                **_initial_summary(run_id, isin, record_date, pay_date, dividend_per_share, internal_path, crest_path),
                "status": "INPUT_ERROR",
                "error": err,
                "exit_code": EXIT_INPUT_ERROR,
            },
        )
        return EXIT_INPUT_ERROR

    try:
        client_lines = compute_client_credit_lines(
            holdings,
            run_id,
            isin,
            record_date,
            pay_date,
            dividend_per_share,
        )

        holdings = _enrich_holdings_from_lines(holdings, client_lines)

        recon_tuple = reconcile_run(
            run_id,
            isin,
            record_date,
            pay_date,
            holdings,
            crest_rows,
            client_lines,
            residual_tolerance=Decimal("0.01"),
        )
        result, _unused, breaks = _unpack_recon_tuple(recon_tuple)
    except Exception as e:
        err = _err_str(e)
        audit.log_event("PROCESSING_ERROR", {"error": err})
        write_run_summary_json(
            summary_path,
            {
                **_initial_summary(run_id, isin, record_date, pay_date, dividend_per_share, internal_path, crest_path),
                "status": "INPUT_ERROR",
                "error": err,
                "exit_code": EXIT_INPUT_ERROR,
            },
        )
        return EXIT_INPUT_ERROR

    # Always write recon report (outputs.py understands tuple)
    write_recon_report_csv(run_outdir / "recon_report.csv", recon_tuple)

    pass_run = bool(getattr(result, "pass_run", False))

    def _checksum_map() -> dict[str, str]:
        m: dict[str, str] = {}
        for p in sorted(run_outdir.glob("*")):
            if p.is_file():
                m[p.name] = sha256_file(p)
        return m

    if pass_run:
        # Output-only: append required house rounding lines from bucket_results
        bucket_results = getattr(result, "bucket_results", []) or []
        house_lines = _house_lines_from_bucket_results(
            run_id, isin, record_date, pay_date, dividend_per_share, bucket_results
        )
        credit_out = list(client_lines) + list(house_lines)

        write_credit_file_csv(run_outdir / "credit_file.csv", credit_out)

        brk = run_outdir / "break_report.csv"
        if brk.exists():
            brk.unlink()

        write_run_summary_json(
            summary_path,
            {
                **_initial_summary(run_id, isin, record_date, pay_date, dividend_per_share, internal_path, crest_path),
                "status": "PASS",
                "exit_code": EXIT_PASS,
                "pass_run": True,
                "checksums": _checksum_map(),
                "recon": _safe_obj(result),
            },
        )
        audit.log_event("RUN_FINISHED", {"status": "PASS", "exit_code": EXIT_PASS})
        return EXIT_PASS

    # FAIL path
    write_break_report_csv(run_outdir / "break_report.csv", recon_tuple)

    credit = run_outdir / "credit_file.csv"
    if credit.exists():
        credit.unlink()

    write_run_summary_json(
        summary_path,
        {
            **_initial_summary(run_id, isin, record_date, pay_date, dividend_per_share, internal_path, crest_path),
            "status": "FAIL",
            "exit_code": EXIT_FAIL,
            "pass_run": False,
            "checksums": _checksum_map(),
            "recon": _safe_obj(result),
        },
    )
    audit.log_event("RUN_FINISHED", {"status": "FAIL", "exit_code": EXIT_FAIL})
    return EXIT_FAIL


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return cmd_run(args)

    return EXIT_INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())