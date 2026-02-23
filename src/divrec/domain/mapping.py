from typing import Literal

CrestBucket = Literal["ISA", "SIPP", "GIA"]

ALLOWED_PRODUCT_CODES = {22, 24, 25, 70, 71, 97}

PRODUCT_TO_BUCKET: dict[int, CrestBucket] = {
    22: "ISA",
    24: "ISA",
    25: "ISA",
    70: "SIPP",
    71: "SIPP",
    97: "GIA",
}

HOUSE_CLIENT_NUMBER = "55555555"

HOUSE_PRODUCT_BY_BUCKET: dict[CrestBucket, int] = {
    "ISA": 22,
    "SIPP": 70,
    "GIA": 97,
}


def bucket_for_product(product_code: int) -> CrestBucket:
    try:
        return PRODUCT_TO_BUCKET[product_code]
    except KeyError as exc:
        raise ValueError("UNKNOWN_PRODUCT_CODE") from exc


def make_account_number(client_number: str, product_code: int) -> str:
    return f"{client_number}{product_code:02d}"