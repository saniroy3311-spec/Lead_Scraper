import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 15m data
df = pd.read_csv("delta_india_btcusd_15m.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# Session timing: UTC hours
df['hour_utc'] = df['datetime'].dt.hour
# Liquid hours: London & NY (08:00 to 20:00 UTC)
df['liquid_session'] = df['hour_utc'].between(8, 20)

# Rolling VWAP (24h = 96 bars)
cum_vol = df['volume'].rolling(96).sum()
cum_vol_price = (df['close'] * df['volume']).rolling(96).sum()
df['vwap'] = cum_vol_price / (cum_vol + 1e-9)

# Distance to VWAP in %
df['vwap_dist_pct'] = (df['close'] - df['vwap']) / df['vwap'] * 100

# 4H EMA 50 for HTF bias (800 15m bars)
df['htf_ema50'] = df['close'].ewm(span=800, adjust=False).mean()
df['htf_bull'] = df['close'] > df['htf_ema50']
df['htf_bear'] = df['close'] < df['htf_ema50']

# RSI(2)
delta = df['close'].diff()
gain2 = delta.where(delta > 0, 0.0).rolling(2).mean()
loss2 = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
df['rsi2'] = 100 - (100 / (1 + (gain2 / (loss2 + 1e-9))))

# ATR(14)
tr = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift(1)), 
                           abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(14).mean()

df = df.dropna().reset_index(drop=True)

def test_vwap_scalper(risk_usd=8.0, vwap_thresh=0.25, sl_mult=1.2):
    MAKER_FEE = 0.0002
    TAKER_FEE = 0.0005
    SLIPPAGE = 0.5
    
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
            qty = pos['qty']
            side = pos['side']
            
            # SL check
            hit_sl = False
            if side == "LONG" and next_low <= sl:
                hit_sl = True
            elif side == "SHORT" and next_high >= sl:
                hit_sl = True
                
            if hit_sl:
                exit_price = sl - SLIPPAGE if side == "LONG" else sl + SLIPPAGE
                points = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'net_pnl': round(pnl - fees, 2),
                    'result': 'LOSS',
                    'bars': pos['bars_held'],
                    'reason': 'STOP_LOSS'
                })
                in_pos = False
                pos = {}
                continue
                
            # TP check: Price reclaims or touches VWAP!
            reclaimed_vwap = False
            if side == "LONG" and next_high >= row['vwap']:
                reclaimed_vwap = True
                exit_price = row['vwap']
            elif side == "SHORT" and next_low <= row['vwap']:
                reclaimed_vwap = True
                exit_price = row['vwap']
                
            if reclaimed_vwap:
                points = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * MAKER_FEE) # Maker exit at VWAP limit
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'net_pnl': round(pnl - fees, 2),
                    'result': 'WIN' if (pnl - fees) > 0 else 'LOSS',
                    'bars': pos['bars_held'],
                    'reason': 'VWAP_RECLAIM'
                })
                in_pos = False
                pos = {}
                continue
                
            # Time exit after 12 bars (3 hours)
            if pos['bars_held'] >= 12:
                exit_price = next_close
                points = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * TAKER_FEE)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'net_pnl': round(pnl - fees, 2),
                    'result': 'WIN' if (pnl - fees) > 0 else 'LOSS',
                    'bars': pos['bars_held'],
                    'reason': 'TIME_EXIT'
                })
                in_pos = False
                pos = {}
                continue
                
        if not in_pos:
            # Liquid session only
            if not row['liquid_session']:
                continue
                
            # Long Scalp: HTF Bull + Price > 0.25% below VWAP + RSI2 < 10 + Confirmation bar (Close > Prev High)
            long_scalp = row['htf_bull'] and (row['vwap_dist_pct'] < -vwap_thresh) and (row['rsi2'] < 10) and (row['close'] > prev['high'])
            
            # Short Scalp: HTF Bear + Price > 0.25% above VWAP + RSI2 > 90 + Confirmation bar (Close < Prev Low)
            short_scalp = row['htf_bear'] and (row['vwap_dist_pct'] > vwap_thresh) and (row['rsi2'] > 90) and (row['close'] < prev['low'])
            
            if long_scalp:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.004)
                sl_p = entry_p - sl_dist
                qty = risk_usd / sl_dist
                in_pos = True
                pos = {
                    'side': 'LONG',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'bars_held': 0
                }
            elif short_scalp:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.004)
                sl_p = entry_p + sl_dist
                qty = risk_usd / sl_dist
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
    if len(tdf) == 0:
        return
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    
    total_trades = len(tdf)
    wins = len(tdf[tdf['net_pnl'] > 0])
    win_rate = (wins / total_trades) * 100
    total_net = tdf['net_pnl'].sum()
    
    monthly_stats = []
    for m, g in tdf.groupby('month'):
        cum = g['net_pnl'].cumsum()
        running_max = np.maximum.accumulate(cum)
        dd = (running_max - cum).max()
        monthly_stats.append({
            'Month': str(m),
            'Trades': len(g),
            'Wins': len(g[g['net_pnl'] > 0]),
            'Win Rate %': f"{round(len(g[g['net_pnl'] > 0]) / len(g) * 100, 1)}%",
            'Net PnL ($)': round(g['net_pnl'].sum(), 2),
            'Max Drawdown ($)': round(dd, 2),
            'Status': 'GREEN' if g['net_pnl'].sum() > 0 else 'RED'
        })
    mdf = pd.DataFrame(monthly_stats)
    max_mdd = mdf['Max Drawdown ($)'].max()
    print(f"Dist:{vwap_thresh}% SL:{sl_mult} | Trades:{total_trades} (~{total_trades/len(mdf):.0f}/mo) | WinRate:{win_rate:.1f}% | NetPnL:${total_net:.2f} | MaxMDD:${max_mdd:.2f}")
    return mdf

for d in [0.20, 0.35, 0.50]:
    for sl in [1.0, 1.3, 1.6]:
        test_vwap_scalper(risk_usd=10.0, vwap_thresh=d, sl_mult=sl)
