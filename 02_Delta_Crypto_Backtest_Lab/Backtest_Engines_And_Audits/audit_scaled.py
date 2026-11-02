import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

df_idx = df.set_index('datetime')
df_4h = df_idx.resample('4h').agg({
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

df_4h = df_4h.dropna().reset_index(drop=True)

def audit_high_win_rate(fixed_risk=60.0):
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
                rem_qty = qty * (0.35 if pos['tp1_hit'] else 1.0)
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
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                # 65% taken off at TP1
                tp1_qty = qty * 0.65
                exit_price = tp1
                pnl = (exit_price - entry_p) * tp1_qty if side == "LONG" else (entry_p - exit_price) * tp1_qty
                fees = (entry_p * tp1_qty * MAKER_FEE) + (exit_price * tp1_qty * MAKER_FEE)
                pos['realized_pnl'] += (pnl - fees)
                pos['tp1_hit'] = True
                # Move Stop to Breakeven (+0.1% buffer)
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                continue
                
            # Exit runner on momentum recovery (close > 5 EMA)
            if pos['tp1_hit'] and ((side == "LONG" and next_close > row['ema5']) or (side == "SHORT" and next_close < row['ema5'])):
                rem_qty = qty * 0.35
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
            is_bull = row['close'] > row['ema200']
            is_bear = row['close'] < row['ema200']
            
            long_sig = is_bull and (row['ibs'] < 0.25) and (row['rsi2'] < 10)
            short_sig = is_bear and (row['ibs'] > 0.75) and (row['rsi2'] > 90)
            
            if long_sig:
                entry_p = next_open
                sl_dist = 1.5 * row['atr']
                sl_p = entry_p - sl_dist
                qty = fixed_risk / sl_dist
                in_pos = True
                pos = {
                    'side': 'LONG',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp1': entry_p + (0.9 * sl_dist),
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }
            elif short_sig:
                entry_p = next_open
                sl_dist = 1.5 * row['atr']
                sl_p = entry_p + sl_dist
                qty = fixed_risk / sl_dist
                in_pos = True
                pos = {
                    'side': 'SHORT',
                    'entry_time': next_dt,
                    'entry_price': entry_p,
                    'qty': qty,
                    'sl': sl_p,
                    'tp1': entry_p - (0.9 * sl_dist),
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }

    tdf = pd.DataFrame(trades)
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
    print("="*80)
    print("AUDITED RESULTS: SCALED PROFIT + HIGH WIN RATE (DELTA EXCHANGE INDIA)")
    print("="*80)
    print(mdf.to_string(index=False))
    print("="*80)
    print(f"Total Trades:       {total_trades}")
    print(f"Overall Win Rate:   {win_rate:.1f}%")
    print(f"Total Net PnL:      +${total_net:.2f}")
    print(f"Max Month Drawdown: ${max_mdd:.2f}")
    print("="*80)

audit_high_win_rate(60.0)
