# plugins/exchanges/east_africa.py
import requests
import datetime

CURRENCIES = ["KES", "UGX", "TZS", "ETB", "RWF", "BIF", "SSP", "SOS"]

def get_rates(base="USD"):
    """
    Fetch live FX rates for East African currencies.
    Returns dict: {currency: rate}
    """
    url = f"https://api.exchangerate.host/latest?base={base}&symbols={','.join(CURRENCIES)}"
    resp = requests.get(url)
    data = resp.json()
    rates = data.get("rates", {})
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "base": base,
        "rates": rates
    }

if __name__ == "__main__":
    print(get_rates())
