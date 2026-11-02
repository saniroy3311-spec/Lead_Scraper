import os
import sys
import re
import time
import json
import subprocess
import pandas as pd
import datetime
import instaloader
import whisper

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = "Trading_Intelligence_Database"
os.makedirs(ROOT_DIR, exist_ok=True)

PROFILES = [
    "quantifiedstrategies",
    "tradesbyanand",
    "finastictrading",
    "official.moneymatters",
    "quantfinance.ai",
    "trade_and_gain07",
    "smartmoneybreakouts",
    "investalogy.in",
    "quantvue.io",
    "quant_grad",
    "tseng_trades.10",
    "quant_labde",
    "order_flow_trade",
    "quantchics",
    "skydweller.trades",
    "mirkovicdev",
    "sixlots",
    "tradezella",
    "moneytradeedge",
    "sumedhhkumar.ai",
    "nagarajan3437",
    "cache.capital",
    "niccofx",
    "fxupdates_",
    "optionstradingguru86",
    "thejokotrader",
    "tradinglikevicky"
]

def clean_pure_trading_content(text):
    if not isinstance(text, str):
        return ""
    # Strip all links (http, https, www, t.me, bit.ly, etc.)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    # Strip hashtags
    text = re.sub(r'#\w+', '', text)
    # Strip mentions
    text = re.sub(r'@\w+', '', text)
    
    lines = text.split("\n")
    cleaned = []
    
    skip_phrases = [
        "link in bio", "substack", "about quantified strategies",
        "save this carousel", "let us know in the comments", "share this",
        "free substack", "our newsletter has", "our trading books have sold",
        "prefer deeper research", "follow for more", "turn on notifications",
        "check the carousel", "swipe left", "save this post", "👇", "👉",
        "historical tendency, not a forecast", "disclaimer", "join our telegram",
        "join our community", "dm for details", "whatsapp", "link in story",
        "comment below", "tag a friend", "save for later", "follow @"
    ]
    
    for l in lines:
        line_str = l.strip()
        if not line_str or line_str in [".", "..", "...", "....", "-", "--", "---"]:
            continue
        l_lower = line_str.lower()
        if any(p in l_lower for p in skip_phrases):
            continue
        # Also clean out trailing calls to action
        if l_lower.startswith("follow ") or l_lower.startswith("dm ") or l_lower.startswith("comment "):
            continue
        cleaned.append(line_str)
        
    return "\n\n".join(cleaned)

def extract_trading_metadata(text, spoken=""):
    combined = text + " " + spoken
    
    # Asset detection
    assets = []
    for a in ["Nifty", "Bank Nifty", "Sensex", "SPY", "QQQ", "GLD", "Gold", "XAUUSD", "NQ", "Nasdaq", "Bitcoin", "BTC", "Ethereum", "ETH", "Crypto", "Forex", "EURUSD", "GBPUSD", "USDJPY", "JETS", "VIX", "Crude Oil", "WTI", "Options", "Futures", "Stocks"]:
        if re.search(r'\b' + re.escape(a) + r'\b', combined, re.IGNORECASE):
            assets.append(a.upper() if len(a) <= 4 else a.title())
    asset_str = ", ".join(list(dict.fromkeys(assets))) if assets else "Equities & Financial Markets"
    
    # Category / Trading Type detection
    types = []
    c_low = combined.lower()
    if any(k in c_low for k in ["scalp", "scalping"]):
        types.append("Scalping")
    if any(k in c_low for k in ["day trade", "day trading", "intraday"]):
        types.append("Day Trading / Intraday")
    if any(k in c_low for k in ["swing", "swing trade", "overnight"]):
        types.append("Swing Trading")
    if any(k in c_low for k in ["option", "call", "put", "straddle", "strangle", "expiry", "oi"]):
        types.append("Options Trading")
    if any(k in c_low for k in ["order flow", "footprint", "market profile", "volume profile", "poc", "delta"]):
        types.append("Order Flow & Volume Profile")
    if any(k in c_low for k in ["smc", "smart money", "liquidity", "fair value gap", "fvg", "order block", "bos", "choch"]):
        types.append("Smart Money Concepts (SMC)")
    if any(k in c_low for k in ["quant", "backtest", "algo", "python", "code", "rule-based", "statistical", "sharpe", "win rate"]):
        types.append("Quantitative & Algorithmic")
    if any(k in c_low for k in ["psychology", "discipline", "mindset", "fear", "greed", "fomo", "patience", "emotion"]):
        types.append("Trading Psychology")
    if any(k in c_low for k in ["risk", "stop loss", "position size", "drawdown", "r:r", "risk reward", "capital protection"]):
        types.append("Risk Management")
        
    type_str = ", ".join(types) if types else "Price Action & Strategy"
    
    # Indicators
    indicators = []
    for ind in ["RSI(2)", "RSI", "EMA", "SMA", "VWAP", "Williams %R", "ADX", "IBS", "MACD", "Bollinger Bands", "CPR", "Supertrend", "Moving Average", "Order Block", "FVG", "Stochastic", "Fibonacci", "ATR"]:
        if re.search(r'\b' + re.escape(ind) + r'\b', combined, re.IGNORECASE):
            indicators.append(ind)
    ind_str = ", ".join(list(dict.fromkeys(indicators))) if indicators else "Price Action & Market Structure"
    
    # First line title
    first_line = text.split("\n")[0] if text else "Trading Concept & Setup"
    title = re.sub(r'^[^\w\s]+', '', first_line).strip()[:65]
    if not title:
        title = "Trading Analysis & Technical Setup"
        
    return {
        "title": title,
        "asset": asset_str,
        "type": type_str,
        "indicators": ind_str
    }

def process_creator(username, L, whisper_model, posts_per_profile=12):
    creator_dir = os.path.join(ROOT_DIR, username)
    os.makedirs(creator_dir, exist_ok=True)
    
    md_filepath = os.path.join(creator_dir, f"{username}_Trading_Intelligence.md")
    csv_filepath = os.path.join(creator_dir, f"{username}_raw_posts.csv")
    
    # If already scraped and dossier exists with valid content, load it and return
    if os.path.exists(md_filepath) and os.path.getsize(md_filepath) > 1000:
        print(f"Skipping @{username}: Already processed ({os.path.getsize(md_filepath):,} bytes)")
        with open(md_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        setups_cnt = len(re.findall(r'### Setup #\d+:', content))
        return {
            "username": username,
            "status": "Success (Cached)",
            "posts_scraped": setups_cnt if setups_cnt > 0 else 12,
            "folder": creator_dir
        }
        
    print(f"\n{'='*55}")
    print(f"PROCESSING PROFILE: @{username}")
    print(f"{'='*55}")
    
    profile = None
    for attempt in range(1, 4):
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            break
        except Exception as e:
            print(f"  [Attempt {attempt}/3] Failed to access profile @{username}: {e}")
            time.sleep(5.0 * attempt)
            
    if profile is None:
        return {
            "username": username,
            "status": "Error: Connection Failed",
            "posts_scraped": 0,
            "folder": creator_dir
        }
        
    full_name = getattr(profile, 'full_name', username) or username
    bio = getattr(profile, 'biography', '') or ''
    clean_bio = clean_pure_trading_content(bio)
    
    print(f"Name: {full_name} | Bio: {clean_bio[:60]}...")
    
    posts_data = []
    count = 0
    
    for post in profile.get_posts():
        count += 1
        try:
            shortcode = post.shortcode
            date_utc = post.date_utc.strftime("%Y-%m-%d %H:%M:%S") if post.date_utc else ""
            is_video = bool(post.is_video)
            media_type = "Video / Reel" if is_video else ("Carousel (Sidecar)" if post.typename == "GraphSidecar" else "Single Photo")
            caption = post.caption or ""
            video_url = post.video_url if is_video else ""
            
            # Spoken video transcription (fast 45s audio window)
            spoken_text = ""
            if is_video and isinstance(video_url, str) and video_url.startswith("http") and whisper_model:
                temp_audio = os.path.join(creator_dir, f"temp_{shortcode}.mp3")
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-t", "45", "-i", video_url, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "48k", temp_audio],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=18
                    )
                    if os.path.exists(temp_audio):
                        res = whisper_model.transcribe(temp_audio)
                        spoken_text = res["text"].strip()
                        os.remove(temp_audio)
                        if len(spoken_text) > 15:
                            print(f"  [Post {count:02d}] Spoken Audio Extracted: {spoken_text[:65]}...")
                except Exception:
                    if os.path.exists(temp_audio):
                        try:
                            os.remove(temp_audio)
                        except:
                            pass
                        
            cleaned_caption = clean_pure_trading_content(caption)
            spec = extract_trading_metadata(cleaned_caption, spoken_text)
            
            item = {
                "post_no": count,
                "shortcode": shortcode,
                "date_utc": date_utc,
                "media_type": media_type,
                "is_video": is_video,
                "title": spec["title"],
                "asset": spec["asset"],
                "trading_type": spec["type"],
                "indicators": spec["indicators"],
                "cleaned_caption": cleaned_caption,
                "spoken_transcript": spoken_text,
                "raw_caption": caption
            }
            posts_data.append(item)
            print(f"  [{count:02d}] {item['date_utc'][:10]} | {item['trading_type'][:20]:<20} | {item['title'][:40]}...")
            
            if count >= posts_per_profile:
                break
                
            time.sleep(2.0) # Polite rate-limiting
            
        except Exception as post_err:
            print(f"  Warning on post {count}: {post_err}")
            time.sleep(2.5)
            
    # Write CSV
    if posts_data:
        raw_df = pd.DataFrame(posts_data)
        raw_df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
        
        # Write clean Markdown Playbook
        md = []
        md.append(f"# Trading Intelligence Playbook: @{username}")
        md.append("")
        md.append(f"> **Creator:** {full_name} (`@{username}`)  ")
        md.append(f"> **Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        md.append(f"> **Trading Concepts & Setups Documented:** {len(posts_data)}  ")
        md.append(f"> **Creator Profile Summary:** {clean_bio}  ")
        md.append("")
        md.append("---")
        md.append("")
        
        md.append("## Table of Trading Setups & Insights")
        md.append("")
        md.append("| No. | Concept / Setup Title | Target Asset | Strategy / Category | Indicator(s) | Spoken Audio Insight |")
        md.append("| :---: | :--- | :---: | :--- | :--- | :---: |")
        
        for p in posts_data:
            has_voice = "Yes" if len(p["spoken_transcript"]) > 15 else "None"
            md.append(f"| **#{p['post_no']:02d}** | {p['title']} | `{p['asset']}` | {p['trading_type']} | {p['indicators']} | {has_voice} |")
            
        md.append("")
        md.append("---")
        md.append("")
        md.append("## Detailed Trading Intelligence Dossier")
        md.append("")
        
        for p in posts_data:
            md.append(f"### Setup #{p['post_no']:02d}: {p['title']}")
            md.append("")
            md.append(f"- **Target Asset / Market:** `{p['asset']}`")
            md.append(f"- **Trading Domain:** `{p['trading_type']}`")
            md.append(f"- **Key Indicators & Tools:** `{p['indicators']}`")
            md.append(f"- **Format:** `{p['media_type']}`")
            md.append("")
            
            if len(p["spoken_transcript"]) > 15:
                md.append("#### Spoken Video Voiceover Insight:")
                md.append(f"> *\"{p['spoken_transcript']}\"*")
                md.append("")
                
            md.append("#### Written Technical Rules & Analysis:")
            md.append("")
            for para in p["cleaned_caption"].split("\n\n"):
                if para.strip():
                    md.append(f"> {para.strip()}")
                    md.append(">")
            if md and md[-1] == ">":
                md.pop()
                
            md.append("")
            md.append("---")
            md.append("")
            
        with open(md_filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
            
        print(f"SUCCESS: Saved @{username} dossier to {md_filepath} ({len(posts_data)} setups)!")
        
    return {
        "username": username,
        "status": "Success",
        "posts_scraped": len(posts_data),
        "folder": creator_dir
    }

def update_master_index():
    index_md = []
    index_md.append("# Master Trading Intelligence Database Index")
    index_md.append("")
    index_md.append(f"> **Database Root:** `{ROOT_DIR}/`  ")
    index_md.append(f"> **Last Updated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    index_md.append(f"> **Total Creators Targeted:** {len(PROFILES)}  ")
    
    rows = []
    completed_count = 0
    total_setups = 0
    
    for idx, uname in enumerate(PROFILES, 1):
        folder_rel = f"{ROOT_DIR}/{uname}"
        md_full = os.path.join(ROOT_DIR, uname, f"{uname}_Trading_Intelligence.md")
        
        if os.path.exists(md_full) and os.path.getsize(md_full) > 500:
            try:
                with open(md_full, "r", encoding="utf-8") as f:
                    cnt = len(re.findall(r'### Setup #\d+:', f.read()))
            except:
                cnt = 12
            status = "Completed"
            cnt_str = f"**{cnt} Setups**"
            completed_count += 1
            total_setups += cnt
        else:
            status = "In Queue / Pending"
            cnt_str = "0 Setups"
            
        rows.append(f"| {idx:02d} | `@{uname}` | {status} | {cnt_str} | `{folder_rel}/` | `{uname}_Trading_Intelligence.md` |")
        
    index_md.append(f"> **Total Profiles Fully Processed:** {completed_count} / {len(PROFILES)}  ")
    index_md.append(f"> **Total Trading Strategies & Setups Extracted:** {total_setups}  ")
    index_md.append("")
    index_md.append("---")
    index_md.append("")
    index_md.append("## Creator Directory & Organized Folders")
    index_md.append("")
    index_md.append("| # | Creator Handle | Status | Total Setups Documented | Folder Location | Dossier File |")
    index_md.append("| :---: | :--- | :---: | :---: | :--- | :--- |")
    index_md.extend(rows)
    
    index_path = os.path.join(ROOT_DIR, "MASTER_TRADING_INTELLIGENCE_INDEX.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_md))
    print(f"Master Index updated ({completed_count}/{len(PROFILES)} done, {total_setups} setups) at {index_path}")

def main():
    print(f"==================================================")
    print(f"AUTONOMOUS TRADING INTELLIGENCE PIPELINE")
    print(f"Total Unique Targets: {len(PROFILES)}")
    print(f"Storage Directory: {os.path.abspath(ROOT_DIR)}")
    print(f"==================================================")
    
    # Refresh index first
    update_master_index()
    
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )
    
    print("Loading Whisper model for speech decoding...")
    whisper_model = whisper.load_model("tiny")
    
    for idx, u in enumerate(PROFILES, 1):
        print(f"\n>>> [{idx}/{len(PROFILES)}] Target: @{u}")
        process_creator(u, L, whisper_model, posts_per_profile=12)
        update_master_index()
        time.sleep(3.0)
        
    print("\nALL CREATORS PROCESSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
