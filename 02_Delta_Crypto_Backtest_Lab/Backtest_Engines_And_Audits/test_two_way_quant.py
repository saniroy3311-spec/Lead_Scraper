import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# Resample to 4H
df = df.set_index('datetime')
df_4h = df.resample('4h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

# 4H Trend & Momentum Indicators
df_4h['ema50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
df_4h['ema200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
df_4h['ema5'] = df_4h['close'].ewm(span=5, adjust=False).mean()

# IBS
df_4h['ibs'] = (df_4h['close'] - df_4h['low']) / (df_4h['high'] - df_4h['low'] + 1e-9)

# 2-period RSI on 4H
delta = df_4h['close'].diff()
gain2 = delta.where(delta > 0, 0.0).rolling(2).mean()
loss2 = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
df_4h['rsi2'] = 100 - (100 / (1 + (gain2 / (loss2 + 1e-9))))

# ATR(14)
tr = np.maximum(df_4h['high'] - df_4h['low'], 
                np.maximum(abs(df_4h['high'] - df_4h['close'].shift(1)), 
                           abs(df_4h['low'] - df_4h['close'].shift(1))))
df_4h['atr'] = tr.rolling(14).mean()

df_4h = df_4h.dropna().reset_index(drop=True)

def run_two_way_quant(fixed_risk=25.0, tp1_r=1.2, tp2_r=2.8, sl_mult=1.8):
    MAKER_FEE = 0.0002
    TAKER_FEE = 0.0005
    SLIPPAGE = 0.5
    FUNDING_PER_8H = 0.0001
    
    trades = []
    in_pos = False
    pos = {}
    
    for i in range(len(df_4h) - 1):
        row = df_4h.iloc[i]
        next_open = df_4h.iloc[i+1]['open']
        next_high = df_4h.iloc[i+1]['high']
        next_low = df_4h.iloc[i+1]['low']
        next_close = df_4h.iloc[i+1]['close']
        next_dt = df_4h.iloc[i+1]['datetime']
        
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
                rem_qty = qty * (0.50 if pos['tp1_hit'] else 1.0)
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                funding = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                pos['realized_pnl'] += (pnl - fees - funding)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars': pos['bars_held'],
                    'reason': 'STOP_LOSS' if not pos['tp1_hit'] else 'BREAKEVEN_STOP'
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                # Close 50% at TP1
                tp1_qty = qty * 0.50
                exit_p = tp1
                pnl = (exit_p - entry_p) * tp1_qty if side == "LONG" else (entry_p - exit_p) * tp1_qty
                fees = (entry_p * tp1_qty * MAKER_FEE) + (exit_p * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                pos['tp1_hit'] = True
                # Move Stop Loss to Break-Even + fee cushion
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                
            if hit_tp2 and pos['tp1_hit']:
                rem_qty = qty * 0.50
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
                    'bars': pos['bars_held'],
                    'reason': 'FULL_TAKE_PROFIT'
                })
                in_pos = False
                pos = {}
                continue
                
            # Mean reversion momentum exit for remaining 50%
            if pos['tp1_hit'] and ((side == "LONG" and next_close > row['ema5']) or (side == "SHORT" and next_close < row['ema5'])):
                rem_qty = qty * 0.50
                exit_p = next_close
                pnl = (exit_p - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_p) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_p * rem_qty * TAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_p,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN',
                    'bars': pos['bars_held'],
                    'reason': 'MOMENTUM_RUNNER_EXIT'
                })
                in_pos = False
                pos = {}
                continue

        if not in_pos:
            is_bull = (row['close'] > row['ema200']) and (row['ema50'] > row['ema200'])
            is_bear = (row['close'] < row['ema200']) and (row['ema50'] < row['ema200'])
            
            # Deep flush trigger
            long_sig = is_bull and (row['ibs'] < 0.20) and (row['rsi2'] < 15)
            short_sig = is_bear and (row['ibs'] > 0.80) and (row['rsi2'] > 85)
            
            if long_sig:
                entry_p = next_open
                sl_dist = sl_mult * row['atr']
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
            elif short_sig:
                entry_p = next_open
                sl_dist = sl_mult * row['atr']
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
    
    total_net = tdf['net_pnl'].sum()
    win_rate = (len(tdf[tdf['net_pnl'] > 0]) / len(tdf)) * 100
    
    monthly_stats = []
    for m, g in tdf.groupby('month'):
        cum = g['net_pnl'].cumsum()
        running_max = np.maximum.accumulate(cum)
        dd = (running_max - cum).max()
        monthly_stats.append({
            'month': str(m),
            'trades': len(g),
            'wins': len(g[g['net_pnl'] > 0]),
            'win_rate': round(len(g[g['net_pnl'] > 0]) / len(g) * 100, 1),
            'net': round(g['net_pnl'].sum(), 2),
            'max_dd': round(dd, 2)
        })
    mdf = pd.DataFrame(monthly_stats)
    red_m = len(mdf[mdf['net'] < 0])
    max_mdd = mdf['max_dd'].max()
    print(f"TP1:{tp1_r} TP2:{tp2_r} SL:{sl_mult} | Trades:{len(tdf):2d} | WinRate:{win_rate:5.1f}% | NetPnL:${total_net:6.2f} | MaxMDD:${max_mdd:5.2f} | RedMonths:{red_m}/{len(mdf)}")
    return tdf, mdf

for tp1 in [1.0, 1.2, 1.4]:
    for tp2 in [2.0, 2.5, 3.0]:
        for sl in [1.5, 1.8, 2.2]:
            run_two_way_quant(fixed_risk=30.0, tp1_r=tp1, tp2_r=tp2, sl_mult=sl)
