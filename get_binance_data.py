from binance.client import Client
import pandas as pd
import os


def fetch_binance_data(symbol="BTCUSDT", interval="1m", limit=1000):
    api_key = ""
    api_secret = ""
    client = Client(api_key, api_secret)

    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/binance_data.csv")
    print("✅ Дані з Binance збережено в data/binance_data.csv")

if __name__ == "__main__":
    fetch_binance_data()
    import pandas as pd
import os