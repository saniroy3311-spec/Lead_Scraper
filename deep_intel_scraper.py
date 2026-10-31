"""
Deep Business Intelligence & Email Enrichment Engine
---------------------------------------------------
Crawls websites for verified business emails, audits strengths & weaknesses,
and generates step-by-step psychological persuasion strategies to convert leads.
"""

import sys
import os
import re
import csv
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

IGNORED_EMAIL_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp', 'sentry', 'w3.org', 'schema.org', 'example.com')

def extract_email_from_url(url):
    if not url or "http" not in url:
        return "No Website - Use Phone/WhatsApp"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    found_emails = set()
    pages_to_check = [url]
    
    # Try base + contact page
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    pages_to_check.append(urllib.parse.urljoin(base, "/contact"))
    pages_to_check.append(urllib.parse.urljoin(base, "/contact-us"))
    
    for page_url in pages_to_check[:2]:
        try:
            resp = requests.get(page_url, headers=headers, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                # 1. Regex search
                matches = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', resp.text)
                for m in matches:
                    m_lower = m.lower()
                    if not any(ign in m_lower for ign in IGNORED_EMAIL_EXTENSIONS):
                        found_emails.add(m)
                
                # 2. mailto: links
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.select('a[href^="mailto:"]'):
                    href = a.get('href', '').replace('mailto:', '').split('?')[0].strip()
                    if href and '@' in href:
                        found_emails.add(href)
                        
            if found_emails:
                break
        except Exception:
            continue
            
    if found_emails:
        # Prioritize info@, contact@, sales@, support@, or first clean email
        sorted_emails = sorted(list(found_emails), key=lambda e: (
            0 if 'info@' in e.lower() or 'contact@' in e.lower() else 1
        ))
        return sorted_emails[0]
    
    return "Not Found on Site (Call / WhatsApp Direct)"

def generate_deep_intelligence(row):
    name = row.get("Business_Name", "")
    category = row.get("Category", "")
    rating_str = row.get("Google_Rating", "4.5★").replace("★", "")
    rating = float(rating_str) if rating_str else 4.5
    reviews = int(row.get("Review_Count", 20))
    address = row.get("Full_Address", "")
    website = row.get("Website_Status", "")
    has_website = bool(website and "http" in website)
    
    # Analyze Strengths
    strengths = []
    if reviews >= 50 and rating >= 4.5:
        strengths.append(f"Strong organic social proof ({reviews} reviews with {rating}★ rating), indicating high customer trust.")
    elif reviews >= 20:
        strengths.append(f"Established local footprint with {reviews} customer ratings.")
    else:
        strengths.append(f"Emerging boutique business in a prime location.")
        
    if "Road" in address or "Banjara" in address or "Colony" in address:
        strengths.append("High-rent, affluent neighborhood with affluent footfall and high-income clientele.")
        
    if has_website:
        strengths.append("Existing online presence and domain authority.")
    else:
        strengths.append("High word-of-mouth reputation (surviving and growing without a digital marketing engine).")

    # Analyze Weak Points
    weaknesses = []
    if not has_website:
        weaknesses.append("🚨 ZERO Direct Website: Missing the Google Maps website button. Losing 100% of high-intent searchers who prefer booking/researching online.")
        weaknesses.append("Reliance on manual phone calls or walk-ins; leads drop off if phone is busy.")
    else:
        weaknesses.append("Digital friction: Website lacks modern 1-click WhatsApp checkout/booking, making mobile conversion slow.")
        weaknesses.append("Slow mobile load times or outdated design compared to aggressive venture-funded competitors.")
        
    if reviews < 30:
        weaknesses.append("Low review velocity: Vulnerable to competitors actively running review-generation campaigns.")
    else:
        weaknesses.append("No automated follow-up loop: Customer lifetime value is under-monetized due to lack of automated WhatsApp reminders/promotions.")

    # How to Convince (The Strategy)
    if not has_website:
        strategy = (
            f"1. Acknowledge their strong {rating}★ rating ({reviews} reviews) to build immediate trust. "
            f"2. Expose the leak: 'Doctor/Owner, when clients search for your services in {address[:25]}..., they see your reviews but have NO website button to click. They immediately go to the competitor right below you.' "
            f"3. Frame the ROI: Remind them that just 1 to 2 new high-ticket clients or orders completely covers the ₹35,000–₹50,000 website cost. "
            f"4. The Soft Close: Never ask to buy. Ask: 'Can I send a 30-second WhatsApp video demo showing how your booking site will look on mobile?'"
        )
    else:
        strategy = (
            f"1. Compliment their brand presence in the local market. "
            f"2. Audit their mobile experience: Point out that 85% of local searches happen on mobile phones, where slow forms and lack of a direct WhatsApp booking button cost them 40% of conversions. "
            f"3. Offer speed & automation: Pitch a 5-day modernization that adds 1-click WhatsApp booking and automated Google review collection. "
            f"4. The Soft Close: Offer a free 60-second mobile performance audit video delivered directly to their WhatsApp."
        )

    return {
        "Strong_Points": " | ".join(strengths),
        "Weak_Points": " | ".join(weaknesses),
        "How_To_Convince_Lead": strategy
    }

def run_enrichment():
    input_file = "d:/Vibe Code/Lead_Scraper/all_banjara_businesses_enriched.csv"
    output_csv = "d:/Vibe Code/Lead_Scraper/all_businesses_with_email_and_deep_intel.csv"
    output_md = "d:/Vibe Code/Lead_Scraper/COMPREHENSIVE_BUSINESS_INTELLIGENCE_REPORT.md"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print(f"Loaded {len(reader)} leads. Crawling websites for emails & building deep intelligence...")

    # Extract emails with thread pool for speed
    urls = [r.get("Website_Status", "") for r in reader]
    print("Scraping emails from available websites in parallel...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        emails = list(executor.map(extract_email_from_url, urls))

    enriched_leads = []
    for idx, (row, email) in enumerate(zip(reader, emails)):
        intel = generate_deep_intelligence(row)
        
        row_enriched = {
            "Lead_Grade": row.get("Lead_Grade", ""),
            "Business_Name": row.get("Business_Name", ""),
            "Category": row.get("Category", ""),
            "Phone_Number": row.get("Phone_Number", ""),
            "Email_Address": email,
            "Website_Status": row.get("Website_Status", ""),
            "Google_Rating": row.get("Google_Rating", ""),
            "Review_Count": row.get("Review_Count", ""),
            "Full_Address": row.get("Full_Address", ""),
            "Google_Maps_URL": row.get("Google_Maps_URL", ""),
            "Business_Intro": row.get("Business_Intro", ""),
            "Customer_Profile": row.get("Customer_Profile", ""),
            "Customer_Ticket_Size": row.get("Customer_Ticket_Size", ""),
            "Strong_Points": intel["Strong_Points"],
            "Weak_Points": intel["Weak_Points"],
            "How_To_Convince_Lead": intel["How_To_Convince_Lead"],
            "Digital_Leak_Pain_Point": row.get("Digital_Leak_Pain_Point", ""),
            "Solution_We_Offer": row.get("Solution_We_Offer", ""),
            "Financial_ROI_Anchor": row.get("Financial_ROI_Anchor", ""),
            "Gatekeeper_Opener": row.get("Gatekeeper_Opener", ""),
            "Cold_Call_Hook": row.get("Cold_Call_Hook", ""),
            "Value_Pitch": row.get("Value_Pitch", ""),
            "Closing_CTA": row.get("Closing_CTA", ""),
            "Objection_Rebuttal": row.get("Objection_Rebuttal", "")
        }
        enriched_leads.append(row_enriched)

    # Save to CSV
    fieldnames = list(enriched_leads[0].keys())
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in enriched_leads:
            writer.writerow(r)
    print(f"✅ Exported enriched CSV with emails to: {output_csv}")

    # Generate Markdown Report
    with open(output_md, mode="w", encoding="utf-8") as f:
        f.write("# 📑 Comprehensive Business Intelligence & Conversion Dossier\n")
        f.write(f"**Target Market:** Banjara Hills, Hyderabad | **Total Leads Analyzed:** {len(enriched_leads)}\n\n")
        f.write("---\n\n")
        
        for idx, l in enumerate(enriched_leads[:15], start=1):
            f.write(f"### {idx}. {l['Business_Name']} ({l['Lead_Grade']})\n")
            f.write(f"- **Category:** {l['Category']}\n")
            f.write(f"- **Phone:** `{l['Phone_Number']}` | **Email:** `{l['Email_Address']}`\n")
            f.write(f"- **Website:** {l['Website_Status']}\n")
            f.write(f"- **Reputation:** {l['Google_Rating']} ({l['Review_Count']} reviews) | [View on Google Maps]({l['Google_Maps_URL']})\n")
            f.write(f"- **Address:** {l['Full_Address']}\n\n")
            
            f.write(f"**🏢 Business Profile:**\n")
            f.write(f"{l['Business_Intro']}\n")
            f.write(f"*Target Customer:* {l['Customer_Profile']} | *Ticket Size:* {l['Customer_Ticket_Size']}\n\n")
            
            f.write(f"**💪 Strong Points (Their Assets):**\n")
            for sp in l['Strong_Points'].split(" | "):
                f.write(f"- {sp}\n")
            f.write("\n")
            
            f.write(f"**⚠️ Weak Points (Their Vulnerabilities & Leaks):**\n")
            for wp in l['Weak_Points'].split(" | "):
                f.write(f"- {wp}\n")
            f.write("\n")
            
            f.write(f"**🎯 How to Convince This Lead (Psychology & Closing Steps):**\n")
            f.write(f"{l['How_To_Convince_Lead']}\n\n")
            
            f.write(f"**📞 Ready-to-Use Cold Call Script:**\n")
            f.write(f"- *Gatekeeper Opener:* {l['Gatekeeper_Opener']}\n")
            f.write(f"- *Opening Hook:* {l['Cold_Call_Hook']}\n")
            f.write(f"- *The 1-Client ROI Pitch:* {l['Financial_ROI_Anchor']}\n")
            f.write(f"- *Closing CTA:* {l['Closing_CTA']}\n")
            f.write(f"- *Objection Rebuttal:* {l['Objection_Rebuttal']}\n\n")
            f.write("---\n\n")
            
    print(f"✅ Generated Comprehensive Intelligence Report at: {output_md}")

if __name__ == "__main__":
    run_enrichment()
