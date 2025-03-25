
import pandas as pd
import numpy as np
from datetime import datetime
from indicators.indicators import calculate_tsi, detect_tsi_divergence, detect_local_tsi_entry
from structure.structure import detect_market_structure
from utils.utils import confidence_score_update, log_trade_to_csv
from utils.blackbox_logger import log_blackbox
from structure.lux_structure import detect_lux_structure  

# --- Історія впевненості для трейдів ---
previous_confidences = {}

# Замість старої функції run_bot_logic встав цю:
def run_bot_logic(data, symbol):
    df_1h = calculate_tsi(data["1h"])
    df_30m = calculate_tsi(data["30m"])
    df_15m = calculate_tsi(data["15m"])
    df_5m = calculate_tsi(data["5m"])
    df_1m = calculate_tsi(data["1m"])

    divergence_1h = detect_tsi_divergence(df_1h)
    divergence_30m = detect_tsi_divergence(df_30m)
    divergence_15m = detect_tsi_divergence(df_15m)
    divergence_1m = detect_tsi_divergence(df_1m)

    local_div = detect_local_tsi_entry(df_1m)
    market_structure = detect_market_structure(df_1m)
    lux_structure = detect_lux_structure(df_1m)  # 🆕

    tsi_now = df_1m["tsi"].iloc[-1]
    tsi_signal = df_1m["tsi_signal"].iloc[-1]

    trade_key = f"{divergence_1h}_{divergence_30m}_{divergence_15m}_{divergence_1m}_{local_div}_{market_structure}_{lux_structure}"
    previous_score = previous_confidences.get(trade_key, 1.0)
    confidence = confidence_score_update(trade_key, was_success=None)
    previous_confidences[trade_key] = confidence

    # 🧠 Умова входу з LuxAlgo-тригером BOS/CHoCH
    if divergence_1m in ["🔻 Дивергенція", "🔼 Дивергенція"] and \
       local_div.startswith("🔻") and market_structure in ["LH", "LL"] and \
       any(d in ["🔻 Дивергенція", "🔼 Дивергенція"] for d in [divergence_1h, divergence_30m, divergence_15m]) and \
       lux_structure in ["BOS", "CHoCH"]:
        decision = "🔻 ПРОДАЖ"
    elif divergence_1m in ["🔻 Дивергенція", "🔼 Дивергенція"] and \
         local_div.startswith("🔼") and market_structure in ["HH", "HL"] and \
         any(d in ["🔻 Дивергенція", "🔼 Дивергенція"] for d in [divergence_1h, divergence_30m, divergence_15m]) and \
         lux_structure in ["BOS", "CHoCH"]:
        decision = "🔼 КУПІВЛЯ"
    else:
        decision = "🚫 БЕЗ ДІЇ"

    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {symbol} | {decision} | Conf: {round(confidence, 2)}")

    log_blackbox({
        "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": symbol,
        "tsi_now": round(tsi_now, 2),
        "tsi_signal": round(tsi_signal, 2),
        "divergence_1h": divergence_1h,
        "divergence_30m": divergence_30m,
        "divergence_15m": divergence_15m,
        "divergence_1m": divergence_1m,
        "local_signal": local_div,
        "structure": market_structure,
        "lux_structure": lux_structure,  # 🆕
        "confidence": round(confidence, 3),
        "decision": decision
    })

    log_trade_to_csv({
        "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": symbol,
        "tsi_now": round(tsi_now, 2),
        "tsi_signal": round(tsi_signal, 2),
        "divergence_1h": divergence_1h,
        "divergence_30m": divergence_30m,
        "divergence_15m": divergence_15m,
        "divergence_1m": divergence_1m,
        "local_signal": local_div,
        "structure": market_structure,
        "lux_structure": lux_structure,  # 🆕
        "confidence": round(confidence, 3),
        "decision": decision
    })

    return {
        "tsi_now": round(tsi_now, 2),
        "tsi_signal": round(tsi_signal, 2),
        "divergence_1h": divergence_1h,
        "divergence_30m": divergence_30m,
        "divergence_15m": divergence_15m,
        "divergence_1m": divergence_1m,
        "local_signal": local_div,
        "structure": market_structure,
        "lux_structure": lux_structure,  # 🆕
        "confidence": round(confidence, 3),
        "decision": decision
    }