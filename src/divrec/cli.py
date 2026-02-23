from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="divrec",
        description="UK Brokerage Dividend Crediting & Reconciliation Engine (GBP, v1)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser(
        "run",
        help="Run dividend crediting + reconciliation (stub; logic not implemented yet).",
    )

    # Required inputs for v1 wiring (no validation yet; just plumbing)
    run_p.add_argument("--isin", required=True, help="ISIN to process (e.g. GB00...).")
    run_p.add_argument(
        "--record-date",
        required=True,
        help="Record date (YYYY-MM-DD).",
    )
    run_p.add_argument(
        "--pay-date",
        required=True,
        help="Pay date (YYYY-MM-DD).",
    )
    run_p.add_argument(
        "--internal",
        required=True,
        help="Path to internal positions/holdings snapshot (CSV).",
    )
    run_p.add_argument(
        "--crest",
        required=True,
        help="Path to CREST/settlement snapshot (CSV).",
    )
    run_p.add_argument(
        "--outdir",
        required=True,
        help="Output directory for reports/artifacts.",
    )

    # Optional run metadata / logging control
    run_p.add_argument(
        "--run-id",
        required=False,
        default=None,
        help="Optional run identifier for traceability (e.g. UUID).",
    )
    run_p.add_argument(
        "--log-level",
        required=False,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    _args = parser.parse_args(argv)

    # Stub only: run logic will be implemented in later tickets.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())