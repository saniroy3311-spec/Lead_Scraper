import os
import sys
import time
import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import instaloader

sys.stdout.reconfigure(encoding='utf-8')

TARGET_USERNAME = "quantifiedstrategies"
EXCEL_FILENAME = f"Instagram_Post_Scraper_{TARGET_USERNAME}.xlsx"
CSV_FILENAME = f"Instagram_Post_Scraper_{TARGET_USERNAME}.csv"

# Pre-extracted verified profile info (from browser dom to avoid web_profile_info 429s)
PROFILE_DATA = {
    "username": "quantifiedstrategies",
    "full_name": "Quantified Strategies",
    "biography": "Helping traders scale | Backtested, rule-based strategies | Futures, Stocks & ETFs | Ex Prop Trader 👇 Free Substack",
    "followers": "5,274",
    "following": "92",
    "total_posts_catalog": "1,814",
    "external_url": "https://quantifiedstrategies.substack.com/",
    "profile_url": "https://www.instagram.com/quantifiedstrategies/"
}

def format_excel(filepath, profile_data, posts_df):
    """Generates a professional multi-sheet Excel dossier."""
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Sheet 1: All Posts Details
        posts_df.to_excel(writer, sheet_name="All Posts Details", index=False)
        
        # Sheet 2: Creator Dossier & Metrics
        summary_rows = [
            {"Metric": "Creator Username", "Value": profile_data.get("username", TARGET_USERNAME)},
            {"Metric": "Creator Full Name", "Value": profile_data.get("full_name", "")},
            {"Metric": "Bio Description", "Value": profile_data.get("biography", "")},
            {"Metric": "Profile URL", "Value": profile_data.get("profile_url", "")},
            {"Metric": "Followers Count", "Value": profile_data.get("followers", "5,274")},
            {"Metric": "Following Count", "Value": profile_data.get("following", "92")},
            {"Metric": "Lifetime Total Posts Catalog", "Value": profile_data.get("total_posts_catalog", "1,814")},
            {"Metric": "External Link", "Value": profile_data.get("external_url", "")},
            {"Metric": "Total Posts Scraped in Run", "Value": len(posts_df)},
            {"Metric": "Total Likes on Scraped Posts", "Value": int(posts_df["Likes Count"].sum()) if not posts_df.empty else 0},
            {"Metric": "Total Comments on Scraped Posts", "Value": int(posts_df["Comments Count"].sum()) if not posts_df.empty else 0},
            {"Metric": "Average Likes per Post", "Value": round(posts_df["Likes Count"].mean(), 2) if not posts_df.empty else 0},
            {"Metric": "Average Comments per Post", "Value": round(posts_df["Comments Count"].mean(), 2) if not posts_df.empty else 0},
            {"Metric": "Video / Reel Count", "Value": int((posts_df["Is Video"] == True).sum()) if not posts_df.empty else 0},
            {"Metric": "Carousel / Sidecar Count", "Value": int((posts_df["Media Type"] == "Carousel (Sidecar)").sum()) if not posts_df.empty else 0},
            {"Metric": "Single Photo Count", "Value": int((posts_df["Media Type"] == "Single Photo").sum()) if not posts_df.empty else 0},
            {"Metric": "Scraped At (Local Timestamp)", "Value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        ]
        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_excel(writer, sheet_name="Creator Dossier & Stats", index=False)
        
    wb = openpyxl.load_workbook(filepath)
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    cell_font = Font(name="Segoe UI", size=10)
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    # Format Post Details sheet
    ws_posts = wb["All Posts Details"]
    ws_posts.views.sheetView[0].showGridLines = True
    for col_idx, col in enumerate(ws_posts.iter_cols(min_row=1, max_row=ws_posts.max_row), start=1):
        col_letter = get_column_letter(col_idx)
        header_cell = col[0]
        header_cell.fill = header_fill
        header_cell.font = header_font
        header_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        max_len = len(str(header_cell.value or ""))
        for cell in col[1:]:
            cell.font = cell_font
            cell.border = thin_border
            val_str = str(cell.value or "")
            if len(val_str) > max_len and len(val_str) < 50:
                max_len = len(val_str)
        ws_posts.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)
        
    # Format Summary Sheet
    ws_summary = wb["Creator Dossier & Stats"]
    ws_summary.views.sheetView[0].showGridLines = True
    for col_idx, col in enumerate(ws_summary.iter_cols(min_row=1, max_row=ws_summary.max_row), start=1):
        col_letter = get_column_letter(col_idx)
        header_cell = col[0]
        header_cell.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        header_cell.font = header_font
        for cell in col[1:]:
            cell.font = cell_font
            cell.border = thin_border
        ws_summary.column_dimensions[col_letter].width = 35 if col_idx == 1 else 60
        
    wb.save(filepath)

def save_data(profile_info, records):
    if not records:
        return
    df = pd.DataFrame(records)
    # Save CSV
    df.to_csv(CSV_FILENAME, index=False, encoding='utf-8-sig')
    # Save Excel
    format_excel(EXCEL_FILENAME, profile_info, df)

def main():
    print(f"==================================================")
    print(f"INSTAGRAM POST & PROFILE SCRAPER")
    print(f"Target: @{TARGET_USERNAME}")
    print(f"==================================================")
    
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )
    
    print("[1/3] Loading profile stream...")
    # Using profile without triggering lazy web_profile_info
    profile = instaloader.Profile.from_username(L.context, TARGET_USERNAME)
    
    print(f"Creator: {PROFILE_DATA['full_name']} (@{TARGET_USERNAME})")
    print(f"Followers: {PROFILE_DATA['followers']}")
    print(f"Bio: {PROFILE_DATA['biography']}")
    
    print("\n[2/3] Extracting detailed post data...")
    records = []
    count = 0
    max_target = 60 # Set to scrape a solid high-volume dataset cleanly
    
    try:
        for post in profile.get_posts():
            count += 1
            try:
                typename = post.typename
                if post.is_video:
                    media_type = "Video / Reel"
                elif typename == "GraphSidecar":
                    media_type = "Carousel (Sidecar)"
                else:
                    media_type = "Single Photo"
                    
                hashtags_list = list(post.caption_hashtags) if post.caption_hashtags else []
                mentions_list = list(post.caption_mentions) if post.caption_mentions else []
                tagged_users_list = list(post.tagged_users) if post.tagged_users else []
                
                loc_name = ""
                loc_id = ""
                if post.location:
                    loc_name = getattr(post.location, 'name', '') or ''
                    loc_id = getattr(post.location, 'id', '') or ''
                    
                caption_text = post.caption or ""
                
                record = {
                    "Post Index": count,
                    "Shortcode": post.shortcode,
                    "Post URL": f"https://www.instagram.com/p/{post.shortcode}/",
                    "Post ID": str(post.mediaid),
                    "Publish Date (UTC)": post.date_utc.strftime("%Y-%m-%d %H:%M:%S") if post.date_utc else "",
                    "Publish Date (Local)": post.date_local.strftime("%Y-%m-%d %H:%M:%S") if post.date_local else "",
                    "Media Type": media_type,
                    "Is Video": bool(post.is_video),
                    "Likes Count": int(post.likes) if post.likes is not None else 0,
                    "Comments Count": int(post.comments) if post.comments is not None else 0,
                    "Hashtags Count": len(hashtags_list),
                    "Hashtags": ", ".join(f"#{tag}" for tag in hashtags_list),
                    "Mentions Count": len(mentions_list),
                    "Mentions": ", ".join(f"@{m}" for m in mentions_list),
                    "Tagged Users": ", ".join(tagged_users_list),
                    "Location": loc_name,
                    "Location ID": str(loc_id),
                    "Display Media URL": post.url or "",
                    "Video Media URL": post.video_url if post.is_video else "",
                    "Caption Text": caption_text,
                    "Creator Username": TARGET_USERNAME,
                    "Creator Full Name": PROFILE_DATA["full_name"]
                }
                
                records.append(record)
                
                caption_snippet = caption_text.replace("\n", " ")[:55]
                print(f"[{count:02d}] {record['Publish Date (UTC)'][:10]} | {record['Media Type']:<18} | Likes: {record['Likes Count']:<4} | Comments: {record['Comments Count']:<2} | {caption_snippet}...")
                
                # Checkpoint save every 5 posts
                if count % 5 == 0 or count == 1:
                    save_data(PROFILE_DATA, records)
                    print(f"   [Checkpoint: {count} posts saved to disk]")
                    
                if count >= max_target:
                    print(f"Reached batch target of {max_target} posts!")
                    break
                    
                time.sleep(2.5) # Safe rate limiting delay
                
            except Exception as item_err:
                print(f"Warning on post {count}: {item_err}")
                time.sleep(3)
                if "429" in str(item_err):
                    print("Hit Instagram rate limit, stopping and preserving all scraped posts...")
                    break
                    
    except KeyboardInterrupt:
        print("\nScraper stopped by user. Saving data...")
    except Exception as stream_err:
        print(f"\nStream completed/paused: {type(stream_err).__name__}: {stream_err}")
        
    print(f"\n[3/3] Finalizing output files...")
    save_data(PROFILE_DATA, records)
    print(f"SUCCESS: Saved {len(records)} detailed posts to:")
    print(f"  - {os.path.abspath(EXCEL_FILENAME)}")
    print(f"  - {os.path.abspath(CSV_FILENAME)}")

if __name__ == "__main__":
    main()
