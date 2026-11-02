import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 15m data
df = pd.read_csv("delta_india_btcusd_15m.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# 1. Higher Time Frame (HTF) Trend: 4H 50 EMA proxy (800 15m bars)
df['htf_ema50'] = df['close'].ewm(span=800, adjust=False).mean()
df['htf_bull'] = df['close'] > df['htf_ema50']
df['htf_bear'] = df['close'] < df['htf_ema50']

# 2. Rolling 24H VWAP (96 15m bars)
cum_vol = df['volume'].rolling(96).sum()
cum_vol_price = (df['close'] * df['volume']).rolling(96).sum()
df['vwap'] = cum_vol_price / (cum_vol + 1e-9)
df['vwap_dist_pct'] = (df['close'] - df['vwap']) / df['vwap'] * 100

# 3. Connors RSI(2)
delta = df['close'].diff()
gain2 = delta.where(delta > 0, 0.0).rolling(2).mean()
loss2 = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
df['rsi2'] = 100 - (100 / (1 + (gain2 / (loss2 + 1e-9))))

# 4. ATR(14)
tr = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift(1)), 
                           abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(14).mean()

df = df.dropna().reset_index(drop=True)

def test_scalper(risk_usd=8.0, vwap_thresh=0.20, rsi_thresh=15, sl_mult=1.3):
    MAKER_FEE = 0.0002          # 0.02% maker fee on Delta India
    TAKER_FEE = 0.0005          # 0.05% taker fee on Delta India
    SLIPPAGE = 0.5              # 1 tick ($0.50 on BTC)
    
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
            tp = pos['tp']
            qty = pos['qty']
            side = pos['side']
            
            # SL check
            hit_sl = False
            hit_tp = False
            
            if side == "LONG":
                if next_low <= sl:
                    hit_sl = True
                elif next_high >= tp:
                    hit_tp = True
            else:
                if next_high >= sl:
                    hit_sl = True
                elif next_low <= tp:
                    hit_tp = True
                    
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
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp:
                exit_price = tp
                points = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points * qty
                fees = (entry_p * qty * MAKER_FEE) + (exit_price * qty * MAKER_FEE) # Maker limit exit
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'net_pnl': round(pnl - fees, 2),
                    'result': 'WIN',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            # Time exit after 16 bars (4 hours max hold for scalp)
            if pos['bars_held'] >= 16:
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
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue

        if not in_pos:
            # Rebound Entry:
            # Long: HTF Bull + Previous bar was deeply oversold below VWAP + Current bar bounced green
            long_rebound = row['htf_bull'] and (prev['vwap_dist_pct'] < -vwap_thresh) and (prev['rsi2'] < rsi_thresh) and (row['close'] > row['open'])
            
            # Short: HTF Bear + Previous bar was deeply overbought above VWAP + Current bar closed red
            short_rebound = row['htf_bear'] and (prev['vwap_dist_pct'] > vwap_thresh) and (prev['rsi2'] > (100 - rsi_thresh)) and (row['close'] < row['open'])
            
            if long_rebound:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.0035)
                sl_p = entry_p - sl_dist
                # Target: VWAP or minimum 1.2R
                tp_p = max(row['vwap'], entry_p + (1.2 * sl_dist))
                qty = risk_usd / sl_dist
                in_pos = True
                pos = {
                    'side': 'LONG',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp': tp_p,
                    'bars_held': 0
                }
            elif short_rebound:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.0035)
                sl_p = entry_p + sl_dist
                tp_p = min(row['vwap'], entry_p - (1.2 * sl_dist))
                qty = risk_usd / sl_dist
                in_pos = True
                pos = {
                    'side': 'SHORT',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp': tp_p,
                    'bars_held': 0
                }

    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        return None
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
    avg_trades = total_trades / len(mdf)
    print(f"Risk:${risk_usd} VDist:{vwap_thresh}% SL:{sl_mult} | Trades:{total_trades} (~{avg_trades:.0f}/mo) | WinRate:{win_rate:.1f}% | NetPnL:${total_net:.2f} | MaxMDD:${max_mdd:.2f}")
    return tdf, mdf

for r in [6.0, 8.0, 10.0]:
    for sl_m in [1.0, 1.2, 1.5]:
        for vd in [0.15, 0.25]:
            test_scalper(risk_usd=r, vwap_thresh=vd, rsi_thresh=15, sl_mult=sl_m)
