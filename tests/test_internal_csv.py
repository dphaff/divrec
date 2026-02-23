from __future__ import annotations

from pathlib import Path

import pytest

from divrec.domain.mapping import make_account_number
from divrec.io.internal_csv import read_internal_holdings_csv
from divrec.validate.validate_internal import validate_internal_holdings


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = [",".join(header)]
    for r in rows:
        lines.append(",".join(r))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_happy_path_parses_and_validates_two_rows(tmp_path: Path) -> None:
    p = tmp_path / "internal.csv"

    header = ["isin", "record_date", "client_number", "product_code", "account_number", "shares"]
    r1_client, r1_prod = "12345678", 22
    r2_client, r2_prod = "87654321", 70
    rows = [
        [
            "GB00B03MLX29",
            "2026-02-01",
            r1_client,
            str(r1_prod),
            make_account_number(r1_client, r1_prod),
            "10",
        ],
        [
            "GB00B03MLX29",
            "2026-02-01",
            r2_client,
            str(r2_prod),
            make_account_number(r2_client, r2_prod),
            "1",
        ],
    ]

    _write_csv(p, header, rows)
    holdings = read_internal_holdings_csv(p)
    assert len(holdings) == 2
    validate_internal_holdings(holdings)


def test_missing_column_raises_missing_column(tmp_path: Path) -> None:
    p = tmp_path / "internal.csv"
    header = ["isin", "record_date", "client_number", "product_code", "account_number"]  # missing shares
    rows = [["GB00B03MLX29", "2026-02-01", "12345678", "22", "X"]]
    _write_csv(p, header, rows)

    with pytest.raises(ValueError) as e:
        read_internal_holdings_csv(p)
    assert str(e.value) == "MISSING_COLUMN"


def test_bad_client_number_raises_bad_client_number(tmp_path: Path) -> None:
    p = tmp_path / "internal.csv"
    header = ["isin", "record_date", "client_number", "product_code", "account_number", "shares"]

    client, prod = "1234ABCD", 22
    rows = [["GB00B03MLX29", "2026-02-01", client, str(prod), "ignored", "1"]]
    _write_csv(p, header, rows)

    holdings = read_internal_holdings_csv(p)
    with pytest.raises(ValueError) as e:
        validate_internal_holdings(holdings)
    assert str(e.value) == "BAD_CLIENT_NUMBER"


def test_unknown_product_code_raises_unknown_product_code(tmp_path: Path) -> None:
    p = tmp_path / "internal.csv"
    header = ["isin", "record_date", "client_number", "product_code", "account_number", "shares"]

    client, prod = "12345678", 99
    rows = [["GB00B03MLX29", "2026-02-01", client, str(prod), make_account_number(client, 22), "1"]]
    _write_csv(p, header, rows)

    holdings = read_internal_holdings_csv(p)
    with pytest.raises(ValueError) as e:
        validate_internal_holdings(holdings)
    assert str(e.value) == "UNKNOWN_PRODUCT_CODE"


def test_bad_account_number_raises_bad_account_number(tmp_path: Path) -> None:
    p = tmp_path / "internal.csv"
    header = ["isin", "record_date", "client_number", "product_code", "account_number", "shares"]

    client, prod = "12345678", 22
    rows = [["GB00B03MLX29", "2026-02-01", client, str(prod), "WRONG", "1"]]
    _write_csv(p, header, rows)

    holdings = read_internal_holdings_csv(p)
    with pytest.raises(ValueError) as e:
        validate_internal_holdings(holdings)
    assert str(e.value) == "BAD_ACCOUNT_NUMBER"


@pytest.mark.parametrize(
    "shares",
    ["0", "abc"],
)
def test_bad_shares_raises_bad_shares(tmp_path: Path, shares: str) -> None:
    p = tmp_path / "internal.csv"
    header = ["isin", "record_date", "client_number", "product_code", "account_number", "shares"]

    client, prod = "12345678", 22
    rows = [["GB00B03MLX29", "2026-02-01", client, str(prod), make_account_number(client, prod), shares]]
    _write_csv(p, header, rows)

    holdings = read_internal_holdings_csv(p)
    with pytest.raises(ValueError) as e:
        validate_internal_holdings(holdings)
    assert str(e.value) == "BAD_SHARES"


def test_duplicate_key_raises_duplicate_internal_key(tmp_path: Path) -> None:
    p = tmp_path / "internal.csv"
    header = ["isin", "record_date", "client_number", "product_code", "account_number", "shares"]

    client, prod = "12345678", 22
    acct = make_account_number(client, prod)
    rows = [
        ["GB00B03MLX29", "2026-02-01", client, str(prod), acct, "1"],
        ["GB00B03MLX29", "2026-02-01", client, str(prod), acct, "2"],
    ]
    _write_csv(p, header, rows)

    holdings = read_internal_holdings_csv(p)
    with pytest.raises(ValueError) as e:
        validate_internal_holdings(holdings)
    assert str(e.value) == "DUPLICATE_INTERNAL_KEY"