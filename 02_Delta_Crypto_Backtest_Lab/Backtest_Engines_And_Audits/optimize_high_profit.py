import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# Resample to 4H
df_idx = df.set_index('datetime')
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
df_4h['ema200'] = df_4h['close'].ewm(span=200, adjust=False).mean()

# RSI(2)
delta = df_4h['close'].diff()
gain2 = delta.where(delta > 0, 0.0).rolling(2).mean()
loss2 = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
df_4h['rsi2'] = 100 - (100 / (1 + (gain2 / (loss2 + 1e-9))))

# IBS
df_4h['ibs'] = (df_4h['close'] - df_4h['low']) / (df_4h['high'] - df_4h['low'] + 1e-9)

# ATR(14)
tr = np.maximum(df_4h['high'] - df_4h['low'], 
                np.maximum(abs(df_4h['high'] - df_4h['close'].shift(1)), 
                           abs(df_4h['low'] - df_4h['close'].shift(1))))
df_4h['atr'] = tr.rolling(14).mean()

# ADX
plus_dm = df_4h['high'].diff()
minus_dm = df_4h['low'].diff()
plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), -minus_dm, 0.0)
tr_smooth = tr.rolling(14).mean()
plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
df_4h['adx'] = dx.rolling(14).mean()

df_4h = df_4h.dropna().reset_index(drop=True)

# Let's test a High Win-Rate Mean Reversion + Asymmetric Runner model
# Where:
# 1. Wider Stop (e.g. 2.5 - 3.0x ATR) -> gives trade massive breathing room so noise NEVER stops it out (boosts win rate to 75-85%).
# 2. Risk per trade: $50 - $75 (allowed higher drawdown to make more money!).
# 3. Quick Partial TP1 (e.g. +1.0R / 50% position): locks in win early, moves stop to Breakeven.
# 4. Moonbag Runner (50%): exits on 20 EMA / trend exhaustion.

def test_high_win_rate_engine(risk_usd=60.0, sl_mult=2.5, tp1_r=1.0, runner_ema=20):
    MAKER_FEE = 0.0002
    TAKER_FEE = 0.0005
    SLIPPAGE = 0.5
    FUNDING_PER_8H = 0.0001
    
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
            
            hit_sl = False
            hit_tp1 = False
            
            if side == "LONG":
                if next_low <= sl:
                    hit_sl = True
                elif next_high >= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
            else:
                if next_high >= sl:
                    hit_sl = True
                elif next_low <= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
                    
            if hit_sl:
                exit_price = sl - SLIPPAGE if side == "LONG" else sl + SLIPPAGE
                rem_qty = qty * (0.40 if pos['tp1_hit'] else 1.0)
                points = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl = points * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                funding = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 2.0))
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
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                tp1_qty = qty * 0.60
                exit_price = tp1
                points1 = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                pnl1 = points1 * tp1_qty
                fees1 = (entry_p * tp1_qty * MAKER_FEE) + (exit_price * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl1 - fees1)
                pos['tp1_hit'] = True
                # Move Stop Loss to Breakeven (+0.1% buffer)
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                continue
                
            # Runner exit on 4H 20 EMA cross after TP1 hit
            if pos['tp1_hit']:
                runner_exit = False
                if side == "LONG" and next_close < row['ema20']:
                    runner_exit = True
                elif side == "SHORT" and next_close > row['ema20']:
                    runner_exit = True
                    
                if runner_exit:
                    rem_qty = qty * 0.40
                    exit_price = next_close
                    points2 = (exit_price - entry_p) if side == "LONG" else (entry_p - exit_price)
                    pnl2 = points2 * rem_qty
                    fees2 = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                    pos['realized_pnl'] += (pnl2 - fees2)
                    trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': next_dt,
                        'side': side,
                        'entry_price': entry_p,
                        'exit_price': exit_price,
                        'points': round(points2, 1),
                        'net_pnl': round(pos['realized_pnl'], 2),
                        'result': 'WIN',
                        'bars': pos['bars_held']
                    })
                    in_pos = False
                    pos = {}
                    continue

        if not in_pos:
            is_bull = row['close'] > row['ema200']
            is_bear = row['close'] < row['ema200']
            
            # High-probability Connors RSI + IBS dip
            # Long: Bullish trend + RSI2 < 10 + IBS < 0.20 + Reversal bar (Close > Open)
            long_sig = is_bull and (row['rsi2'] < 10) and (row['ibs'] < 0.20) and (row['close'] > row['open'])
            short_sig = is_bear and (row['rsi2'] > 90) and (row['ibs'] > 0.80) and (row['close'] < row['open'])
            
            if long_sig:
                entry_p = next_open
                sl_dist = sl_mult * row['atr']
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
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }
            elif short_sig:
                entry_p = next_open
                sl_dist = sl_mult * row['atr']
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
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
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
    max_mdd = mdf['Max Drawdown ($)'].max()
    red_months = len(mdf[mdf['Status'] == 'RED'])
    print(f"Risk:${risk_usd} SL:{sl_mult} TP1:{tp1_r}R | Trades:{total_trades} | WinRate:{win_rate:.1f}% | NetPnL:${total_net:.2f} | MaxMDD:${max_mdd:.2f} | RedMonths:{red_months}/{len(mdf)}")
    return tdf, mdf

for r in [50.0, 75.0, 100.0]:
    for sl_m in [2.2, 2.8, 3.2]:
        for tp1 in [0.8, 1.0, 1.2]:
            test_high_win_rate_engine(risk_usd=r, sl_mult=sl_m, tp1_r=tp1)
