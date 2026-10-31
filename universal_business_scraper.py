"""
Universal Google Maps Business Scraper & Cold Call Intelligence Engine
---------------------------------------------------------------------
Scrapes ALL businesses in a target location without filtering by ticket size.
Enriches every lead with:
1. Raw Lead Info (Name, Phone, Maps URL, Address, Rating, Reviews, Website)
2. Business Profile & Economics (What they do, Customer Profile, Ticket Size)
3. Digital Leak Audit (Why they are losing revenue)
4. Cold Caller Battle-Card (Gatekeeper Opener, Hook, Value Pitch, ROI Equation, CTA, Objection Rebuttal)
"""

import sys
import os
import re
import time
import json
import csv
import urllib.parse

# Set stdout/stderr to UTF-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from playwright.sync_api import sync_playwright

# Comprehensive Multi-Industry Intelligence Knowledge Base
INDUSTRY_KNOWLEDGE_BASE = {
    "dental": {
        "match_keywords": ["dental", "dentist", "orthodont", "teeth", "implant", "oral"],
        "category_label": "Dental Clinic & Implant Centre",
        "business_intro": "Private healthcare practice providing preventive, restorative, and aesthetic dental care to local residents and families.",
        "customer_profile": "Local residents, families, and patients seeking urgent tooth pain relief or cosmetic smile transformations.",
        "ticket_size_range": "₹500 to ₹60,000+ (Consultations ₹500, Root Canals ₹4k, Implants/Aligners ₹35k-₹1L)",
        "digital_leak": "Losing urgent dental searchers on Google Maps to nearby clinics. High reliance on Practo where competitors are advertised.",
        "solution_offer": "Direct online appointment booking website with smile before/after gallery and 1-click WhatsApp slot confirmation.",
        "roi_formula": "Just ONE single dental implant or smile-makeover patient (₹35,000+) covers the entire website investment.",
        "gatekeeper_opener": "'Hello! Calling for Dr. [Doctor/Clinic Head] regarding patient inquiries searching for dental treatments on Google Maps in [Location]. Could you connect me?'",
        "cold_call_hook": "'Doctor, you have {rating} stars across {reviews} reviews on Google Maps, but when patients search for urgent dental appointments, there is no direct website link. Patients bounce and book other clinics.'",
        "value_pitch": "'We build custom clinic booking pages in 5 days that route appointments straight to your front desk WhatsApp, giving you 100% direct patient ownership without Practo commissions.'",
        "cta": "'Can I WhatsApp you a 30-second mobile preview of our dental smile-booking template? What is your direct number?'",
        "objection_rebuttal": "'Practo brings us patients': 'Yes, but Practo takes a cut and shows 10 competitor dentists right next to your profile. Your own website gives you exclusive patients forever.'"
    },
    "derma_cosmetic": {
        "match_keywords": ["skin", "derma", "dermatolog", "hair", "laser", "cosmetic", "aesthetic", "botox"],
        "category_label": "Dermatology & Aesthetic Clinic",
        "business_intro": "Specialized medical aesthetic center offering clinical skin rejuvenation, acne scar revision, laser treatments, and hair loss therapies.",
        "customer_profile": "Affluent professionals, brides-to-be, and beauty-conscious clients seeking high-end cosmetic and skin treatments.",
        "ticket_size_range": "₹1,500 to ₹50,000+ per treatment cycle (Facials ₹4k, Lasers ₹20k-₹45k, PRP ₹6k/session)",
        "digital_leak": "Patients researching laser and anti-aging treatments require visual proof and instant booking. Without a website, they book rival clinics.",
        "solution_offer": "High-converting mobile landing page featuring treatment before/after results, transparent service guides, and instant WhatsApp booking.",
        "roi_formula": "Just 2 new laser packages or HydraFacial clients completely pay off the entire website in the first 30 days.",
        "gatekeeper_opener": "'Good afternoon! Calling for Dr. [Doctor Name] or the cosmetic clinic manager regarding patient booking flows from Google Maps in [Location].'",
        "cold_call_hook": "'Doctor / Manager, you have an impressive {rating}-star rating with {reviews} reviews, but no direct website button. High-ticket laser and skin clients search online and choose clinics with dedicated portals.'",
        "value_pitch": "'We build high-speed cosmetic clinic booking sites in 5 days that convert local searchers into confirmed WhatsApp consultations.'",
        "cta": "'Can I WhatsApp you a 30-second video demo of how aesthetic clinics capture patient appointments from mobile?'",
        "objection_rebuttal": "'Instagram is enough for us': 'Instagram is great for browsing, but patients searching Google Maps for urgent skin issues want immediate booking, not waiting for slow DMs.'"
    },
    "restaurant_cafe": {
        "match_keywords": ["restaurant", "cafe", "coffee", "bistro", "bakery", "food", "kitchen", "biryani", "pizzeria", "bar", "dining", "sweet"],
        "category_label": "Restaurant, Cafe & Dining",
        "business_intro": "Food service establishment offering dine-in, takeaway, and specialty delicacies to local food lovers, office goers, and families.",
        "customer_profile": "Daily diners, hungry neighbors, working professionals, and weekend gathering parties.",
        "ticket_size_range": "₹200 to ₹3,500 per table / order",
        "digital_leak": "Losing 25% to 30% margin on every delivery order to Zomato & Swiggy commissions. No direct digital menu or direct WhatsApp ordering.",
        "solution_offer": "Branded mobile digital menu with 1-click Direct WhatsApp Ordering and table reservation system (Zero commission).",
        "roi_formula": "Saving 30% Swiggy/Zomato commission on just 25 direct WhatsApp orders pays for the system every single month.",
        "gatekeeper_opener": "'Hi, calling for the restaurant manager or owner regarding customer party bookings and table reservations from Google Maps.'",
        "cold_call_hook": "'Owner / Manager, you have {reviews} customer reviews and great food, but customers searching your name on Google Maps can only order through Zomato where you lose 30% commission on every order.'",
        "value_pitch": "'We build you a direct digital menu with 1-click WhatsApp ordering so repeat neighborhood customers order directly from you at 0% commission.'",
        "cta": "'Can I WhatsApp you a 15-second sample menu link showing how customers place orders directly to your restaurant phone?'",
        "objection_rebuttal": "'Zomato handles all our delivery': 'Zomato is great for new reach, but your regular customers shouldn't cost you 30% every time they re-order. Direct ordering puts that 30% back in your pocket.'"
    },
    "salon_spa": {
        "match_keywords": ["salon", "spa", "beauty parlour", "hair salon", "barber", "grooming", "makeup", "massage"],
        "category_label": "Salon, Spa & Grooming",
        "business_intro": "Personal grooming and wellness studio delivering haircuts, styling, bridal makeup, facials, and relaxation therapies.",
        "customer_profile": "Men and women looking for regular maintenance, premium hair transformations, or pre-event styling.",
        "ticket_size_range": "₹300 to ₹25,000+ (Haircuts ₹400, Keratin/Color ₹5k-₹10k, Bridal Makeup ₹15k-₹30k)",
        "digital_leak": "Heavy appointment cancellations, reception phone congestion, and losing bridal/keratin inquiries due to lack of a digital rate card.",
        "solution_offer": "Chic mobile booking site with service rate-card, stylists' lookbook, and automated WhatsApp appointment confirmations.",
        "roi_formula": "Just 1 or 2 bridal makeup or premium hair spa bookings pay for the entire website setup.",
        "gatekeeper_opener": "'Hello! Calling for the salon manager or head stylist regarding bridal and appointment bookings from Google Maps.'",
        "cold_call_hook": "'Hi! You have {rating} stars and {reviews} reviews, but no direct rate-card website. Customers searching for styling and bridal services in [Location] can't view prices or book slots directly.'",
        "value_pitch": "'We build sleek salon booking pages with WhatsApp appointment scheduling so your chairs stay full without reception back-and-forth.'",
        "cta": "'Can I WhatsApp you a quick 20-second preview of how our salon booking menu looks on a phone?'",
        "objection_rebuttal": "'Clients just walk in': 'Walk-ins are great for basic cuts, but high-ticket bridal and hair spa clients always research prices and book ahead online.'"
    },
    "jewellery_luxury": {
        "match_keywords": ["jewel", "jewellery", "gold", "diamond", "silver", "gems", "ornament"],
        "category_label": "Jewellery & Gem Showroom",
        "business_intro": "Fine jewellery showroom specializing in hallmarked gold ornaments, certified diamonds, wedding bridal sets, and custom designs.",
        "customer_profile": "High-net-worth families, brides, festival shoppers, and gemstone investors seeking authentic, trusted craftsmanship.",
        "ticket_size_range": "₹15,000 to ₹5,00,000+ per purchase",
        "digital_leak": "Shoppers browse Instagram and Google before buying gold. Missing a live WhatsApp digital catalogue causes customers to visit competing national chains.",
        "solution_offer": "Luxurious digital design catalogue with live gold rates, direct WhatsApp inquiry buttons, and private showroom appointment booking.",
        "roi_formula": "Closing just ONE bridal jewellery customer inquiry (₹1,00,000+) completely pays for the website many times over.",
        "gatekeeper_opener": "'Namaste! Calling to speak with the showroom owner or director regarding customer inquiries coming through Google Maps in [Location].'",
        "cold_call_hook": "'Owner / Director, your showroom has a sterling reputation with {reviews} reviews. But modern bridal families want to see catalogues and book private viewing slots on WhatsApp before visiting in person.'",
        "value_pitch": "'We build exclusive digital showroom catalogues in 5 days that let customers browse designs and send instant WhatsApp inquiries for custom jewellery.'",
        "cta": "'May I WhatsApp you a 30-second video demo of our high-end jewellery showroom catalogue?'",
        "objection_rebuttal": "'Gold is only bought in person': 'Exactly! Customers don't buy gold online—they browse the catalogue online first, and then visit your store to finalize the purchase.'"
    },
    "gym_fitness": {
        "match_keywords": ["gym", "fitness", "workout", "crossfit", "yoga", "pilates", "aerobics", "mma"],
        "category_label": "Gym & Fitness Studio",
        "business_intro": "Health club and strength training facility offering cardio, weightlifting, group fitness classes, and personal training.",
        "customer_profile": "Health-conscious youth, working professionals, and fitness enthusiasts looking for physique transformation and vitality.",
        "ticket_size_range": "₹1,500 to ₹35,000 (Monthly ₹2k, Annual Membership ₹15k-₹25k, Personal Training ₹10k/mo)",
        "digital_leak": "High membership churn and failure to capture new local residents moving into the neighborhood searching Google for gyms.",
        "solution_offer": "High-energy gym website with virtual floor tour, transparent membership plans, free trial pass registration, and WhatsApp sign-ups.",
        "roi_formula": "Just 2 annual membership sign-ups or 1 personal training client (₹20,000) completely funds the entire website.",
        "gatekeeper_opener": "'Hi, calling for the gym owner or head trainer regarding free trial pass requests from Google Maps in [Location].'",
        "cold_call_hook": "'Hi Coach / Owner, you have {reviews} reviews on Google, but people searching for gym memberships in [Location] cannot book a free trial pass directly. They end up visiting gyms with instant online passes.'",
        "value_pitch": "'We build dynamic fitness landing pages with 1-click 'Book Free 1-Day Trial Pass' via WhatsApp to instantly capture new member leads.'",
        "cta": "'Can I WhatsApp you a 15-second preview of how our 1-Day Trial Pass funnel brings in new gym members?'",
        "objection_rebuttal": "'People just walk in to see the gym': 'A trial-pass landing page captures their phone number BEFORE they walk in, so your sales team can follow up even if they don't buy immediately.'"
    },
    "retail_clothing": {
        "match_keywords": ["clothing", "boutique", "apparel", "saree", "menswear", "fashion", "garment", "shoes", "tailor", "optical", "furniture"],
        "category_label": "Retail Store & Boutique",
        "business_intro": "Local retail merchant delivering curated merchandise, apparel, traditional wear, or home goods to neighborhood shoppers.",
        "customer_profile": "Shoppers, families, and style-conscious locals looking for quality apparel, festive outfits, or home essentials.",
        "ticket_size_range": "₹500 to ₹35,000+ per bill",
        "digital_leak": "Footfall drop due to e-commerce competition (Amazon/Myntra). Customers don't know latest store arrivals or seasonal stock.",
        "solution_offer": "Interactive WhatsApp digital product catalogue with new arrivals showcase, store location map, and instant inquiry button.",
        "roi_formula": "Selling just 3 to 5 outfits or home items through direct WhatsApp inquiries covers the cost of setting up the catalogue.",
        "gatekeeper_opener": "'Hello! Calling to speak with the store proprietor or manager regarding customer shopping inquiries from Google Maps.'",
        "cold_call_hook": "'Owner / Store Manager, you have {rating} stars and {reviews} reviews. But shoppers searching for clothing and boutiques in [Location] have no way to browse current stock online before visiting.'",
        "value_pitch": "'We build an easy WhatsApp product catalogue where customers browse your latest collection and click 'Buy/Inquire' directly on WhatsApp.'",
        "cta": "'Can I WhatsApp you a 20-second sample of our WhatsApp store catalogue?'",
        "objection_rebuttal": "'We are too small for an e-commerce site': 'This is NOT a complicated e-commerce store. It is a simple WhatsApp catalogue that drives physical footfall to your shop floor.'"
    },
    "realestate_construction": {
        "match_keywords": ["real estate", "property", "builder", "developer", "realtor", "interior", "architect", "construction"],
        "category_label": "Real Estate, Interior & Architecture",
        "business_intro": "Property consultancy, interior design firm, or architecture practice handling commercial and residential spaces.",
        "customer_profile": "Homebuyers, high-net-worth investors, commercial tenants, and homeowners seeking turnkey renovation or properties.",
        "ticket_size_range": "₹50,000 to ₹10,00,000+ (Commissions ₹1L+, Interior projects ₹5L-₹25L)",
        "digital_leak": "High-value clients demand visual portfolios and company credibility. Without a polished website, deals are lost to larger firms.",
        "solution_offer": "Stunning architectural/property portfolio site with project galleries, 3D walkthrough links, and high-intent inquiry lead capture.",
        "roi_formula": "Just ONE single interior client or property deal closes for lakhs—making a ₹50,000 website an immediate 10x ROI.",
        "gatekeeper_opener": "'Good morning! Calling for the principal architect or managing partner regarding project inquiries from Google in [Location].'",
        "cold_call_hook": "'Partner / Director, you have {reviews} reviews on Google, but affluent homeowners searching for premier interiors or properties in [Location] expect a modern project portfolio site before reaching out.'",
        "value_pitch": "'We build high-end architecture and property portfolio websites that showcase your completed projects and capture pre-qualified lead details.'",
        "cta": "'Can I share a 30-second mobile link of our interior design portfolio layout on WhatsApp?'",
        "objection_rebuttal": "'Our business is 100% word-of-mouth': 'Word-of-mouth leads ALWAYS google your company name before meeting you. If your website is missing or outdated, you lose trust before the first pitch.'"
    },
    "corporate_it_services": {
        "match_keywords": ["software", "technolog", "it services", "corporate", "consulting", "marketing", "logistics", "industrial", "office"],
        "category_label": "B2B, IT & Corporate Services",
        "business_intro": "Enterprise service provider delivering technology solutions, business consulting, corporate services, or industrial products.",
        "customer_profile": "Corporate enterprises, business executives, startups, and commercial institutional buyers.",
        "ticket_size_range": "₹50,000 to ₹5,00,000+ contracts",
        "digital_leak": "B2B procurement teams check company credibility and capability decks online before sending RFPs or scheduling calls.",
        "solution_offer": "Executive corporate website with service case studies, client testimonials, service offerings, and automated meeting booking.",
        "roi_formula": "A single B2B contract or corporate retainer pays for corporate web redesign instantly.",
        "gatekeeper_opener": "'Hello, calling for the director of business development or managing director regarding corporate inquiries in [Location].'",
        "cold_call_hook": "'Director, your corporate profile shows {reviews} reviews on Google Maps, but enterprise clients vetting your company online need a modern, responsive web presence with clear service case studies.'",
        "value_pitch": "'We modernize corporate web platforms in 7 days to showcase enterprise capabilities, compliance, and automated Calendly/WhatsApp meeting booking.'",
        "cta": "'May I send a 30-second link showing our B2B capability layout to your WhatsApp or corporate email?'",
        "objection_rebuttal": "'We don't need leads from Google': 'Enterprise buyers use Google to verify your corporate authority and credibility before signing contracts.'"
    },
    "general_local_business": {
        "match_keywords": [],  # Catch-all default
        "category_label": "Local Commercial Business",
        "business_intro": "Established local commercial enterprise serving the neighborhood and greater municipal area with essential products and services.",
        "customer_profile": "General public, residential neighbors, and commercial customers in the immediate locality.",
        "ticket_size_range": "₹300 to ₹25,000+ depending on service scope",
        "digital_leak": "Missing out on local smartphone searchers who pick competitors with active Google Maps websites and direct WhatsApp buttons.",
        "solution_offer": "5-day local business website featuring business hours, product/service breakdown, location directions, and direct WhatsApp contact.",
        "roi_formula": "Attracting just a handful of new recurring neighborhood customers pays for the website within weeks.",
        "gatekeeper_opener": "'Hello! Calling to speak with the business owner or proprietor regarding customer inquiries from Google Maps in [Location].'",
        "cold_call_hook": "'Owner / Manager, you have {rating} stars and {reviews} reviews on Google Maps. But when local customers search for your services in [Location], there is no direct website button. They end up calling competitors.'",
        "value_pitch": "'We build clean, affordable 5-day local websites with 1-click WhatsApp buttons so customers find you and contact you instantly.'",
        "cta": "'Can I WhatsApp you a 20-second sample preview of how a local business site works on mobile?'",
        "objection_rebuttal": "'We are already well known locally': 'Being well-known is great, but new residents moving to the area rely 100% on Google Maps to choose who to call.'"
    }
}

def detect_industry(category_str, name_str):
    combined = (category_str + " " + name_str).lower()
    for key, data in INDUSTRY_KNOWLEDGE_BASE.items():
        if key == "general_local_business":
            continue
        for kw in data["match_keywords"]:
            if kw in combined:
                return key, data
    return "general_local_business", INDUSTRY_KNOWLEDGE_BASE["general_local_business"]

def enrich_business(lead_dict, location_str):
    name = lead_dict.get("title", "Local Business")
    category = lead_dict.get("category", "")
    phone = lead_dict.get("phone", "")
    website = lead_dict.get("website", "")
    rating = lead_dict.get("rating", "4.5")
    reviews = lead_dict.get("reviews", "20")
    address = lead_dict.get("address", location_str)
    maps_url = lead_dict.get("maps_url", "")

    industry_key, intel = detect_industry(category, name)

    has_website = bool(website and website.strip() and "http" in website)
    rev_int = int(reviews) if str(reviews).isdigit() else 20
    rat_flt = float(rating) if rating else 4.5

    # Grade the lead
    if not has_website and rev_int >= 15:
        lead_grade = "HOT - Grade A (No Website, Established Business)"
        leak = f"Business has {rev_int} reviews ({rat_flt}★) but NO website button on Maps. High-intent searchers bounce to competitors daily."
    elif not has_website and rev_int < 15:
        lead_grade = "HOT - Grade A (No Website & Review Booster Opportunity)"
        leak = f"No website and only {rev_int} reviews. Needs both an online presence and a Google Review Booster."
    else:
        lead_grade = "WARM - Grade B (Website Redesign / App Upsell)"
        leak = f"Existing website exists ({website}), but likely lacks mobile optimization, instant WhatsApp booking, or fast conversion flows."

    # Format battle-card strings
    hook = intel["cold_call_hook"].format(rating=rat_flt, reviews=rev_int, location=location_str)
    hook = hook.replace("[Location]", location_str)
    gatekeeper = intel["gatekeeper_opener"].replace("[Location]", location_str)
    cta = intel["cta"].replace("[Location]", location_str)

    return {
        "Lead_Grade": lead_grade,
        "Business_Name": name,
        "Category": intel["category_label"] + (f" ({category})" if category else ""),
        "Phone_Number": phone if phone else "Listing has no public phone",
        "Website_Status": website if has_website else "NO WEBSITE (Missing on Google Maps)",
        "Google_Rating": f"{rat_flt}★",
        "Review_Count": rev_int,
        "Full_Address": address,
        "Google_Maps_URL": maps_url,
        "Business_Intro": intel["business_intro"],
        "Customer_Profile": intel["customer_profile"],
        "Customer_Ticket_Size": intel["ticket_size_range"],
        "Digital_Leak_Pain_Point": leak,
        "Solution_We_Offer": intel["solution_offer"],
        "Financial_ROI_Anchor": intel["roi_formula"],
        "Gatekeeper_Opener": gatekeeper,
        "Cold_Call_Hook": hook,
        "Value_Pitch": intel["value_pitch"],
        "Closing_CTA": cta,
        "Objection_Rebuttal": intel["objection_rebuttal"]
    }

def scrape_google_maps_all(location, search_term="businesses", max_scrolls=12):
    """Scrapes ALL businesses for a given location using Playwright Chromium."""
    query = f"{search_term} in {location}" if search_term else location
    url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
    
    print(f"\n=======================================================")
    print(f"🚀 Starting Universal Lead Scraper")
    print(f"📍 Location: {location}")
    print(f"🔍 Search Query: {query}")
    print(f"🌐 Scraping Engine: Google Maps Live via Playwright")
    print(f"=======================================================\n")

    scraped_leads = []
    seen_titles = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN"
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=35000)
            page.wait_for_timeout(4000)
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            browser.close()
            return []

        feed = page.locator('div[role="feed"]')
        if feed.count() == 0:
            print("⚠️ No scrollable feed found. Checking single place or alternative view...")
        else:
            print(f"📜 Feed detected. Scrolling to load all businesses in {location}...")
            for i in range(max_scrolls):
                feed.evaluate("el => el.scrollBy(0, 1500)")
                page.wait_for_timeout(1800)
                # Print progress
                current_count = page.locator('div[role="feed"] > div > div[role="article"]').count()
                print(f"   ↳ Scroll {i+1}/{max_scrolls}: {current_count} businesses rendered...")

        articles = page.locator('div[role="feed"] > div > div[role="article"]').all()
        print(f"\n⚡ Extracting data points from {len(articles)} business cards...")

        for idx, art in enumerate(articles, start=1):
            try:
                # 1. Title & Maps Link
                link_el = art.locator('a.hfpxzc').first
                title = link_el.get_attribute('aria-label') if link_el.count() > 0 else ""
                maps_url = link_el.get_attribute('href') if link_el.count() > 0 else ""

                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                # 2. Text lines
                text = art.inner_text()
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                # 3. Rating & Reviews
                rating = "4.5"
                reviews = "25"
                rating_match = re.search(r'(\d\.\d)\s*\(([\d,]+)\)', text)
                if rating_match:
                    rating = rating_match.group(1)
                    reviews = rating_match.group(2).replace(',', '')

                # 4. Category & Address
                category = ""
                address = ""
                for line in lines:
                    if "·" in line and not re.search(r'Open|Closed|Closes|Opens', line):
                        parts = [p.strip() for p in line.split("·")]
                        if len(parts) >= 2:
                            category = parts[0]
                            address = parts[1]
                        elif len(parts) == 1:
                            category = parts[0]
                        break

                # 5. Phone Number
                phone = ""
                phone_match = re.search(r'(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|0\d{2,4}[\s-]?\d{6,8}', text)
                if phone_match:
                    phone = phone_match.group(0).strip()

                # 6. Website
                website = ""
                web_link = art.locator('a[aria-label*="website" i], a[data-value="Website"]').first
                if web_link.count() > 0:
                    website = web_link.get_attribute('href') or "Has Website"

                # Enrich with Intelligence
                raw_lead = {
                    "title": title,
                    "category": category,
                    "phone": phone,
                    "website": website,
                    "rating": rating,
                    "reviews": reviews,
                    "address": f"{address}, {location}" if address else location,
                    "maps_url": maps_url
                }

                enriched = enrich_business(raw_lead, location)
                scraped_leads.append(enriched)
                print(f"   [{idx}] {title} | {enriched['Category']} | Grade: {enriched['Lead_Grade'][:15]}...")

            except Exception as e:
                continue

        browser.close()

    return scraped_leads

def save_leads_to_csv(leads, output_file):
    if not leads:
        print("No leads to save.")
        return
    fieldnames = list(leads[0].keys())
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in leads:
            writer.writerow(r)
    print(f"\n✅ Successfully exported {len(leads)} enriched leads to:")
    print(f"   📁 {os.path.abspath(output_file)}")

if __name__ == "__main__":
    target_loc = sys.argv[1] if len(sys.argv) > 1 else "Banjara Hills, Hyderabad"
    target_search = sys.argv[2] if len(sys.argv) > 2 else "businesses"
    out_file = sys.argv[3] if len(sys.argv) > 3 else "all_leads_enriched.csv"

    leads = scrape_google_maps_all(target_loc, target_search, max_scrolls=8)
    save_leads_to_csv(leads, out_file)
