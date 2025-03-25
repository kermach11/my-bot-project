import pandas as pd
from scipy.signal import argrelextrema
import numpy as np

def find_tsi_divergence(df: pd.DataFrame, order: int = 5):
    """
    Знаходить TSI-дивергенції між ціною та індикатором TSI
    """
    if 'close' not in df.columns or 'tsi' not in df.columns:
        return {'divergence': None}

    df = df.copy()
    df['price_max'] = df['close'].iloc[argrelextrema(df['close'].values, np.greater_equal, order=order)[0]]
    df['price_min'] = df['close'].iloc[argrelextrema(df['close'].values, np.less_equal, order=order)[0]]
    df['tsi_max'] = df['tsi'].iloc[argrelextrema(df['tsi'].values, np.greater_equal, order=order)[0]]
    df['tsi_min'] = df['tsi'].iloc[argrelextrema(df['tsi'].values, np.less_equal, order=order)[0]]

    # Bearish divergence: higher high in price, lower high in TSI
    price_highs = df.dropna(subset=['price_max'])[-2:]
    tsi_highs = df.dropna(subset=['tsi_max'])[-2:]
    if len(price_highs) == 2 and len(tsi_highs) == 2:
        if price_highs['price_max'].iloc[1] > price_highs['price_max'].iloc[0] and \
           tsi_highs['tsi_max'].iloc[1] < tsi_highs['tsi_max'].iloc[0]:
            return {
                'divergence': 'bearish',
                'price_point_1': price_highs['price_max'].iloc[0],
                'price_point_2': price_highs['price_max'].iloc[1],
                'tsi_point_1': tsi_highs['tsi_max'].iloc[0],
                'tsi_point_2': tsi_highs['tsi_max'].iloc[1]
            }

    # Bullish divergence: lower low in price, higher low in TSI
    price_lows = df.dropna(subset=['price_min'])[-2:]
    tsi_lows = df.dropna(subset=['tsi_min'])[-2:]
    if len(price_lows) == 2 and len(tsi_lows) == 2:
        if price_lows['price_min'].iloc[1] < price_lows['price_min'].iloc[0] and \
           tsi_lows['tsi_min'].iloc[1] > tsi_lows['tsi_min'].iloc[0]:
            return {
                'divergence': 'bullish',
                'price_point_1': price_lows['price_min'].iloc[0],
                'price_point_2': price_lows['price_min'].iloc[1],
                'tsi_point_1': tsi_lows['tsi_min'].iloc[0],
                'tsi_point_2': tsi_lows['tsi_min'].iloc[1]
            }

    return {'divergence': None}