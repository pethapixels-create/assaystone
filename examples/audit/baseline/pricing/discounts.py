"""Pricing rules for the Assaystone demo."""


def apply_discount(price_cents: int, percent: int) -> int:
    """Apply a percentage discount, rounded half-up to the nearest cent."""
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100")
    discount = int(price_cents * percent / 100)
    return price_cents - discount


def bulk_price(price_cents: int, quantity: int) -> int:
    """Return the total price for a quantity, with 10% off at 10+ units."""
    if quantity >= 10:
        return price_cents * quantity * 9 // 10
    return price_cents * quantity
