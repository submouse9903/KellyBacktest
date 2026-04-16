"""Signal functions using plain Python lists or RollingWindow. No pandas."""


def _to_list(prices):
    if isinstance(prices, (list, tuple)):
        return list(prices)
    # RollingWindow is iterable oldest-first
    return list(prices)


def golden_cross(prices, short=5, long=20):
    prices = _to_list(prices)
    if len(prices) < long:
        return 0
    sma_short = sum(prices[-short:]) / short
    sma_long = sum(prices[-long:]) / long
    if sma_short > sma_long:
        return 1
    elif sma_short < sma_long:
        return -1
    return 0


def rsi_signal(prices, period=14, oversold=30, overbought=70):
    prices = _to_list(prices)
    if len(prices) < period + 1:
        return 0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    if rsi <= oversold:
        return 1
    elif rsi >= overbought:
        return -1
    return 0


def momentum_breakout(prices, lookback=20):
    prices = _to_list(prices)
    if len(prices) < lookback + 1:
        return 0
    today = prices[-1]
    past = prices[-lookback - 1 : -1]
    highest = max(past)
    lowest = min(past)
    if today > highest:
        return 1
    elif today < lowest:
        return -1
    return 0


def bollinger_signal(prices, period=20, std=2.0):
    prices = _to_list(prices)
    if len(prices) < period:
        return 0
    window = prices[-period:]
    ma = sum(window) / period
    variance = sum((p - ma) ** 2 for p in window) / period
    sigma = variance ** 0.5
    upper = ma + std * sigma
    lower = ma - std * sigma
    today = prices[-1]
    if today <= lower:
        return 1
    elif today >= upper:
        return -1
    return 0


def macd_signal(prices, fast=12, slow=26, signal=9):
    """MACD 상태 (+1: MACD > Signal, -1: MACD < Signal, 0: 불명확)
    
    +1: MACD 라인이 시그널 라인 위에 있는 구간
    -1: MACD 라인이 시그널 라인 아래에 있는 구간
     0: 기간 부족
    """
    prices = _to_list(prices)
    if len(prices) < slow + signal:
        return 0
    
    def _ema(data, span):
        alpha = 2.0 / (span + 1.0)
        ema = [data[0]]
        for price in data[1:]:
            ema.append(alpha * price + (1 - alpha) * ema[-1])
        return ema
    
    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal)
    
    if macd_line[-1] > signal_line[-1]:
        return 1
    elif macd_line[-1] < signal_line[-1]:
        return -1
    return 0


def get_signal(name, prices, **kwargs):
    mapping = {
        "golden_cross": golden_cross,
        "rsi": rsi_signal,
        "momentum_breakout": momentum_breakout,
        "bollinger": bollinger_signal,
        "macd": macd_signal,
    }
    fn = mapping.get(name)
    if fn is None:
        raise ValueError(f"Unknown signal: {name}")
    return fn(prices, **kwargs)
