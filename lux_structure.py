
import pandas as pd

def get_lux_structure_signal(df):
    """
    Аналізує структуру ринку, як у LuxAlgo: HH, LL, LH, HL + BOS/CHoCH
    """
    if len(df) < 20 or not {'high', 'low'}.issubset(df.columns):
        return {"direction": None, "BOS": False, "CHoCH": False, "last_structure": None}

    highs = df['high'].values
    lows = df['low'].values

    structure = []
    direction = None
    bos = False
    choch = False

    swing_points = []

    for i in range(2, len(df) - 2):
        if highs[i] > highs[i-2] and highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            swing_points.append((df.index[i], 'high', highs[i]))
        elif lows[i] < lows[i-2] and lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            swing_points.append((df.index[i], 'low', lows[i]))

    if len(swing_points) < 3:
        return {"direction": None, "BOS": False, "CHoCH": False, "last_structure": None}

    p1 = swing_points[-3]
    p2 = swing_points[-2]
    p3 = swing_points[-1]

    def get_type(p1, p2):
        if p1[1] == 'high' and p2[1] == 'high':
            return 'HH' if p2[2] > p1[2] else 'LH'
        elif p1[1] == 'low' and p2[1] == 'low':
            return 'LL' if p2[2] < p1[2] else 'HL'
        return None

    type1 = get_type(p1, p2)
    type2 = get_type(p2, p3)

    if type1 and type2:
        structure.append(type2)
        if type1 in ['HH', 'HL'] and type2 in ['LH', 'LL']:
            direction = 'down'
            choch = True if type1 == 'HH' and type2 == 'LL' else False
            bos = True if type1 == 'HL' and type2 == 'LL' else False
        elif type1 in ['LL', 'LH'] and type2 in ['HH', 'HL']:
            direction = 'up'
            choch = True if type1 == 'LL' and type2 == 'HH' else False
            bos = True if type1 == 'LH' and type2 == 'HH' else False

    return {
        "direction": direction,
        "BOS": bos,
        "CHoCH": choch,
        "last_structure": structure[-1] if structure else None
    }
