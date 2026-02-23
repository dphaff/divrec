from __future__ import annotations

import sys
from pathlib import Path


# Ensure src/ layout is importable even if the package isn't installed yet.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_cli_smoke_parser_builds_and_parses_run():
    import divrec.cli as cli

    parser = cli.build_parser()
    assert parser is not None

    argv = [
        "run",
        "--isin",
        "GB00TESTISIN0",
        "--record-date",
        "2026-01-01",
        "--pay-date",
        "2026-01-15",
        "--internal",
        "data/internal.csv",
        "--crest",
        "data/crest.csv",
        "--outdir",
        "out",
    ]
    args = parser.parse_args(argv)
    assert args.command == "run"
    assert args.isin == "GB00TESTISIN0"