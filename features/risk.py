def calculate_position_size(account_equity, risk_percent, entry_price, stop_loss_price, pair_rate):
    """
    Returns units of base currency to trade for USD/XXX pair.
    pair_rate: current exchange rate (1 USD = X local)
    """
    risk_amount = account_equity * (risk_percent / 100.0)
    stop_distance = abs(entry_price - stop_loss_price)
    if stop_distance == 0 or pair_rate == 0:
        return 0.0
    # Convert stop distance from local currency to USD
    stop_loss_usd = stop_distance / pair_rate
    units = risk_amount / stop_loss_usd
    return round(units, 2)
