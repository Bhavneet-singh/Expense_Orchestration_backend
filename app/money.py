from decimal import Decimal, ROUND_HALF_UP


PAISE_PER_RUPEE = Decimal("100")


def to_paise(amount: Decimal) -> int:
    """Convert rupees to integer paise using half-up rounding."""
    return int(
        (amount * PAISE_PER_RUPEE).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def from_paise(amount: int) -> Decimal:
    """Convert integer paise to rupees with two decimal places."""
    return (Decimal(amount) / PAISE_PER_RUPEE).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
