"""Plain-Python port of the Kelly engine functions. No pandas / numpy."""


def discrete_kelly_adjusted(returns):
    """Modified discrete Kelly for stock trading.

    f* = (b*p - avg_loss*q) / (b * avg_loss)
    """
    returns = [r for r in returns if r is not None]
    if len(returns) < 2:
        return 0.0

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0

    p = len(wins) / len(returns)
    q = 1 - p
    b = sum(wins) / len(wins)
    avg_loss = sum(abs(r) for r in losses) / len(losses)

    if b == 0 or avg_loss == 0:
        return 0.0

    return (b * p - avg_loss * q) / (b * avg_loss)


def fractional_kelly(f_star, fraction=0.5):
    """Apply a fraction to the raw Kelly value (e.g. Half-Kelly)."""
    return max(0.0, f_star * fraction)
