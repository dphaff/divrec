from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


CREDIT_COLUMNS = [
    "run_id",
    "isin",
    "record_date",
    "pay_date",
    "client_number",
    "product_code",
    "account_number",
    "crest_bucket",
    "shares",
    "dividend_per_share",
    "cash_credited",
    "line_type",
]

RECON_COLUMNS = [
    "run_id",
    "isin",
    "record_date",
    "pay_date",
    "crest_bucket",
    "crest_shares",
    "internal_shares",
    "shares_diff",
    "crest_cash",
    "internal_cash_pre_residual",
    "residual_to_house",
    "internal_cash_post_residual",
    "cash_diff_post_residual",
    "pass_bucket",
    "pass_run",
]

BREAK_COLUMNS = [
    "run_id",
    "isin",
    "crest_bucket",
    "break_type",
    "details",
    "crest_value",
    "internal_value",
]


def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Decimal):
        # keep stable string form; cash fields are already quantized upstream where needed
        return str(v)
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, str):
        return v.strip()
    return str(v)


def _get(obj: Any, key: str, default: Any = "") -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _unpack_recon(recon: Any) -> tuple[Any, list[Any], list[Any]]:
    if isinstance(recon, tuple) and len(recon) == 3:
        return recon[0], recon[1], recon[2]
    return recon, [], _get(recon, "break_rows", []) or _get(recon, "breaks", []) or []


def write_credit_file_csv(path: str | Path, credit_lines: Iterable[Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CREDIT_COLUMNS)
        w.writeheader()
        for line in credit_lines:
            cash = _get(line, "cash_credited", "")
            if isinstance(cash, Decimal):
                cash = cash.quantize(Decimal("0.01"))
            row = {
                "run_id": _s(_get(line, "run_id")),
                "isin": _s(_get(line, "isin")),
                "record_date": _s(_get(line, "record_date")),
                "pay_date": _s(_get(line, "pay_date")),
                "client_number": _s(_get(line, "client_number")),
                "product_code": _s(_get(line, "product_code")),
                "account_number": _s(_get(line, "account_number")),
                "crest_bucket": _s(_get(line, "crest_bucket")),
                "shares": _s(_get(line, "shares")),
                "dividend_per_share": _s(_get(line, "dividend_per_share")),
                "cash_credited": _s(cash),
                "line_type": _s(_get(line, "line_type")),
            }
            w.writerow(row)


def write_recon_report_csv(path: str | Path, recon: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    result, _unused, _breaks = _unpack_recon(recon)
    pass_run = bool(_get(result, "pass_run", False))
    bucket_results = _get(result, "bucket_results", []) or []

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RECON_COLUMNS)
        w.writeheader()
        for r in bucket_results:
            row = {
                "run_id": _s(_get(result, "run_id")),
                "isin": _s(_get(result, "isin")),
                "record_date": _s(_get(result, "record_date")),
                "pay_date": _s(_get(result, "pay_date")),
                "crest_bucket": _s(_get(r, "crest_bucket")),
                "crest_shares": _s(_get(r, "crest_shares")),
                "internal_shares": _s(_get(r, "internal_shares")),
                "shares_diff": _s(_get(r, "shares_diff")),
                "crest_cash": _s(_get(r, "crest_cash")),
                "internal_cash_pre_residual": _s(_get(r, "internal_cash_pre_residual")),
                "residual_to_house": _s(_get(r, "residual_to_house")),
                "internal_cash_post_residual": _s(_get(r, "internal_cash_post_residual")),
                "cash_diff_post_residual": _s(_get(r, "cash_diff_post_residual")),
                "pass_bucket": _s(_get(r, "pass_bucket")),
                "pass_run": _s(pass_run),
            }
            w.writerow(row)


def write_break_report_csv(path: str | Path, recon: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    result, _unused, breaks = _unpack_recon(recon)

    # If reconcile_run didn't supply BreakRow objects, synthesise from bucket_results
    if not breaks:
        bucket_results = _get(result, "bucket_results", []) or []
        syn: list[dict[str, Any]] = []
        for r in bucket_results:
            diff = _get(r, "shares_diff", 0)
            try:
                diff_int = int(diff)
            except Exception:
                diff_int = 0
            if diff_int != 0:
                syn.append(
                    {
                        "run_id": _get(result, "run_id"),
                        "isin": _get(result, "isin"),
                        "crest_bucket": _get(r, "crest_bucket"),
                        "break_type": "SHARES_MISMATCH",
                        "details": f"shares_diff={diff_int}",
                        "crest_value": _get(r, "crest_shares"),
                        "internal_value": _get(r, "internal_shares"),
                    }
                )
        breaks = syn

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BREAK_COLUMNS)
        w.writeheader()
        for b in breaks:
            crest_v = _get(b, "crest_value", "")
            internal_v = _get(b, "internal_value", "")
            if isinstance(crest_v, Decimal):
                crest_v = crest_v.quantize(Decimal("0.01"))
            if isinstance(internal_v, Decimal):
                internal_v = internal_v.quantize(Decimal("0.01"))

            row = {
                "run_id": _s(_get(b, "run_id")),
                "isin": _s(_get(b, "isin")),
                "crest_bucket": _s(_get(b, "crest_bucket")),
                "break_type": _s(_get(b, "break_type")),
                "details": _s(_get(b, "details")),
                "crest_value": _s(crest_v),
                "internal_value": _s(internal_v),
            }
            w.writerow(row)


def write_run_summary_json(path: str | Path, summary: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")