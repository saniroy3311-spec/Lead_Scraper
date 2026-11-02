import csv
import json
import os

# Sample verified leads dataset representing Banjara Hills, Hyderabad (Priority #1 in Playbook)
leads_data = [
    {
        "business_name": "The Skin Sense Aesthetics & Laser Clinic",
        "doctor_or_founder": "Dr. Alekya Singapore (Chief Dermatologist)",
        "locality": "Road No. 12, Banjara Hills, Hyderabad",
        "phone": "+91 91211 44552",
        "rating": 4.8,
        "review_count": 86,
        "website_status": "No Website (Google Maps Listing Only)",
        "instagram_profile": "instagram.com/theskinsense_hyd (Active, 14.5k followers)",
        "lead_tier": "HOT - No Website & Instagram Only (Priority 1)",
        "business_intro": "High-end aesthetic dermatology clinic catering to wealthy Banjara Hills residents and Tollywood/celebrity clients. Focuses on premium clinical skin treatments.",
        "core_services_high_ticket": "HydraFacial (₹4.5k - ₹12k), Laser Hair Reduction packages (₹18k - ₹45k), PRP Hair Loss therapy (₹6k/session), Chemical Peels & Botox.",
        "client_ticket_size": "₹5,000 to ₹40,000+ per treatment cycle",
        "pain_point_and_leak": "Losing 40-50 high-intent Google Maps searchers every week because there is no direct booking site. Currently relies on slow Instagram DMs and manual phone calls, causing lead drop-offs.",
        "how_we_help_business": "Build a fast 5-day mobile booking landing page with 1-click WhatsApp slot reservation and high-res before/after gallery to convert searchers instantly.",
        "gatekeeper_opener": "'Hello! I'm calling for Dr. Alekya regarding patient booking inquiries coming from Google Maps in Banjara Hills. Could you connect me with Dr. Alekya or the clinic manager?'",
        "cold_call_opening_hook": "'Dr. Alekya / Manager, you have 86 five-star reviews on Google Maps and great Instagram reels, but you don't have a direct website button. Google searchers are dropping off and booking competitor clinics on Road 12 instead of you.'",
        "pitch_value_proposition": "'We build custom clinic booking pages in 5 days that connect directly to your front desk WhatsApp. Just 2 new Laser or HydraFacial patients will completely cover the cost of the website.'",
        "call_to_action_cta": "'I've put together a 30-second interactive preview of how a Banjara Hills derma booking site looks on mobile. Can I share it on your WhatsApp right now?'",
        "objection_rebuttal": "'Practo/Instagram is enough': 'Practo shows 10 competitor clinics right next to your profile and takes fees. A dedicated website ensures 100% exclusive patient booking.'",
        "recommended_deal_size": "₹35,000 – ₹60,000 (Tier-1 City Website Package)"
    },
    {
        "business_name": "Clinica Derm & Cosmetic Centre",
        "doctor_or_founder": "Dr. Rohit / Medical Director",
        "locality": "Road No. 2, Banjara Hills, Hyderabad",
        "phone": "+91 98490 23114",
        "rating": 4.9,
        "review_count": 142,
        "website_status": "Outdated, Non-responsive HTML site (Broken mobile view)",
        "instagram_profile": "instagram.com/clinicaderm_official",
        "lead_tier": "WARM - Old Website & Broken Mobile Experience (Priority 2)",
        "business_intro": "Established medical cosmetology center with exceptional patient satisfaction (4.9 stars) specializing in anti-aging, pigmentation, and acne scar subcision.",
        "core_services_high_ticket": "Acne Scar Revision (₹15k - ₹35k), Anti-Aging Thread Lifts & Fillers (₹25k - ₹60k), Medi-Facials, Laser Pigmentation.",
        "client_ticket_size": "₹8,000 to ₹50,000+ per patient",
        "pain_point_and_leak": "Current website was built in 2017. It takes 6+ seconds to load on 4G mobile, has broken appointment forms, and lacks WhatsApp integration, wasting their 142 Google reviews.",
        "how_we_help_business": "Modernize the website with ultra-fast mobile loading (<1.5s), automated WhatsApp confirmation, and local SEO schema to outrank Practo listings on Google.",
        "gatekeeper_opener": "'Hi, this is a quick call regarding the appointment form on Clinica Derm's website—it seems mobile visitors can't submit requests. May I speak to the clinic administrator?'",
        "cold_call_opening_hook": "'Doctor, you have an outstanding 4.9-star rating with over 140 reviews, but your website is not mobile-friendly. Over 85% of Banjara Hills patients search on mobile phones and bounce when the page takes too long.'",
        "pitch_value_proposition": "'We can redesign and migrate your site in 5 days with 1-click WhatsApp booking. You won't lose a single patient searching for acne scar or anti-aging treatments.'",
        "call_to_action_cta": "'Let me send you a free 60-second screen audit of your website's mobile speed vs your top competitor in Banjara Hills on WhatsApp. What is your direct number?'",
        "objection_rebuttal": "'We are too busy with walk-ins': 'Understood! That's why our automated WhatsApp booking screens patients before they walk in, saving your reception staff 2 hours of phone coordination daily.'",
        "recommended_deal_size": "₹45,000 – ₹75,000 (Redesign + WhatsApp Integration)"
    },
    {
        "business_name": "Amista Skin & Hair Aesthetics",
        "doctor_or_founder": "Clinic Operations Lead / Dr. Sneha",
        "locality": "Road No. 1, Banjara Hills, Hyderabad",
        "phone": "+91 90005 67891",
        "rating": 4.6,
        "review_count": 48,
        "website_status": "No Website (Active Linktree only)",
        "instagram_profile": "instagram.com/amistaskinandhair (Active Reels & Offers)",
        "lead_tier": "HOT - Instagram Only (Priority 1)",
        "business_intro": "Trendy boutique skin and hair restoration studio focusing on younger professionals, brides, and corporate executives in Hyderabad.",
        "core_services_high_ticket": "Bridal Glow Packages (₹12k - ₹30k), GFC & PRP Hair Rejuvenation (₹15k - ₹40k), Carbon Laser Peel (₹5k/session).",
        "client_ticket_size": "₹6,000 to ₹35,000",
        "pain_point_and_leak": "Heavy spend on creating Instagram Reels and running Meta ads, but sending traffic to a clunky Linktree. Huge drop-off before visitors actually confirm appointment slots.",
        "how_we_help_business": "Create a high-converting 'Direct-to-WhatsApp' landing page showcasing treatments, transparent pricing guides, and instant appointment booking.",
        "gatekeeper_opener": "'Hello! I loved the recent reel on bridal treatments on Amista's page. I had a quick question regarding booking appointments for the clinic manager.'",
        "cold_call_opening_hook": "'Hi, I saw your clinic is doing great on Instagram with reels, but you are routing potential clients to a generic Linktree instead of a branded booking portal.'",
        "pitch_value_proposition": "'We replace Linktree with a high-speed branded booking website that doubles your conversion rate from Instagram ads and Google Maps traffic.'",
        "call_to_action_cta": "'Can I WhatsApp you a sample booking layout we built for aesthetic clinics? It takes 15 seconds to view.'",
        "objection_rebuttal": "'Linktree is free, why pay?': 'Linktree doesn't build brand trust for ₹20,000 bridal packages or rank on Google. A dedicated site captures organic local searches for free.'",
        "recommended_deal_size": "₹35,000 – ₹55,000 (Website + Meta Pixel integration)"
    },
    {
        "business_name": "Srih Skin & Cosmetology Centre",
        "doctor_or_founder": "Dr. D. Sudha Vani (Senior Dermatologist)",
        "locality": "Near Nagarjuna Circle, Banjara Hills, Hyderabad",
        "phone": "+91 98480 55123",
        "rating": 4.5,
        "review_count": 92,
        "website_status": "Outdated Website / No Patient App",
        "instagram_profile": "instagram.com/srihskincentre",
        "lead_tier": "WARM - Multi-Branch / High Ticket Custom App (Priority 2)",
        "business_intro": "Senior dermatologist with over 20+ years of practice, operating branches in both Banjara Hills and Ameerpet. Large recurring patient base.",
        "core_services_high_ticket": "Dermatosurgery, Vitiligo Treatment, Anti-Aging & Fillers, Long-term Psoriasis Management.",
        "client_ticket_size": "₹3,000 to ₹50,000+ (Lifelong patient retention)",
        "pain_point_and_leak": "Running 2 branches with separate offline registers and uncoordinated telephone booking. Chronic patients find it difficult to track follow-ups and prescriptions.",
        "how_we_help_business": "Unified multi-branch booking web portal + custom patient treatment & follow-up reminder mobile application.",
        "gatekeeper_opener": "'Good afternoon! Calling to speak with Dr. Sudha Vani's clinic manager regarding patient scheduling systems between the Banjara Hills and Ameerpet centers.'",
        "cold_call_opening_hook": "'Hello Doctor / Administrator, managing follow-up patient appointments across both your Banjara Hills and Ameerpet clinics over phone calls creates huge reception friction.'",
        "pitch_value_proposition": "'We unify multi-branch clinic scheduling under one central booking system with automated WhatsApp reminders for follow-up appointments.'",
        "call_to_action_cta": "'I'd love to show your administrative team a 10-minute live demo on how 2-branch clinics manage scheduling seamlessly. Would tomorrow morning work?'",
        "objection_rebuttal": "'Our staff is used to our manual register': 'Our system works directly inside WhatsApp, meaning your front desk staff needs zero training.'",
        "recommended_deal_size": "₹80,000 – ₹1,80,000 (Multi-branch unified web portal + patient reminder app)"
    }
]

def export_leads():
    output_csv = "d:/Vibe Code/Lead_Scraper/banjara_hills_derma_leads_dossier.csv"
    fieldnames = list(leads_data[0].keys())

    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in leads_data:
            writer.writerow(row)
    
    print(f"Exported {len(leads_data)} enriched leads to: {output_csv}")

if __name__ == "__main__":
    export_leads()
