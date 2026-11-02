import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# Higher Time Frame Trend (4H EMA 50 & 200 equivalent)
df['ema_fast'] = df['close'].ewm(span=200, adjust=False).mean()
df['ema_slow'] = df['close'].ewm(span=800, adjust=False).mean()

# ATR
tr = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift(1)), 
                           abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(window=14).mean()

# ADX
plus_dm = df['high'].diff()
minus_dm = df['low'].diff()
plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), -minus_dm, 0.0)
tr_smooth = tr.rolling(14).mean()
plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
df['adx'] = dx.rolling(14).mean()

# RSI
delta = df['close'].diff()
gain14 = delta.where(delta > 0, 0.0).rolling(14).mean()
loss14 = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
rs14 = gain14 / (loss14 + 1e-9)
df['rsi'] = 100 - (100 / (1 + rs14))

# Williams %R
highest_high = df['high'].rolling(14).max()
lowest_low = df['low'].rolling(14).min()
df['williams_r'] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low + 1e-9))

df = df.dropna().reset_index(drop=True)

def simulate_config(fixed_risk=30.0, rsi_buy_thresh=35, tp1_r=1.2, tp2_r=3.5, sl_mult=1.5):
    MAKER_FEE = 0.0002
    TAKER_FEE = 0.0005
    SLIPPAGE = 0.5
    FUNDING_PER_8H = 0.0001
    
    trades = []
    in_pos = False
    pos = {}
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        next_open = df.iloc[i+1]['open']
        next_high = df.iloc[i+1]['high']
        next_low = df.iloc[i+1]['low']
        next_close = df.iloc[i+1]['close']
        next_dt = df.iloc[i+1]['datetime']
        
        if in_pos:
            pos['bars_held'] += 1
            entry_p = pos['entry_price']
            sl = pos['sl']
            tp1 = pos['tp1']
            tp2 = pos['tp2']
            qty = pos['qty']
            side = pos['side']
            
            hit_sl = False
            hit_tp1 = False
            hit_tp2 = False
            
            if side == "LONG":
                if next_low <= sl:
                    hit_sl = True
                elif next_high >= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
                elif pos['tp1_hit'] and next_high >= tp2:
                    hit_tp2 = True
            else:
                if next_high >= sl:
                    hit_sl = True
                elif next_low <= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
                elif pos['tp1_hit'] and next_low <= tp2:
                    hit_tp2 = True
                    
            if hit_sl:
                exit_price = sl - SLIPPAGE if side == "LONG" else sl + SLIPPAGE
                rem_qty = qty * (0.30 if pos['tp1_hit'] else 1.0)
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                funding = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 8.0))
                pos['realized_pnl'] += (pnl - fees - funding)
                
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                tp1_qty = qty * 0.70
                exit_price = tp1
                pnl = (exit_price - entry_p) * tp1_qty if side == "LONG" else (entry_p - exit_price) * tp1_qty
                fees = (entry_p * tp1_qty * MAKER_FEE) + (exit_price * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                pos['tp1_hit'] = True
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                
            if hit_tp2 and pos['tp1_hit']:
                rem_qty = qty * 0.30
                exit_price = tp2
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            if pos['bars_held'] >= 48:
                rem_qty = qty * (0.30 if pos['tp1_hit'] else 1.0)
                exit_price = next_close
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue

        if not in_pos:
            htf_bull = (row['close'] > row['ema_slow']) and (row['ema_fast'] > row['ema_slow'])
            htf_bear = (row['close'] < row['ema_slow']) and (row['ema_fast'] < row['ema_slow'])
            
            trend_ok = row['adx'] > 18
            
            bull_trigger = (htf_bull and trend_ok and 
                            (prev['rsi'] < rsi_buy_thresh or prev['williams_r'] < -80) and 
                            (row['close'] > row['open']) and 
                            (row['close'] > prev['high']))
                            
            bear_trigger = (htf_bear and trend_ok and 
                            (prev['rsi'] > (100 - rsi_buy_thresh) or prev['williams_r'] > -20) and 
                            (row['close'] < row['open']) and 
                            (row['close'] < prev['low']))
            
            if bull_trigger:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.008)
                sl_p = entry_p - sl_dist
                qty = fixed_risk / sl_dist
                in_pos = True
                pos = {
                    'side': 'LONG',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp1': entry_p + (tp1_r * sl_dist),
                    'tp2': entry_p + (tp2_r * sl_dist),
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }
            elif bear_trigger:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.008)
                sl_p = entry_p + sl_dist
                qty = fixed_risk / sl_dist
                in_pos = True
                pos = {
                    'side': 'SHORT',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp1': entry_p - (tp1_r * sl_dist),
                    'tp2': entry_p - (tp2_r * sl_dist),
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }

    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        return None
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    return tdf

# Test a set of configs
results = []
for sl in [1.2, 1.5, 1.8]:
    for tp in [1.0, 1.3, 1.6]:
        for rsi in [32, 38, 42]:
            tdf = simulate_config(fixed_risk=25.0, rsi_buy_thresh=rsi, tp1_r=tp, sl_mult=sl)
            if tdf is not None and len(tdf) > 10:
                win_rate = (len(tdf[tdf['net_pnl'] > 0]) / len(tdf)) * 100
                net = tdf['net_pnl'].sum()
                months = tdf['month'].unique()
                red_m = sum(1 for m, g in tdf.groupby('month') if g['net_pnl'].sum() < 0)
                max_dd = 0
                for m, g in tdf.groupby('month'):
                    cum = g['net_pnl'].cumsum()
                    running_max = np.maximum.accumulate(cum)
                    dd = (running_max - cum).max()
                    if dd > max_dd:
                        max_dd = dd
                results.append({
                    'sl': sl, 'tp': tp, 'rsi': rsi,
                    'trades': len(tdf),
                    'win_rate': round(win_rate, 1),
                    'net': round(net, 2),
                    'max_mdd': round(max_dd, 2),
                    'red_m': red_m,
                    'total_m': len(months)
                })

res_df = pd.DataFrame(results).sort_values(by=['red_m', 'net'], ascending=[True, False])
print(res_df.head(10).to_string(index=False))
