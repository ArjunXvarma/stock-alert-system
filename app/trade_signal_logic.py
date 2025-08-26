def compute_cvd_ohlc(price_open, price_close, volume, prev_cum_delta=None):
    """
    Compute synthetic CVD OHLC values from price + volume.

    Args:
        price_open (float): Candle open price
        price_close (float): Candle close price
        volume (float): Candle traded volume
        prev_cum_delta (float or None): Previous cumulative delta value

    Returns:
        tuple: (cvd_open, cvd_high, cvd_low, cvd_close, cum_delta)
    """

    # --- Classify volume into up or down ---
    if price_close > price_open:
        up_vol = volume
        down_vol = 0.0
    elif price_close < price_open:
        up_vol = 0.0
        down_vol = volume
    else:
        up_vol = down_vol = 0.0

    # --- Delta = buy volume - sell volume ---
    delta = up_vol - down_vol

    # --- Update cumulative delta ---
    cum_delta = (prev_cum_delta if prev_cum_delta is not None else 0.0) + delta

    # --- Build synthetic OHLC for CVD ---
    cvd_open = prev_cum_delta if prev_cum_delta is not None else cum_delta
    cvd_close = cum_delta
    cvd_high = max(cvd_open, cvd_close)
    cvd_low = min(cvd_open, cvd_close)

    return cvd_open, cvd_high, cvd_low, cvd_close, cum_delta
