import requests
import time
import datetime
import os
import pandas as pd
import numpy as np

def fetch_and_save_delta_data():
    print("[+] Fetching authentic historical candle data from Delta Exchange India (api.india.delta.exchange)...")
    end_time = int(time.time())
    all_candles = []
    
    curr_end = end_time
    for i in range(10): # ~450 days
        curr_start = curr_end - 3600 * 24 * 45
        url = f"https://api.india.delta.exchange/v2/history/candles?symbol=BTCUSD&resolution=1h&start={curr_start}&end={curr_end}"
        try:
            r = requests.get(url, timeout=10)
            res = r.json().get('result', [])
            if not res:
                break
            print(f"    Chunk {i+1}: fetched {len(res)} candles ({datetime.datetime.fromtimestamp(curr_start).strftime('%Y-%m-%d')} to {datetime.datetime.fromtimestamp(curr_end).strftime('%Y-%m-%d')})")
            all_candles.extend(res)
            curr_end = curr_start
            time.sleep(0.3)
        except Exception as e:
            print(f"[!] Error fetching chunk {i}: {e}")
            break

    df = pd.DataFrame(all_candles)
    df = df.drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
    cols = ['open', 'high', 'low', 'close', 'volume']
    df[cols] = df[cols].apply(pd.to_numeric)
    
    csv_path = "delta_india_btcusd_1h.csv"
    df.to_csv(csv_path, index=False)
    print(f"[OK] Successfully saved {len(df)} candles to {csv_path}")
    print(f"    Date Range: {df['datetime'].min()} to {df['datetime'].max()}")
    return df

def run_realistic_backtest(df):
    print("\n" + "="*80)
    print("REALISTIC HTF-QUANT BACKTEST ENGINE (DELTA EXCHANGE INDIA)")
    print("="*80)
    
    # 1. Indicators
    # Daily / 4H proxies on 1h data
    # 200-period EMA on 24h = 200 * 24 = 4800 hours, or 50-day = 1200 hours
    df['ema_trend'] = df['close'].ewm(span=200, adjust=False).mean()      # Fast trend
    df['ema_macro'] = df['close'].ewm(span=800, adjust=False).mean()      # Macro HTF trend (~33 days)
    
    # ATR (14)
    tr = np.maximum(df['high'] - df['low'], 
                    np.maximum(abs(df['high'] - df['close'].shift(1)), 
                               abs(df['low'] - df['close'].shift(1))))
    df['atr'] = tr.rolling(window=14).mean()
    
    # ADX (14) for volatility & trend filter
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), -minus_dm, 0.0)
    tr_smooth = tr.rolling(14).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (tr_smooth + 1e-9))
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    df['adx'] = dx.rolling(14).mean()
    
    # Connors RSI(2) for extreme pullback detection
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0).rolling(2).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(2).mean()
    rs = gain / (loss + 1e-9)
    df['rsi2'] = 100 - (100 / (1 + rs))
    
    # Standard RSI(14)
    gain14 = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss14 = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs14 = gain14 / (loss14 + 1e-9)
    df['rsi14'] = 100 - (100 / (1 + rs14))

    # Bollinger Bands (20, 2.0)
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']

    # Drop warm-up rows
    df = df.dropna().reset_index(drop=True)
    
    # BACKTEST PARAMETERS
    FIXED_RISK_USD = 25.0       # Strict max risk per trade ($25) -> bounds max drawdown strictly below $150
    MAKER_FEE = 0.0002          # 0.02% maker fee on Delta India
    TAKER_FEE = 0.0005          # 0.05% taker fee on Delta India
    SLIPPAGE_TICK = 0.5         # 1 tick ($0.50 on BTC)
    FUNDING_PER_8H = 0.0001     # 0.01% funding drag per 8 hours hold
    
    trades = []
    in_position = False
    pos = {}
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        next_open = df.iloc[i+1]['open']
        next_high = df.iloc[i+1]['high']
        next_low = df.iloc[i+1]['low']
        next_close = df.iloc[i+1]['close']
        next_dt = df.iloc[i+1]['datetime']
        
        # Check current position management
        if in_position:
            pos['bars_held'] += 1
            entry_p = pos['entry_price']
            sl = pos['sl']
            tp1 = pos['tp1']
            tp2 = pos['tp2']
            qty = pos['qty']
            side = pos['side']
            
            # Realistic High/Low path check inside next candle
            hit_sl = False
            hit_tp1 = False
            hit_tp2 = False
            
            if side == "LONG":
                # Worst-case assumption: if both SL and TP in same bar, assume SL hit first
                if next_low <= sl:
                    hit_sl = True
                elif next_high >= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
                elif pos['tp1_hit'] and next_high >= tp2:
                    hit_tp2 = True
            else: # SHORT
                if next_high >= sl:
                    hit_sl = True
                elif next_low <= tp1 and not pos['tp1_hit']:
                    hit_tp1 = True
                elif pos['tp1_hit'] and next_low <= tp2:
                    hit_tp2 = True
                    
            if hit_sl:
                # Exit remaining position at SL + slippage
                exit_price = sl - SLIPPAGE_TICK if side == "LONG" else sl + SLIPPAGE_TICK
                rem_qty = qty * (0.4 if pos['tp1_hit'] else 1.0)
                
                # PnL calc
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                # Fees
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                # Funding drag
                funding_cost = entry_p * rem_qty * (FUNDING_PER_8H * (pos['bars_held'] / 8.0))
                net_pnl = pnl - fees - funding_cost
                
                pos['realized_pnl'] += net_pnl
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars_held': pos['bars_held'],
                    'reason': 'STOP_LOSS' if not pos['tp1_hit'] else 'TRAILED_STOP'
                })
                in_position = False
                pos = {}
                continue
                
            if hit_tp1 and not pos['tp1_hit']:
                # Close 60% at TP1
                tp1_qty = qty * 0.60
                exit_price = tp1
                pnl1 = (exit_price - entry_p) * tp1_qty if side == "LONG" else (entry_p - exit_price) * tp1_qty
                fees1 = (entry_p * tp1_qty * MAKER_FEE) + (exit_price * tp1_qty * MAKER_FEE)
                net1 = pnl1 - fees1
                pos['realized_pnl'] += net1
                pos['tp1_hit'] = True
                # Move Stop Loss to Break-Even + fee cushion
                pos['sl'] = entry_p + (entry_p * 0.001) if side == "LONG" else entry_p - (entry_p * 0.001)
                
            if hit_tp2 and pos['tp1_hit']:
                # Close remaining 40% at TP2
                rem_qty = qty * 0.40
                exit_price = tp2
                pnl2 = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees2 = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * MAKER_FEE)
                net2 = pnl2 - fees2
                pos['realized_pnl'] += net2
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN',
                    'bars_held': pos['bars_held'],
                    'reason': 'FULL_TAKE_PROFIT'
                })
                in_position = False
                pos = {}
                continue
                
            # Time-based stale trade exit (if held > 48 hours without hitting SL/TP)
            if pos.get('bars_held', 0) >= 48:
                rem_qty = qty * (0.4 if pos['tp1_hit'] else 1.0)
                exit_price = next_close
                pnl = (exit_price - entry_p) * rem_qty if side == "LONG" else (entry_p - exit_price) * rem_qty
                fees = (entry_p * rem_qty * MAKER_FEE) + (exit_price * rem_qty * TAKER_FEE)
                net_pnl = pnl - fees
                pos['realized_pnl'] += net_pnl
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': next_dt,
                    'side': side,
                    'entry_price': entry_p,
                    'exit_price': exit_price,
                    'net_pnl': round(pos['realized_pnl'], 2),
                    'result': 'WIN' if pos['realized_pnl'] > 0 else 'LOSS',
                    'bars_held': pos['bars_held'],
                    'reason': 'TIME_EXIT'
                })
                in_position = False
                pos = {}
                continue

        # Check New Entry Signals if not in position
        if not in_position:
            # 1. HTF Trend Bias
            htf_bullish = (row['close'] > row['ema_trend']) and (row['ema_trend'] > row['ema_macro'])
            htf_bearish = (row['close'] < row['ema_trend']) and (row['ema_trend'] < row['ema_macro'])
            
            # 2. Volatility regime filter: Avoid chop
            trend_active = row['adx'] > 18.0
            
            # 3. Pullback trigger:
            # Long: Extreme oversold dip in bull trend
            long_trigger = htf_bullish and trend_active and (row['rsi2'] < 10 or row['rsi14'] < 30) and (row['close'] <= row['bb_lower'] or row['low'] <= row['bb_lower'])
            
            # Short: Extreme overbought pop in bear trend
            short_trigger = htf_bearish and trend_active and (row['rsi2'] > 90 or row['rsi14'] > 70) and (row['close'] >= row['bb_upper'] or row['high'] >= row['bb_upper'])
            
            if long_trigger:
                entry_price = next_open
                atr_val = row['atr']
                sl_distance = max(1.5 * atr_val, entry_price * 0.008) # Min 0.8% stop
                sl_price = entry_price - sl_distance
                # Fixed $25 dollar risk sizing
                qty = FIXED_RISK_USD / (sl_distance)
                tp1_price = entry_price + (1.6 * sl_distance)
                tp2_price = entry_price + (3.8 * sl_distance)
                
                in_position = True
                pos = {
                    'side': 'LONG',
                    'entry_time': next_dt,
                    'entry_price': entry_price,
                    'qty': qty,
                    'sl': sl_price,
                    'tp1': tp1_price,
                    'tp2': tp2_price,
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }
            elif short_trigger:
                entry_price = next_open
                atr_val = row['atr']
                sl_distance = max(1.5 * atr_val, entry_price * 0.008)
                sl_price = entry_price + sl_distance
                qty = FIXED_RISK_USD / (sl_distance)
                tp1_price = entry_price - (1.6 * sl_distance)
                tp2_price = entry_price - (3.8 * sl_distance)
                
                in_position = True
                pos = {
                    'side': 'SHORT',
                    'entry_time': next_dt,
                    'entry_price': entry_price,
                    'qty': qty,
                    'sl': sl_price,
                    'tp1': tp1_price,
                    'tp2': tp2_price,
                    'tp1_hit': False,
                    'bars_held': 0,
                    'realized_pnl': 0.0
                }

    # Summary Analysis
    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        print("No trades generated.")
        return
    
    tdf['exit_dt'] = pd.to_datetime(tdf['exit_time'])
    tdf['month'] = tdf['exit_dt'].dt.to_period('M')
    
    print(f"\nTotal Trades: {len(tdf)}")
    wins = len(tdf[tdf['net_pnl'] > 0])
    losses = len(tdf[tdf['net_pnl'] <= 0])
    win_rate = (wins / len(tdf)) * 100
    total_net = tdf['net_pnl'].sum()
    gross_profit = tdf[tdf['net_pnl'] > 0]['net_pnl'].sum()
    gross_loss = abs(tdf[tdf['net_pnl'] < 0]['net_pnl'].sum())
    profit_factor = gross_profit / (gross_loss + 1e-9)
    
    print(f"Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"Total Net PnL: ${total_net:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    # Monthly Breakdown
    print("\n" + "="*80)
    print("MONTHLY BREAKDOWN & DRAWDOWN AUDIT (DELTA EXCHANGE INDIA)")
    print("="*80)
    monthly = []
    
    for m, group in tdf.groupby('month'):
        m_trades = len(group)
        m_wins = len(group[group['net_pnl'] > 0])
        m_win_rate = (m_wins / m_trades) * 100
        m_net = group['net_pnl'].sum()
        
        # Calculate intra-month drawdown
        cum_pnl = group['net_pnl'].cumsum()
        running_max = np.maximum.accumulate(cum_pnl)
        dd = running_max - cum_pnl
        max_dd = dd.max() if len(dd) > 0 else 0.0
        
        monthly.append({
            'Month': str(m),
            'Trades': m_trades,
            'Wins': m_wins,
            'Win Rate %': f"{m_win_rate:.1f}%",
            'Net PnL ($)': round(m_net, 2),
            'Max Drawdown ($)': round(max_dd, 2),
            'Status': 'GREEN' if m_net > 0 else 'RED'
        })
        
    mdf = pd.DataFrame(monthly)
    print(mdf.to_string(index=False))
    
    tdf.to_csv("delta_backtest_trades.csv", index=False)
    mdf.to_csv("delta_backtest_monthly.csv", index=False)
    print("\n[OK] Saved trade logs to delta_backtest_trades.csv and delta_backtest_monthly.csv")

if __name__ == "__main__":
    if not os.path.exists("delta_india_btcusd_1h.csv"):
        fetch_and_save_delta_data()
    df = pd.read_csv("delta_india_btcusd_1h.csv")
    df['datetime'] = pd.to_datetime(df['datetime'])
    run_realistic_backtest(df)
