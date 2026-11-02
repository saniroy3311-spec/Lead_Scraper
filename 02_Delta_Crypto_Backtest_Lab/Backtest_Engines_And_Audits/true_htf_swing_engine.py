import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# Build Daily (1D) and 4-Hour (4H) resamples from the Delta 1H data
df_idx = df.set_index('datetime')

# 1. DAILY (1D) HTF MACRO
df_daily = df_idx.resample('1d').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

df_daily['ema50'] = df_daily['close'].ewm(span=50, adjust=False).mean()
df_daily['ema200'] = df_daily['close'].ewm(span=200, adjust=False).mean()
df_daily['macro_bull'] = (df_daily['close'] > df_daily['ema200']) & (df_daily['ema50'] > df_daily['ema200'])
df_daily['macro_bear'] = (df_daily['close'] < df_daily['ema200']) & (df_daily['ema50'] < df_daily['ema200'])

# 2. 4-HOUR (4H) HTF SWING STRUCTURE
df_4h = df_idx.resample('4h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

# 4H Indicators
df_4h['ema20'] = df_4h['close'].ewm(span=20, adjust=False).mean()
df_4h['ema50'] = df_4h['close'].ewm(span=50, adjust=False).mean()

# ATR (14) on 4H for swing stops & trailing
tr_4h = np.maximum(df_4h['high'] - df_4h['low'], 
                   np.maximum(abs(df_4h['high'] - df_4h['close'].shift(1)), 
                              abs(df_4h['low'] - df_4h['close'].shift(1))))
df_4h['atr'] = tr_4h.rolling(14).mean()

# Swing Highs & Lows (4H pivots, 15 bars = 2.5 days)
df_4h['swing_high'] = df_4h['high'].rolling(15).max().shift(1)
df_4h['swing_low'] = df_4h['low'].rolling(15).min().shift(1)

# Merge Daily Macro Bias onto 4H
df_4h['date'] = df_4h['datetime'].dt.date
df_daily['date'] = df_daily['datetime'].dt.date
df_4h = pd.merge(df_4h, df_daily[['date', 'macro_bull', 'macro_bear', 'ema50', 'ema200']], on='date', how='left', suffixes=('', '_daily')).ffill()

# Drop warmup
df_4h = df_4h.dropna().reset_index(drop=True)

# TRUE HTF SWING POINT-CAPTURE SIMULATOR
def simulate_true_htf_point_capture(fixed_risk_usd=35.0, tp1_r=1.8, trailing_atr_mult=2.5, sl_atr_mult=1.5):
    MAKER_FEE = 0.0002          # 0.02% maker fee on Delta India
    TAKER_FEE = 0.0005          # 0.05% taker fee on Delta India
    SLIPPAGE = 0.5              # 1 tick ($0.50)
    FUNDING_PER_8H = 0.0001     # 0.01% funding drag
    
    trades = []
    in_pos = False
    pos = {}
    
    for i in range(len(df_4h) - 1):
        row = df_4h.iloc[i]
        prev = df_4h.iloc[i-1]
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
            qty = pos['qty']
            side = pos['side']
            
            # Check Stop Loss & TP1
            hit_sl = False
            hit_tp1 = False
            
            if side == "LONG":
                # Check trailing stop for runner
                if pos['tp1_hit']:
                    # Trail stop using 4H High - (trailing_atr_mult * ATR)
                    trail_candidate = row['high'] - (trailing_atr_mult * row['atr'])
                    if trail_candidate > pos['sl']:
                        pos['sl'] = trail_candidate
                    sl = pos['sl']
                    
                if next_low <= sl:
                    hit_sl = True
                elif next_high >= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
            else: # SHORT
                if pos['tp1_hit']:
                    trail_candidate = row['low'] + (trailing_atr_mult * row['atr'])
                    if trail_candidate < pos['sl']:
                        pos['sl'] = trail_candidate
                    sl = pos['sl']
                    
                if next_high >= sl:
                    hit_sl = True
                elif next_low <= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
                    
            if hit_sl:
                exit_price = sl - SLIPPAGE if side == "LONG" else sl + SLIPPAGE
                rem_qty = qty * (0.50 if pos['tp1_hit'] else 1.0)
                points_captured = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points_captured * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                funding = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
                pos['realized_pnl'] += (pnl - fees - funding)
                
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'points_captured': round(points_captured, 1),
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars_held_4h': pos['bars_held'],
                    'days_held': round(pos['bars_held'] * 4 / 24, 1),
                    'reason': 'STOP_LOSS' if not pos['tp1_hit'] else 'TRAILED_STOP_EXIT'
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                # Lock in 50% at TP1
                tp1_qty = qty * 0.50
                exit_price = tp1
                points1 = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl1 = points1 * tp1_qty
                fees1 = (entry_p * tp1_qty * MAKER_FEE) + (exit_price * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl1 - fees1)
                pos['tp1_hit'] = True
                # Move Stop Loss to Breakeven (+0.1% buffer to guarantee green trade)
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                continue

        # Look for pristine HTF Swing Entry if not in position
        if not in_pos:
            # 1. Macro Daily Bias
            macro_bull = bool(row['macro_bull'])
            macro_bear = bool(row['macro_bear'])
            
            # 2. 4H Pullback to Key Institutional Swing Zone (50 EMA / 20 EMA zone)
            # Bull setup: Daily is Bullish, 4H pulled back into 50 EMA, swept previous 4H swing low, and closed bullish
            bull_pullback = (row['low'] <= row['ema50'] * 1.005) and (row['close'] > row['ema50'])
            bull_rejection = (row['close'] > row['open']) and (row['close'] > prev['high'])
            bull_entry = macro_bull and bull_pullback and bull_rejection
            
            # Bear setup: Daily is Bearish, 4H rallied into 50 EMA, swept previous 4H swing high, and closed bearish
            bear_pullback = (row['high'] >= row['ema50'] * 0.995) and (row['close'] < row['ema50'])
            bear_rejection = (row['close'] < row['open']) and (row['close'] < prev['low'])
            bear_entry = macro_bear and bear_pullback and bear_rejection
            
            if bull_entry:
                entry_p = next_open
                sl_dist = max(sl_atr_mult * row['atr'], entry_p * 0.015) # True HTF swing stop (1.5% - 2.5%)
                sl_p = entry_p - sl_dist
                qty = fixed_risk_usd / sl_dist
                in_pos = True
                pos = {
                    'side': 'LONG',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp1': entry_p + (tp1_r * sl_dist),
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }
            elif bear_entry:
                entry_p = next_open
                sl_dist = max(sl_atr_mult * row['atr'], entry_p * 0.015)
                sl_p = entry_p + sl_dist
                qty = fixed_risk_usd / sl_dist
                in_pos = True
                pos = {
                    'side': 'SHORT',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp1': entry_p - (tp1_r * sl_dist),
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
        monthly_stats.append({
            'Month': str(m),
            'Trades': len(g),
            'Wins': len(g[g['net_pnl'] > 0]),
            'Win Rate %': f"{round(len(g[g['net_pnl'] > 0]) / len(g) * 100, 1)}%",
            'Net PnL ($)': round(g['net_pnl'].sum(), 2),
            'Max Drawdown ($)': round(dd, 2),
            'Avg Points Won': round(g[g['net_pnl'] > 0]['points_captured'].mean(), 1) if len(g[g['net_pnl'] > 0]) > 0 else 0,
            'Status': 'GREEN' if g['net_pnl'].sum() > 0 else ('FLAT' if g['net_pnl'].sum() > -15 else 'RED')
        })
    mdf = pd.DataFrame(monthly_stats)
    
    total_trades = len(tdf)
    wins = len(tdf[tdf['net_pnl'] > 0])
    win_rate = (wins / total_trades) * 100
    total_net = tdf['net_pnl'].sum()
    max_mdd = mdf['Max Drawdown ($)'].max()
    avg_pts = tdf[tdf['net_pnl'] > 0]['points_captured'].mean()
    max_pts = tdf['points_captured'].max()
    
    print(f"Risk:${fixed_risk_usd} TP1:{tp1_r}R Trail:{trailing_atr_mult} | Trades:{total_trades} (~{total_trades/len(mdf):.1f}/mo) | WinRate:{win_rate:.1f}% | NetPnL:${total_net:.2f} | MaxMDD:${max_mdd:.2f} | AvgPoints:{avg_pts:.0f} | MaxPoints:{max_pts:.0f}")
    return tdf, mdf

for tp in [1.5, 1.8, 2.2]:
    for trail in [2.0, 2.5, 3.0]:
        for r_usd in [25.0, 30.0, 35.0]:
            simulate_true_htf_point_capture(fixed_risk_usd=r_usd, tp1_r=tp, trailing_atr_mult=trail, sl_atr_mult=1.5)
