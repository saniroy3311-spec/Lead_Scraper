import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 15m data
df = pd.read_csv("delta_india_btcusd_15m.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# 1. Higher Time Frame (HTF) 4H Indicators calculated directly from 15m (1 4H bar = 16 15m bars)
# 4H 50 EMA = 50 * 16 = 800 bars; 4H 200 EMA = 200 * 16 = 3200 bars
df['htf_ema50'] = df['close'].ewm(span=800, adjust=False).mean()
df['htf_ema200'] = df['close'].ewm(span=3200, adjust=False).mean()
df['htf_bull'] = (df['close'] > df['htf_ema200']) & (df['htf_ema50'] > df['htf_ema200'])
df['htf_bear'] = (df['close'] < df['htf_ema200']) & (df['htf_ema50'] < df['htf_ema200'])

# 2. Intraday Scalp Indicators (15M)
# 15m 20 EMA & Rolling 24H VWAP proxy (96 15m bars in 24 hours)
df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()

# Rolling VWAP (24h = 96 bars)
cum_vol = df['volume'].rolling(96).sum()
cum_vol_price = (df['close'] * df['volume']).rolling(96).sum()
df['vwap'] = cum_vol_price / (cum_vol + 1e-9)

# Bollinger Bands on 15m (20, 2.0)
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']

# Connors RSI(2) on 15m
delta = df['close'].diff()
gain2 = delta.where(delta > 0, 0.0).rolling(2).mean()
loss2 = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
df['rsi2'] = 100 - (100 / (1 + (gain2 / (loss2 + 1e-9))))

# Standard RSI(14) on 15m
gain14 = delta.where(delta > 0, 0.0).rolling(14).mean()
loss14 = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
df['rsi14'] = 100 - (100 / (1 + (gain14 / (loss14 + 1e-9))))

# ATR(14) on 15m for dynamic scalp stops
tr = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift(1)), 
                           abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(14).mean()

# Internal Bar Strength on 15m
df['ibs'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-9)

# Drop initial warmup
df = df.dropna().reset_index(drop=True)

def simulate_intraday_scalper(risk_usd=10.0, tp1_r=1.2, tp2_r=2.5, sl_mult=1.5, rsi_buy=20):
    MAKER_FEE = 0.0002          # 0.02% maker fee on Delta India
    TAKER_FEE = 0.0005          # 0.05% taker fee on Delta India
    SLIPPAGE = 0.5              # 1 tick ($0.50 on BTC)
    FUNDING_PER_8H = 0.0001     # 0.01% funding drag
    
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
                points = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                funding = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 32.0)) # 32 15m bars = 8 hours
                pos['realized_pnl'] += (pnl - fees - funding)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'points': round(points, 1),
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars_held': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                # Lock in 70% of scalp at TP1
                tp1_qty = qty * 0.70
                exit_p = tp1
                points1 = (exit_p - entry_p) if side == "LONG" else (entry_p - exit_p)
                pnl1 = points1 * tp1_qty
                fees1 = (entry_p * tp1_qty * MAKER_FEE) + (exit_p * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl1 - fees1)
                pos['tp1_hit'] = True
                # Move Stop to Breakeven (+0.1% buffer)
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                continue
                
            if hit_tp2 and pos['tp1_hit']:
                rem_qty = qty * 0.30
                exit_p = tp2
                points2 = (exit_p - entry_p) if side == "LONG" else (entry_p - exit_p)
                pnl2 = points2 * rem_qty
                fees2 = (entry_p * rem_qty * MAKER_FEE) + (exit_p * rem_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl2 - fees2)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_p,
                    'points': round(points2, 1),
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN',
                    'bars_held': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            # Stale scalp exit after 16 bars (4 hours)
            if pos['bars_held'] >= 16:
                rem_qty = qty * (0.30 if pos['tp1_hit'] else 1.0)
                exit_p = next_close
                points = (exit_p - entry_p) if side == "LONG" else (entry_p - exit_p)
                pnl = points * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_p * rem_qty * TAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_p,
                    'points': round(points, 1),
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars_held': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue

        if not in_pos:
            # 1. HTF Trend Alignment
            htf_bull = bool(row['htf_bull'])
            htf_bear = bool(row['htf_bear'])
            
            # 2. 15m VWAP & BB Scalp Pullback with Confirmation
            # Long Scalp: HTF Bull + Price below VWAP or touched lower BB + Oversold RSI(2) + Reversal bar (Close > Open)
            long_scalp = htf_bull and (row['low'] <= row['bb_lower'] or row['close'] < row['vwap']) and (row['rsi2'] < rsi_buy) and (row['close'] > row['open'])
            
            # Short Scalp: HTF Bear + Price above VWAP or touched upper BB + Overbought RSI(2) + Reversal bar (Close < Open)
            short_scalp = htf_bear and (row['high'] >= row['bb_upper'] or row['close'] > row['vwap']) and (row['rsi2'] > (100 - rsi_buy)) and (row['close'] < row['open'])
            
            if long_scalp:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.005) # ~0.5% - 0.8% stop
                sl_p = entry_p - sl_dist
                qty = risk_usd / sl_dist
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
            elif short_scalp:
                entry_p = next_open
                sl_dist = max(sl_mult * row['atr'], entry_p * 0.005)
                sl_p = entry_p + sl_dist
                qty = risk_usd / sl_dist
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
        return None, None
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    
    monthly_stats = []
    for m, g in tdf.groupby('month'):
        cum = g['net_pnl'].cumsum()
        running_max = np.maximum.accumulate(cum)
        dd = (running_max - cum).max()
        win_trades = g[g['net_pnl'] > 0]
        monthly_stats.append({
            'Month': str(m),
            'Trades': len(g),
            'Wins': len(win_trades),
            'Win Rate %': f"{round(len(win_trades) / len(g) * 100, 1)}%",
            'Net PnL ($)': round(g['net_pnl'].sum(), 2),
            'Max Drawdown ($)': round(dd, 2),
            'Status': 'GREEN' if g['net_pnl'].sum() > 0 else 'RED'
        })
    mdf = pd.DataFrame(monthly_stats)
    
    total_trades = len(tdf)
    wins = len(tdf[tdf['net_pnl'] > 0])
    win_rate = (wins / total_trades) * 100
    total_net = tdf['net_pnl'].sum()
    max_mdd = mdf['Max Drawdown ($)'].max()
    avg_trades_month = total_trades / len(mdf)
    
    print(f"Risk:${risk_usd} TP1:{tp1_r}R TP2:{tp2_r}R SL:{sl_mult} RSI:{rsi_buy} | Trades:{total_trades} (~{avg_trades_month:.0f}/mo) | WinRate:{win_rate:.1f}% | NetPnL:${total_net:.2f} | MaxMDD:${max_mdd:.2f}")
    return tdf, mdf

for r_usd in [8.0, 10.0, 12.0]:
    for tp1 in [1.0, 1.2, 1.4]:
        for rsi_b in [15, 20, 25]:
            simulate_intraday_scalper(risk_usd=r_usd, tp1_r=tp1, tp2_r=2.5, sl_mult=1.5, rsi_buy=rsi_b)
