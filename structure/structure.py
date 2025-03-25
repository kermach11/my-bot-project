import pandas as pd

def detect_market_structure(df):
    """
    Визначає останню ринкову структуру:
    HH, LH (по high) або LL, HL (по low)
    """
    df = df.copy()

    # --- Визначаємо локальні high/low
    df["hh"] = (df["high"] > df["high"].shift(1)) & (df["high"] > df["high"].shift(-1))
    df["ll"] = (df["low"] < df["low"].shift(1)) & (df["low"] < df["low"].shift(-1))

    # --- Зберігаємо останні знайдені півоти
    last_high = None
    last_low = None
    structure = None

    for i in range(len(df)):
        if df["hh"].iloc[i]:
            current_high = df["high"].iloc[i]
            if last_high is None:
                last_high = current_high
                structure = "HH"
            else:
                structure = "HH" if current_high > last_high else "LH"
                last_high = current_high

        elif df["ll"].iloc[i]:
            current_low = df["low"].iloc[i]
            if last_low is None:
                last_low = current_low
                structure = "LL"
            else:
                structure = "HL" if current_low > last_low else "LL"
                last_low = current_low

    return structure if structure else "ℹ️ Немає структури"
