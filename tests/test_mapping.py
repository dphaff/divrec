import pytest

from divrec.domain.mapping import bucket_for_product, make_account_number


@pytest.mark.parametrize(
    "product_code,expected_bucket",
    [
        (22, "ISA"),
        (24, "ISA"),
        (25, "ISA"),
        (70, "SIPP"),
        (71, "SIPP"),
        (97, "GIA"),
    ],
)
def test_bucket_for_product_mapping(product_code, expected_bucket):
    assert bucket_for_product(product_code) == expected_bucket


def test_bucket_for_product_unknown_raises():
    with pytest.raises(ValueError) as excinfo:
        bucket_for_product(98)
    assert str(excinfo.value) == "UNKNOWN_PRODUCT_CODE"


@pytest.mark.parametrize(
    "client_number,product_code,expected",
    [
        ("12345678", 22, "1234567822"),
        ("55555555", 97, "5555555597"),
        ("12345678", 7, "1234567807"),
    ],
)
def test_make_account_number_formatting(client_number, product_code, expected):
    assert make_account_number(client_number, product_code) == expected