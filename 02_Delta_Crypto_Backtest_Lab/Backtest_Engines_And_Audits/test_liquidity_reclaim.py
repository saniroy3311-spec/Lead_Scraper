import pandas as pd
import numpy as np

# Load authentic Delta Exchange India BTCUSD 1H data
df = pd.read_csv("delta_india_btcusd_1h.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)

# 1. Higher Time Frame (HTF) Trend: 4H proxies on 1H data
# 4H 50 EMA = 200 1H bars; 4H 200 EMA = 800 1H bars
df['ema_fast'] = df['close'].ewm(span=100, adjust=False).mean()
df['ema_slow'] = df['close'].ewm(span=400, adjust=False).mean()

# ATR (14)
tr = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift(1)), 
                           abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(window=14).mean()

# ADX (14)
plus_dm = df['high'].diff()
minus_dm = df['low'].diff()
plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), -minus_dm, 0.0)
tr_smooth = tr.rolling(14).mean()
plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
df['adx'] = dx.rolling(14).mean()

# RSI (14)
delta = df['close'].diff()
gain14 = delta.where(delta > 0, 0.0).rolling(14).mean()
loss14 = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
rs14 = gain14 / (loss14 + 1e-9)
df['rsi'] = 100 - (100 / (1 + rs14))

# 20-period Donchian / Swing Channels
df['swing_low_20'] = df['low'].rolling(20).min().shift(1)
df['swing_high_20'] = df['high'].rolling(20).max().shift(1)

# Volume moving average
df['vol_ma'] = df['volume'].rolling(20).mean()

df = df.dropna().reset_index(drop=True)

# Test various confluence setups
def evaluate_strategy(risk_usd=30.0, tp1_r=1.5, tp2_r=3.5, sl_atr_mult=1.5, require_vol=True):
    MAKER_FEE = 0.0002
    TAKER_FEE = 0.0005
    SLIPPAGE = 0.5
    FUNDING_PER_8H = 0.0001
    
    trades = []
    in_pos = False
    pos = {}
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
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
                rem_qty = qty * (0.4 if pos['tp1_hit'] else 1.0)
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                funding = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 8.0))
                net = pnl - fees - funding
                pos['realized_pnl'] += net
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
                # Break-Even Stop
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                
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
                
            # Time exit after 60 hours
            if pos['bars_held'] >= 60:
                rem_qty = qty * (0.4 if pos['tp1_hit'] else 1.0)
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
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars': pos['bars_held']
                })
                in_pos = False
                pos = {}
                continue
                
        if not in_pos:
            # 1. HTF Trend Filters
            is_bull = row['close'] > row['ema_slow'] and row['ema_fast'] > row['ema_slow']
            is_bear = row['close'] < row['ema_slow'] and row['ema_fast'] < row['ema_slow']
            adx_ok = row['adx'] > 18
            
            # 2. Liquidity Sweep & Reclaim:
            # Long: Price dipped below 20-period swing low, but candle closes strongly green and reclaims back above prev high or swing low!
            swept_low = (prev_row['low'] < prev_row['swing_low_20'] or row['low'] < row['swing_low_20'])
            bull_reclaim = swept_low and (row['close'] > row['open']) and (row['close'] > prev_row['high']) and (row['rsi'] > 35)
            
            # Short: Price spiked above 20-period swing high, but candle closes strongly red below prev low!
            swept_high = (prev_row['high'] > prev_row['swing_high_20'] or row['high'] > row['swing_high_20'])
            bear_reclaim = swept_high and (row['close'] < row['open']) and (row['close'] < prev_row['low']) and (row['rsi'] < 65)
            
            vol_ok = (row['volume'] > row['vol_ma'] * 0.8) if require_vol else True
            
            if is_bull and adx_ok and bull_reclaim and vol_ok:
                entry_p = next_open
                sl_dist = max(sl_atr_mult * row['atr'], entry_p * 0.008)
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
            elif is_bear and adx_ok and bear_reclaim and vol_ok:
                entry_p = next_open
                sl_dist = max(sl_atr_mult * row['atr'], entry_p * 0.008)
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
        return 0, 0, 0, 0, 0
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    
    total_net = tdf['net_pnl'].sum()
    win_rate = (len(tdf[tdf['net_pnl'] > 0]) / len(tdf)) * 100
    
    # Check monthly drawdowns and red months
    red_months = 0
    max_m_dd = 0.0
    for m, g in tdf.groupby('month'):
        net = g['net_pnl'].sum()
        if net < 0:
            red_months += 1
        cum = g['net_pnl'].cumsum()
        running_max = np.maximum.accumulate(cum)
        dd = (running_max - cum).max()
        if dd > max_m_dd:
            max_m_dd = dd
            
    print(f"Trades: {len(tdf):2d} | WinRate: {win_rate:5.1f}% | NetPnL: ${total_net:7.2f} | MaxMDD: ${max_m_dd:5.2f} | RedMonths: {red_months}/{len(tdf['month'].unique())}")
    return tdf

evaluate_strategy(risk_usd=35.0, tp1_r=1.2, tp2_r=3.2, sl_atr_mult=1.6)
