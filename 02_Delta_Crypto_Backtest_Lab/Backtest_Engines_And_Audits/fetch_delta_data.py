import requests
import time
import datetime
import os
import pandas as pd

def fetch_delta_historical_data():
    print("[+] Fetching authentic historical candle data from Delta Exchange India (api.india.delta.exchange)...")
    end_time = int(time.time())
    all_candles = []
    
    # Fetch in 45-day chunks backwards (8 chunks ~ 360 days)
    curr_end = end_time
    for i in range(9):
        curr_start = curr_end - 3600 * 24 * 45
        url = f"https://api.india.delta.exchange/v2/history/candles?symbol=BTCUSD&resolution=1h&start={curr_start}&end={curr_end}"
        try:
            r = requests.get(url, timeout=10)
            res = r.json().get('result', [])
            if not res:
                print(f"[-] No more candles returned at chunk {i}")
                break
            print(f"    Chunk {i+1}: fetched {len(res)} candles from {datetime.datetime.fromtimestamp(curr_start)} to {datetime.datetime.fromtimestamp(curr_end)}")
            all_candles.extend(res)
            curr_end = curr_start
            time.sleep(0.4)
        except Exception as e:
            print(f"[!] Error fetching chunk {i}: {e}")
            break

    df = pd.DataFrame(all_candles)
    df = df.drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    
    # Rename and cast columns
    df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
    cols = ['open', 'high', 'low', 'close', 'volume']
    df[cols] = df[cols].apply(pd.to_numeric)
    
    csv_path = "delta_india_btcusd_1h.csv"
    df.to_csv(csv_path, index=False)
    print(f"[✓] Successfully saved {len(df)} candles to {csv_path}")
    print(f"    Date Range: {df['datetime'].min()} to {df['datetime'].max()}")
    return df

if __name__ == "__main__":
    fetch_delta_historical_data()
