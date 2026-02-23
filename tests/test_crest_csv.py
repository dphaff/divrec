from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure 'src/' is importable when running pytest from repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from divrec.io.crest_csv import read_crest_snapshot_csv
from divrec.validate.validate_crest import validate_crest_snapshot


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "crest.csv"
    p.write_text(text, encoding="utf-8")
    return p


def test_happy_path_parses_and_validates(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,1.23
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,0.1234,2.46
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,0.1234,3.69
""",
    )

    rows = read_crest_snapshot_csv(p)
    assert len(rows) == 3
    validate_crest_snapshot(rows)


def test_missing_column_raises_missing_column(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234
""",
    )

    with pytest.raises(ValueError) as e:
        read_crest_snapshot_csv(p)
    assert str(e.value) == "MISSING_COLUMN"


def test_bad_bucket_value_raises_bad_bucket(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,1.23
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,0.1234,2.46
GB00TEST0001,2026-01-01,2026-01-10,FOO,30,0.1234,3.69
""",
    )
    rows = read_crest_snapshot_csv(p)
    with pytest.raises(ValueError) as e:
        validate_crest_snapshot(rows)
    assert str(e.value) == "BAD_BUCKET"


def test_missing_required_bucket_raises_missing_bucket(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,1.23
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,0.1234,2.46
""",
    )
    rows = read_crest_snapshot_csv(p)
    with pytest.raises(ValueError) as e:
        validate_crest_snapshot(rows)
    assert str(e.value) == "MISSING_BUCKET"


def test_duplicate_bucket_row_raises_duplicate_bucket_row(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,1.23
GB00TEST0001,2026-01-01,2026-01-10,ISA,20,0.1234,2.46
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,0.1234,3.69
""",
    )
    rows = read_crest_snapshot_csv(p)
    with pytest.raises(ValueError) as e:
        validate_crest_snapshot(rows)
    assert str(e.value) == "DUPLICATE_BUCKET_ROW"


def test_multi_isin_raises_multi_isin_crest(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,1.23
GB00TEST0002,2026-01-01,2026-01-10,SIPP,20,0.1234,2.46
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,0.1234,3.69
""",
    )
    rows = read_crest_snapshot_csv(p)
    with pytest.raises(ValueError) as e:
        validate_crest_snapshot(rows)
    assert str(e.value) == "MULTI_ISIN_CREST"


def test_rate_mismatch_across_buckets_raises(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,1.23
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,0.9999,2.46
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,0.1234,3.69
""",
    )
    rows = read_crest_snapshot_csv(p)
    with pytest.raises(ValueError) as e:
        validate_crest_snapshot(rows)
    assert str(e.value) == "RATE_MISMATCH_ACROSS_BUCKETS"


@pytest.mark.parametrize(
    "shares_value",
    [
        "-1",  # negative int
        "abc",  # non-int
    ],
)
def test_bad_shares_raises_bad_shares(tmp_path: Path, shares_value: str) -> None:
    p = _write(
        tmp_path,
        f"""isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,{shares_value},0.1234,1.23
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,0.1234,2.46
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,0.1234,3.69
""",
    )

    if shares_value == "abc":
        with pytest.raises(ValueError) as e:
            read_crest_snapshot_csv(p)
        assert str(e.value) == "BAD_SHARES"
    else:
        rows = read_crest_snapshot_csv(p)
        with pytest.raises(ValueError) as e:
            validate_crest_snapshot(rows)
        assert str(e.value) == "BAD_SHARES"


@pytest.mark.parametrize(
    "rate_value",
    [
        "-0.0001",  # negative
        "abc",  # non-decimal
    ],
)
def test_bad_rate_raises_bad_rate(tmp_path: Path, rate_value: str) -> None:
    p = _write(
        tmp_path,
        f"""isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,{rate_value},1.23
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,{rate_value if rate_value != 'abc' else '0.1234'},2.46
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,{rate_value if rate_value != 'abc' else '0.1234'},3.69
""",
    )

    if rate_value == "abc":
        with pytest.raises(ValueError) as e:
            read_crest_snapshot_csv(p)
        assert str(e.value) == "BAD_RATE"
    else:
        rows = read_crest_snapshot_csv(p)
        with pytest.raises(ValueError) as e:
            validate_crest_snapshot(rows)
        assert str(e.value) == "BAD_RATE"


@pytest.mark.parametrize(
    "cash_value",
    [
        "-0.01",  # negative
        "abc",  # non-decimal
    ],
)
def test_bad_cash_raises_bad_cash(tmp_path: Path, cash_value: str) -> None:
    p = _write(
        tmp_path,
        f"""isin,record_date,pay_date,crest_bucket,shares,dividend_per_share,cash_credited
GB00TEST0001,2026-01-01,2026-01-10,ISA,10,0.1234,{cash_value}
GB00TEST0001,2026-01-01,2026-01-10,SIPP,20,0.1234,{cash_value if cash_value != 'abc' else '2.46'}
GB00TEST0001,2026-01-01,2026-01-10,GIA,30,0.1234,{cash_value if cash_value != 'abc' else '3.69'}
""",
    )

    if cash_value == "abc":
        with pytest.raises(ValueError) as e:
            read_crest_snapshot_csv(p)
        assert str(e.value) == "BAD_CASH"
    else:
        rows = read_crest_snapshot_csv(p)
        with pytest.raises(ValueError) as e:
            validate_crest_snapshot(rows)
        assert str(e.value) == "BAD_CASH"