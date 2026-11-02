import requests
import time
import datetime
import os
import pandas as pd
import numpy as np

def fetch_delta_15m_data(days=120):
    print(f"[+] Fetching {days} days of 15m candles from Delta Exchange India...")
    end_time = int(time.time())
    all_candles = []
    
    # Delta allows up to 2880 candles per call (30 days of 15m)
    curr_end = end_time
    chunks = int(days / 25)
    for i in range(chunks):
        curr_start = curr_end - (3600 * 24 * 25)
        url = f"https://api.india.delta.exchange/v2/history/candles?symbol=BTCUSD&resolution=15m&start={curr_start}&end={curr_end}"
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
            print(f"[!] Error: {e}")
            break
            
    df = pd.DataFrame(all_candles).drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
    cols = ['open', 'high', 'low', 'close', 'volume']
    df[cols] = df[cols].apply(pd.to_numeric)
    df.to_csv("delta_india_btcusd_15m.csv", index=False)
    print(f"[OK] Saved {len(df)} 15m candles to delta_india_btcusd_15m.csv (Range: {df['datetime'].min()} to {df['datetime'].max()})")
    return df

if __name__ == "__main__":
    fetch_delta_15m_data()
