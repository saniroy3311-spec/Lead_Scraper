import urllib.request
import re

url = "https://docs.google.com/spreadsheets/d/1KSfQfw92yw4BHufDSvH9lB0ZGV2N77NZbyXLuQiNKeA/edit?usp=sharing"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        title_m = re.search(r'<title>(.*?)</title>', html)
        print("Page Title:", title_m.group(1) if title_m else "None")
        
        # Check for sheet tabs
        gids = re.findall(r'gid=(\d+)', html)
        print("GIDs found:", set(gids))
        
        # Check sheet name
        names = re.findall(r'\[\d+,\s*\"([^\"]+)\",\s*\"gid\",\s*(\d+)\]', html)
        print("Sheet metadata:", names)
except Exception as e:
    print("Error:", e)
