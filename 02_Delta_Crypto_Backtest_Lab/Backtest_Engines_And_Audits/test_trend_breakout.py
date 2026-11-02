import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# Daily 50 EMA & 200 EMA (50 * 24 = 1200, 200 * 24 = 4800)
# Or 4H 50 EMA (200 bars) & 4H 200 EMA (800 bars)
df['ema_fast'] = df['close'].ewm(span=200, adjust=False).mean()
df['ema_slow'] = df['close'].ewm(span=800, adjust=False).mean()

# ATR (24 bars = 1 day)
tr = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift(1)), 
                           abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(window=24).mean()

# Donchian Breakout Channels (48 hours = 2 days)
df['donchian_high'] = df['high'].rolling(48).max().shift(1)
df['donchian_low'] = df['low'].rolling(48).min().shift(1)

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

df = df.dropna().reset_index(drop=True)

def test_trend_breakout(fixed_risk=30.0, atr_sl=1.5, tp1_r=2.0, tp2_r=5.0):
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
                rem_qty = qty * (0.40 if pos['tp1_hit'] else 1.0)
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
                tp1_qty = qty * 0.60
                exit_p = tp1
                pnl = (exit_p - entry_p) * tp1_qty if side == "LONG" else (entry_p - exit_p) * tp1_qty
                fees = (entry_p * tp1_qty * MAKER_FEE) + (exit_p * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                pos['tp1_hit'] = True
                # Move Stop to Break-Even + 0.15% fee buffer
                pos['sl'] = entry_p + (entry_p * 0.0015) if side == "LONG" else entry_p - (entry_p * 0.0015)
                
            if hit_tp2 and pos['tp1_hit']:
                rem_qty = qty * 0.40
                exit_p = tp2
                pnl = (exit_p - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_p) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_p * rem_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_p,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            # Trailing stop on 20 EMA
            if pos['tp1_hit']:
                cur_ema20 = df.iloc[i]['close']
                if side == "LONG" and next_close < row['donchian_low']:
                    rem_qty = qty * 0.40
                    exit_p = next_close
                    pnl = (exit_p - entry_p) * rem_qty
                    fees = (entry_p * rem_qty * MAKER_FEE) + (exit_p * rem_qty * TAKER_FEE)
                    pos['realized_pnl'] += (pnl - fees)
                    trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': next_dt,
                        'side': side,
                        'entry_price': entry_p,
                        'exit_price': exit_p,
                        'net_pnl': round(pos['realized_pnl'], 2),
                        'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                        'bars': pos['bars_held']
                    })
                    in_pos = False
                    pos = {}
                    continue

        if not in_pos:
            # Macro Trend
            is_bull = (row['close'] > row['ema_slow']) and (row['ema_fast'] > row['ema_slow'])
            is_bear = (row['close'] < row['ema_slow']) and (row['ema_fast'] < row['ema_slow'])
            trend_active = row['adx'] > 22
            
            # Donchian Breakout
            long_break = is_bull and trend_active and (row['close'] > row['donchian_high']) and (prev['close'] <= prev['donchian_high'])
            short_break = is_bear and trend_active and (row['close'] < row['donchian_low']) and (prev['close'] >= prev['donchian_low'])
            
            if long_break:
                entry_p = next_open
                sl_dist = max(atr_sl * row['atr'], entry_p * 0.012)
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
            elif short_break:
                entry_p = next_open
                sl_dist = max(atr_sl * row['atr'], entry_p * 0.012)
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
        print("No trades")
        return
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    
    total_net = tdf['net_pnl'].sum()
    win_rate = (len(tdf[tdf['net_pnl'] > 0]) / len(tdf)) * 100
    print(f"Total Trades: {len(tdf)} | Win Rate: {win_rate:.1f}% | Net PnL: ${total_net:.2f}")
    
    for m, g in tdf.groupby('month'):
        cum = g['net_pnl'].cumsum()
        running_max = np.maximum.accumulate(cum)
        dd = (running_max - cum).max()
        print(f"  {m}: Trades={len(g):2d}, Net=${g['net_pnl'].sum():6.2f}, MaxDD=${dd:5.2f}")

test_trend_breakout(fixed_risk=35.0, atr_sl=1.2, tp1_r=1.5, tp2_r=4.0)
