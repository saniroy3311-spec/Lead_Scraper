import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

df = df.set_index('datetime')
df_4h = df.resample('4h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

df_4h['ema50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
df_4h['ema200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
df_4h['ema5'] = df_4h['close'].ewm(span=5, adjust=False).mean()
df_4h['ibs'] = (df_4h['close'] - df_4h['low']) / (df_4h['high'] - df_4h['low'] + 1e-9)

delta = df_4h['close'].diff()
gain2 = delta.where(delta > 0, 0.0).rolling(2).mean()
loss2 = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
df_4h['rsi2'] = 100 - (100 / (1 + (gain2 / (loss2 + 1e-9))))

tr = np.maximum(df_4h['high'] - df_4h['low'], 
                np.maximum(abs(df_4h['high'] - df_4h['close'].shift(1)), 
                           abs(df_4h['low'] - df_4h['close'].shift(1))))
df_4h['atr'] = tr.rolling(14).mean()

# Waterfall filter (ADX & Directional Movement)
plus_dm = df_4h['high'].diff()
minus_dm = df_4h['low'].diff()
plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), -minus_dm, 0.0)
tr_smooth = tr.rolling(14).mean()
plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
df_4h['adx'] = dx.rolling(14).mean()
df_4h['minus_di'] = minus_di
df_4h['plus_di'] = plus_di

# Daily 50 EMA on 4H
df_4h['daily_ema50'] = df_4h['close'].ewm(span=300, adjust=False).mean()

df_4h = df_4h.dropna().reset_index(drop=True)

def audit_waterfall_filter(fixed_risk=22.0, sl_mult=1.8):
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
            qty = pos['qty']
            side = pos['side']
            
            # Check Stop Loss
            if side == "LONG" and next_low <= sl:
                exit_price = sl - SLIPPAGE
                pnl = (exit_price - entry_p) * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                funding = entry_p * qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pnl - fees - funding, 2),
                    'result': 'LOSS',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
            elif side == "SHORT" and next_high >= sl:
                exit_price = sl + SLIPPAGE
                pnl = (entry_p - exit_price) * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                funding = entry_p * qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pnl - fees - funding, 2),
                    'result': 'LOSS',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            # Exit on mean reversion: if close > 5 EMA or IBS > 0.75
            exit_cond = False
            if side == "LONG" and (next_close > row['ema5'] or row['ibs'] > 0.75):
                exit_cond = True
            elif side == "SHORT" and (next_close < row['ema5'] or row['ibs'] < 0.25):
                exit_cond = True
                
            if exit_cond:
                exit_price = next_close
                pnl = (exit_price - entry_p) * qty if side == "LONG" else (entry_p - exit_price) * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                funding = entry_p * qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pnl - fees - funding, 2),
                    'result': 'WIN' if (pnl - fees - funding) > 0 else 'LOSS',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
        if not in_pos:
            is_bull = row['close'] > row['ema200']
            is_bear = row['close'] < row['ema200']
            
            # Waterfall crash protection: don't buy long if minus_di > 35 and ADX > 35 (extreme violent selloff)
            waterfall_crash = (row['adx'] > 35) and (row['minus_di'] > 35)
            
            long_sig = is_bull and (not waterfall_crash) and (row['ibs'] < 0.25) and (row['rsi2'] < 10)
            short_sig = is_bear and (not (row['adx'] > 35 and row['plus_di'] > 35)) and (row['ibs'] > 0.75) and (row['rsi2'] > 90)
            
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
                    'bars_held': 0
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
                    'bars_held': 0
                }

    tdf = pd.DataFrame(trades)
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    
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
            'net_pnl': round(g['net_pnl'].sum(), 2),
            'max_dd': round(dd, 2),
            'status': 'GREEN' if g['net_pnl'].sum() > 0 else 'RED'
        })
    mdf = pd.DataFrame(monthly_stats)
    print("="*80)
    print("FINAL OPTIMIZED RESULTS (WITH WATERFALL PROTECTION ON DELTA INDIA DATA)")
    print("="*80)
    print(mdf.to_string(index=False))
    print("="*80)
    print(f"Total Trades: {len(tdf)}")
    print(f"Total Net PnL: ${tdf['net_pnl'].sum():.2f}")
    print(f"Win Rate: {(len(tdf[tdf['net_pnl'] > 0]) / len(tdf))*100:.1f}%")
    print(f"Max Monthly Drawdown Across All Months: ${mdf['max_dd'].max():.2f}")
    return tdf, mdf

audit_waterfall_filter()
