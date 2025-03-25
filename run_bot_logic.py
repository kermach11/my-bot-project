import pandas as pd
import numpy as np
from lux_structure import get_lux_structure_signal
from tsi_divergence import find_tsi_divergence
from confidence import calculate_confidence_score, confidence_score_update  # 🧠 Додано адаптивну оцінку
from utils.log_trade_to_csv import log_trade  # 🧠 Новий логер трейду

# 🔁 Завантаження даних (з Binance або локального файлу)
data_path = 'data/binance_data.csv'
try:
    df = pd.read_csv(data_path)
except:
    data_path = 'data/historical_data.csv'
    df = pd.read_csv(data_path)

print(f"📥 Завантажено дані з: {data_path}")

# Обробка часу та колонок
df.index = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df.index)

# 🧮 Обчислення TSI
def calculate_tsi(close, long=25, short=13):
    diff = close.diff()
    abs_diff = diff.abs()
    double_smoothed_diff = diff.ewm(span=short).mean().ewm(span=long).mean()
    double_smoothed_abs = abs_diff.ewm(span=short).mean().ewm(span=long).mean()
    tsi = 100 * (double_smoothed_diff / double_smoothed_abs)
    return tsi

df['tsi'] = calculate_tsi(df['close'])

results = []
window = 50

trades_executed = []
confidence_memory = {}

for i in range(window, len(df)):
    slice_df = df.iloc[:i].copy()
    current_time = df.index[i]
    current_price = df['close'].iloc[i]
    volume_high = slice_df['volume'].iloc[-1] > slice_df['volume'].rolling(20).mean().iloc[-1]

    tsi_signal = find_tsi_divergence(slice_df)
    tsi_divergence = bool(tsi_signal['divergence'])

    lux_result = get_lux_structure_signal(slice_df)

    # 🧠 Ключ трейду для памʼяті
    trade_key = f"{tsi_signal['divergence']}_{lux_result['BOS']}_{lux_result['CHoCH']}_{volume_high}"
    confidence = confidence_score_update(trade_key, None, confidence_memory)

    if (lux_result['BOS'] or lux_result['CHoCH']) and confidence >= 0.5:
        decision = 'buy' if lux_result['direction'] == 'up' else 'sell'
        print(f"✅ Вхід ({decision.upper()}) | Час: {current_time} | Напрям: {lux_result['direction']}")

        entry_price = current_price
        tp = round(entry_price * (1.01 if decision == 'buy' else 0.99), 2)
        sl = round(entry_price * (0.995 if decision == 'buy' else 1.005), 2)
        rr_ratio = round(abs(tp - entry_price) / abs(entry_price - sl), 2)

        log_trade({
            'time': current_time.isoformat(),
            'entry': decision,
            'price': entry_price,
            'tp': tp,
            'sl': sl,
            'rr': rr_ratio,
            'tsi_divergence': tsi_signal['divergence'],
            'lux_structure': 'BOS' if lux_result['BOS'] else 'CHoCH' if lux_result['CHoCH'] else None,
            'direction': lux_result['direction'],
            'volume_high': volume_high,
            'confidence_score': confidence
        })

        pnl = tp - entry_price if decision == 'buy' else entry_price - tp
        trades_executed.append({
            'entry': decision,
            'entry_price': entry_price,
            'tp': tp,
            'sl': sl,
            'confidence': confidence,
            'pnl': pnl
        })

        # 🧠 Підвищення впевненості
        confidence_score_update(trade_key, True, confidence_memory)
    else:
        decision = 'hold'
        tp = sl = rr_ratio = None
        print(f"⛔ Пропуск | {current_time}")
        with open('debug_log.txt', 'a', encoding='utf-8') as dbg:
            dbg.write(f"⛔ NO ENTRY | Time: {current_time}\n")
            if not tsi_divergence:
                dbg.write("Причина: TSI-дивергенція відсутня\n")
            if not volume_high:
                dbg.write("Причина: недостатній обʼєм\n")
            if not (lux_result['BOS'] or lux_result['CHoCH']):
                dbg.write("Причина: LuxAlgo не дав BOS/CHoCH\n")
            if confidence < 0.5:
                dbg.write(f"Причина: низький confidence_score = {confidence}\n")
            dbg.write("---\n")

        # 🧠 Зниження впевненості
        confidence_score_update(trade_key, False, confidence_memory)

    results.append({
        'time': current_time.isoformat(),
        'entry': decision,
        'price': current_price,
        'tp': tp,
        'sl': sl,
        'rr': rr_ratio,
        'tsi_divergence': tsi_signal['divergence'],
        'lux_structure': 'BOS' if lux_result['BOS'] else 'CHoCH' if lux_result['CHoCH'] else None,
        'direction': lux_result['direction'],
        'volume_high': volume_high,
        'confidence_score': confidence
    })

pd.DataFrame(results).to_csv('results.csv', index=False)
print("📊 Бектест завершено → results.csv")

# 📈 performance.csv: підсумкова статистика
if trades_executed:
    df_perf = pd.DataFrame(trades_executed)
    total_pnl = round(df_perf['pnl'].sum(), 2)
    winrate = round((df_perf['pnl'] > 0).mean() * 100, 2)
    avg_profit = round(df_perf[df_perf['pnl'] > 0]['pnl'].mean(), 2)
    avg_loss = round(df_perf[df_perf['pnl'] <= 0]['pnl'].mean(), 2)

    pd.DataFrame([{
        'Total Trades': len(df_perf),
        'Total PnL': total_pnl,
        'Winrate (%)': winrate,
        'Avg Profit': avg_profit,
        'Avg Loss': avg_loss
    }]).to_csv('performance.csv', index=False)

    print("📈 performance.csv збережено")
else:
    print("⚠️ Жодної угоди не було виконано → performance.csv не створено")
