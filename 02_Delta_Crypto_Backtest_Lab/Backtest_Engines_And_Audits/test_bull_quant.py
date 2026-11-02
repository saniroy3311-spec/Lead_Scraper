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

# Resample to Daily (1D)
df_1d = df.resample('1d').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last'
}).dropna().reset_index()
df_1d['daily_ema100'] = df_1d['close'].ewm(span=100, adjust=False).mean()

# Merge daily trend onto 4H
df_4h['date'] = df_4h['datetime'].dt.date
df_1d['date'] = df_1d['datetime'].dt.date
df_4h = pd.merge(df_4h, df_1d[['date', 'daily_ema100']], on='date', how='left').ffill()

# 4H Indicators
df_4h['ema50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
df_4h['ema200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
df_4h['ema5'] = df_4h['close'].ewm(span=5, adjust=False).mean()

# IBS
df_4h['ibs'] = (df_4h['close'] - df_4h['low']) / (df_4h['high'] - df_4h['low'] + 1e-9)

# 2-period RSI
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

def run_bull_quant_system(fixed_risk=35.0, tp_mult=1.8, sl_mult=2.0, max_hold=12):
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
            tp = pos['tp']
            qty = pos['qty']
            
            # Check SL
            if next_low <= sl:
                exit_price = sl - SLIPPAGE
                pnl = (exit_price - entry_p) * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                funding = entry_p * qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': 'LONG',
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pnl - fees - funding, 2),
                    'result': 'LOSS',
                    'bars': pos['bars_held'],
                    'reason': 'STOP_LOSS'
                })
                in_pos = False
                pos = {}
                continue
                
            # Check TP
            if next_high >= tp:
                exit_price = tp
                pnl = (exit_price - entry_p) * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * MAKER_FEE)
                funding = entry_p * qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': 'LONG',
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pnl - fees - funding, 2),
                    'result': 'WIN',
                    'bars': pos['bars_held'],
                    'reason': 'TAKE_PROFIT'
                })
                in_pos = False
                pos = {}
                continue
                
            # Exit on mean reversion: if close > 5 EMA or IBS > 0.70
            if next_close > row['ema5'] or row['ibs'] > 0.70 or pos['bars_held'] >= max_hold:
                exit_price = next_close
                pnl = (exit_price - entry_p) * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                funding = entry_p * qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': 'LONG',
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pnl - fees - funding, 2),
                    'result': 'WIN' if (pnl - fees - funding) > 0 else 'LOSS',
                    'bars': pos['bars_held'],
                    'reason': 'MEAN_REVERSION'
                })
                in_pos = False
                pos = {}
                continue

        if not in_pos:
            # HTF Bull Trend
            daily_bull = row['close'] > row['daily_ema100']
            h4_bull = row['close'] > row['ema200']
            
            # Deep flush pullback: IBS < 0.15 and RSI2 < 10
            flush = (row['ibs'] < 0.15) and (row['rsi2'] < 10)
            
            if daily_bull and h4_bull and flush:
                entry_p = next_open
                sl_dist = sl_mult * row['atr']
                sl_p = entry_p - sl_dist
                qty = fixed_risk / sl_dist
                in_pos = True
                pos = {
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp': entry_p + (tp_mult * sl_dist),
                    'bars_held': 0
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
    print(f"TP:{tp_mult} SL:{sl_mult} Hold:{max_hold} | Trades:{len(tdf):2d} | WinRate:{win_rate:5.1f}% | NetPnL:${total_net:6.2f} | MaxMDD:${max_mdd:5.2f} | RedMonths:{red_m}/{len(mdf)}")
    return tdf, mdf

for tp in [1.5, 2.0, 2.5]:
    for sl in [1.5, 2.0, 2.5]:
        for hold in [6, 10, 14]:
            run_bull_quant_system(fixed_risk=35.0, tp_mult=tp, sl_mult=sl, max_hold=hold)
