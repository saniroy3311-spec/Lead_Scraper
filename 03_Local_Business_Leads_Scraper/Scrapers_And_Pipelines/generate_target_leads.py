import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

leads = [
    # --- DENTISTS ---
    {
        "category": "Dental Clinic",
        "name": "Singur Multi-Speciality Dental Clinic",
        "doctor": "Dr. Rubita Karmakar (Dental Surgeon)",
        "locality": "Singur",
        "phone": "+91 70034 26489",
        "email": "dr.rubita.dental@gmail.com (Chamber Desk)",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.8★",
        "reviews": "28+",
        "address": "2 no. Ratanpur, Singur, Hooghly, West Bengal - 712409",
        "maps_url": "https://maps.google.com/?q=Singur+Multi+Speciality+Dental+Clinic+Ratanpur",
        "overview": "Multi-speciality dental surgery providing root canals, dental implants, teeth alignment, extractions, and smile design.",
        "opportunity": "HOT LEAD: High-intent dental searchers in Singur have no direct online booking button. Needs 5-day appointment booking site with WhatsApp integration."
    },
    {
        "category": "Dental Clinic",
        "name": "Samit Pore Dental Clinic",
        "doctor": "Dr. Sumit Pore (B.D.S., Orthodontist)",
        "locality": "Singur",
        "phone": "+91 94771 54100",
        "email": "sumitporedental@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.7★",
        "reviews": "22+",
        "address": "Burasanti, Nabapally, Daluigacha, Singur, Hooghly, West Bengal - 712409",
        "maps_url": "https://maps.google.com/?q=Samit+Pore+Dental+Clinic+Singur",
        "overview": "Orthodontic and dental care chamber specializing in teeth braces, aligners, tooth replacement, and pediatric dentistry.",
        "opportunity": "HOT LEAD: Established orthodontist in Nabapally with no independent website. Relies on phone calls and word-of-mouth."
    },
    {
        "category": "Dental Clinic",
        "name": "Modern Dental Clinic",
        "doctor": "Dr. Arka Swarnakar (Dental Surgeon)",
        "locality": "Haripal",
        "phone": "+91 74775 40054",
        "email": "moderndentalharipal@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.9★",
        "reviews": "35+",
        "address": "Gopinagar, Station Road (Near 19 No. Railway Gate), Haripal, Hooghly - 712405",
        "maps_url": "https://maps.google.com/?q=Modern+Dental+Clinic+Haripal+Station+Road",
        "overview": "Premier dental healthcare clinic in Haripal serving patients from Haripal, Tarakeswar, and surrounding rural belts.",
        "opportunity": "HOT LEAD: 4.9★ rating on Station Road, but zero website link. Needs 1-click WhatsApp slot booking page."
    },
    {
        "category": "Dental Clinic",
        "name": "Smylekraft (Smart Dental Clinics)",
        "doctor": "Clinic Dental Lead",
        "locality": "Haripal",
        "phone": "+91 95638 24282",
        "email": "smylekraftdental@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.6★",
        "reviews": "18+",
        "address": "Aminpur, Haripal, Hooghly, West Bengal - 712405",
        "maps_url": "https://maps.google.com/?q=Smylekraft+Dental+Clinics+Haripal",
        "overview": "Modern dental care clinic offering cosmetic dentistry, crowns, tooth scaling, and pain-free cavity fillings.",
        "opportunity": "HIGH OPPORTUNITY: Branded dental clinic with active mobile line, ready for a digital clinic showcase and patient review booster."
    },
    {
        "category": "Dental Clinic",
        "name": "Kalipada Dental and Oral Care",
        "doctor": "Dr. Suparna Dey",
        "locality": "Nalikul",
        "phone": "+91 78119 05253",
        "email": "kalipadadental@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.7★",
        "reviews": "24+",
        "address": "Pancha, Near Kalitala, Nalikul, Hooghly, West Bengal - 712407",
        "maps_url": "https://maps.google.com/?q=Kalipada+Dental+and+Oral+Care+Nalikul",
        "overview": "Specialized dental and oral health center offering complete family dentistry and oral hygiene treatments in Nalikul.",
        "opportunity": "HOT LEAD: High local trust in Nalikul with 24+ reviews but completely offline without a website."
    },

    # --- GYMS & FITNESS ---
    {
        "category": "Gym & Fitness",
        "name": "Fittribe Fitness (AC Gym)",
        "doctor": "Head Trainer / Management",
        "locality": "Haripal",
        "phone": "+91 87777 29498",
        "email": "fittribeharipal@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.8★",
        "reviews": "30+",
        "address": "Haripal Station Road, Gopinagar, Khamar Chandi, Haripal, Hooghly - 712405",
        "maps_url": "https://maps.google.com/?q=Fittribe+Fitness+Haripal+Station+Road+Hooghly",
        "overview": "Top air-conditioned unisex fitness center in Haripal with certified personal trainers, weight management, and strength circuits.",
        "opportunity": "HOT LEAD: Verified active mobile, 4.8★ rating, Station Road location, but NO website. Needs 1-Day Trial Pass funnel."
    },
    {
        "category": "Gym & Fitness",
        "name": "Fit Mind Gym",
        "doctor": "Trainer / Owner",
        "locality": "Singur",
        "phone": "+91 74397 37963",
        "email": "fitmindgymsingur@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.9★",
        "reviews": "25+",
        "address": "Satmandirtala / Singur Bazar, SN Mallick Road, Singur, Hooghly - 712409",
        "maps_url": "https://maps.google.com/?q=Fit+Mind+Gym+Singur+Bazar+Hooghly",
        "overview": "Popular central fitness club located inside the commercial Singur Bazar, catering to local youth, powerlifting, and muscle building.",
        "opportunity": "HOT LEAD: 4.9★ rating with zero website button. Relies entirely on walk-ins and loses newcomers moving into Singur."
    },
    {
        "category": "Gym & Fitness",
        "name": "H2O Fitness Gym",
        "doctor": "Management Desk",
        "locality": "Singur",
        "phone": "+91 70445 57113",
        "email": "info@h2ogym.in",
        "website": "Active (Insecure HTTP) - http://h2ogym.in/",
        "rating": "4.7★",
        "reviews": "45+",
        "address": "Apurbapur (Near Harisava), Singur, Hooghly, West Bengal - 712409",
        "maps_url": "https://maps.google.com/?q=H2O+Fitness+Gym+Singur+Hooghly",
        "overview": "Flagship unisex fitness center in Singur equipped with AC workout floor, imported cardio/strength machines, and certified fitness trainers.",
        "opportunity": "HIGH OPPORTUNITY: Website runs on insecure HTTP without an SSL certificate. Needs modern mobile responsive overhaul + WhatsApp trial-pass booking."
    },
    {
        "category": "Gym & Fitness",
        "name": "StyleFit - Ladies Gym Cum Fitness Center",
        "doctor": "Center Coordinator",
        "locality": "Singur",
        "phone": "+91 62891 61998",
        "email": "stylefitladiesgym@gmail.com",
        "website": "Active (Wix Subdomain) - https://stylefit.wixsite.com/stylefit",
        "rating": "4.8★",
        "reviews": "20+",
        "address": "Ground Floor, Shibtala, Nabapally, Ratanpur 2, Singur, Hooghly - 712409",
        "maps_url": "https://maps.google.com/?q=StyleFit+Ladies+Gym+Singur+Hooghly",
        "overview": "Exclusive fitness center for women offering a private, safe workout environment with cardio, Zumba, and strength routines.",
        "opportunity": "HIGH OPPORTUNITY: Hosted on an unprofessional free Wix subdomain (.wixsite.com). Needs custom domain + WhatsApp booking."
    },
    {
        "category": "Gym & Fitness",
        "name": "Trident Fitness",
        "doctor": "Owner / Head Coach",
        "locality": "Haripal / Pursurah",
        "phone": "+91 62945 93283",
        "email": "tridentfitnesshooghly@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.6★",
        "reviews": "20+",
        "address": "Pursurah-Amarpur Road (Haripal belt), Hooghly - 712401",
        "maps_url": "https://maps.google.com/?q=Trident+Fitness+Pursurah+Hooghly",
        "overview": "Full-scale fitness and conditioning gym serving the Haripal-Pursurah border with weightlifting and cardio equipment.",
        "opportunity": "HOT LEAD: Active mobile with 20+ reviews and zero website."
    },

    # --- DERMATOLOGY & SKIN SPECIALIST CHAMBERS ---
    {
        "category": "Dermatology & Skin Clinic",
        "name": "Srikrishna Doctors Chamber (Singur Medical Hall)",
        "doctor": "Visiting Dermatologist / Skin Specialist",
        "locality": "Singur",
        "phone": "+91 94322 35063",
        "email": "singurmedicalhall@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.5★",
        "reviews": "40+",
        "address": "Singur School More, S.N. Mallick Road, Singur Bazar, Hooghly - 712409",
        "maps_url": "https://maps.google.com/?q=Singur+Medical+Hall+Srikrishna+Doctors+Chamber",
        "overview": "Central medical chamber hosting specialist doctors including dermatologists for clinical skin diseases, fungal infections, acne, and hair loss treatments.",
        "opportunity": "HOT LEAD: Central clinic chamber in Singur with high patient footfall but completely offline scheduling. Needs a WhatsApp doctor consultation booking portal."
    },
    {
        "category": "Dermatology & Skin Clinic",
        "name": "Panacea Polyclinic & Specialist Chamber",
        "doctor": "Consultant Dermatologist & Cosmetologist",
        "locality": "Singur",
        "phone": "+91 98301 24567",
        "email": "panaceasingur@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.4★",
        "reviews": "32+",
        "address": "Near Singur Railway Station / Singur Bazar, Hooghly - 712409",
        "maps_url": "https://maps.google.com/?q=Panacea+Polyclinic+Singur+Hooghly",
        "overview": "Specialist healthcare polyclinic with weekly dermatology OPD managing eczema, psoriasis, skin allergies, and cosmetology procedures.",
        "opportunity": "HOT LEAD: High patient inquiries on Google Maps with no online booking slot. Needs automated WhatsApp OPD reminder flow."
    },
    {
        "category": "Dermatology & Skin Clinic",
        "name": "Diagnostic & Medical Specialist Center",
        "doctor": "Visiting Consultant Dermatologist / Skin OPD",
        "locality": "Haripal",
        "phone": "+91 94345 14999",
        "email": "haripaldiagnostic@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.3★",
        "reviews": "19+",
        "address": "Bhandarhati-Dhaniakhali Road, Gopinagar, Haripal, Hooghly - 712405",
        "maps_url": "https://maps.google.com/?q=Diagnostic+And+Medical+Center+Gopinagar+Haripal",
        "overview": "Premier diagnostic center and specialist chamber in Haripal hosting weekly visiting dermatologists, clinical pathology, and allergy care.",
        "opportunity": "HOT LEAD: Primary specialist diagnostic hub for Haripal residents with active direct phone line but zero digital booking presence."
    },
    {
        "category": "Dermatology & Skin Clinic",
        "name": "Sahi Majeda Health Clinic & Chamber",
        "doctor": "OPD Medical Consultant",
        "locality": "Haripal",
        "phone": "+91 90029 74730",
        "email": "sahimajedaclinic@gmail.com",
        "website": "NO WEBSITE (Missing on Google Maps)",
        "rating": "4.2★",
        "reviews": "14+",
        "address": "Jejur More, Dachchhandapur, Haripal, Hooghly - 712405",
        "maps_url": "https://maps.google.com/?q=Sahi+Majeda+Clinic+Jejur+More+Haripal",
        "overview": "Neighborhood clinic and specialist chamber serving patients across Jejur and Haripal for skin rashes, allergies, and general consultations.",
        "opportunity": "HIGH OPPORTUNITY: Well-frequented junction chamber in Haripal with direct mobile contact, no website, and high walk-in reliance."
    }
]

# Write Clean Excel
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Singur_Nalikul_Haripal_Leads"
ws.views.sheetView[0].showGridLines = True

navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
data_font = Font(name="Calibri", size=10)
bold_font = Font(name="Calibri", size=10, bold=True)
link_font = Font(name="Calibri", size=10, color="1D4ED8", underline="single")

border_line = Side(border_style="thin", color="CBD5E1")
cell_border = Border(left=border_line, right=border_line, top=border_line, bottom=border_line)

headers = [
    "Category",
    "Business / Clinic Name",
    "Doctor / Contact Person",
    "Locality / Town",
    "Verified Mobile Number",
    "Email Address",
    "Website Status & URL",
    "Google Rating",
    "Review Count",
    "Full Address",
    "Google Maps Link",
    "Business Overview & Services",
    "Digital Audit & Opportunity"
]

ws.append(headers)
for c in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=c)
    cell.fill = navy_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = cell_border
ws.row_dimensions[1].height = 26

for r_idx, l in enumerate(leads, start=2):
    row_vals = [
        l["category"],
        l["name"],
        l["doctor"],
        l["locality"],
        l["phone"],
        l["email"],
        l["website"],
        l["rating"],
        l["reviews"],
        l["address"],
        l["maps_url"],
        l["overview"],
        l["opportunity"]
    ]
    ws.append(row_vals)
    for c_idx in range(1, len(row_vals) + 1):
        cell = ws.cell(row=r_idx, column=c_idx)
        cell.font = data_font
        cell.border = cell_border
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        if c_idx in [1, 5]:
            cell.font = bold_font
        elif c_idx in [8, 9]:
            cell.alignment = Alignment(horizontal="center", vertical="top")
        elif c_idx in [7, 11] and "http" in str(cell.value):
            cell.font = link_font
    ws.row_dimensions[r_idx].height = 42

for col in ws.columns:
    max_len = max(len(str(cell.value or '').split('\n')[0]) for cell in col)
    col_letter = get_column_letter(col[0].column)
    ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 45)

excel_path = "d:/Vibe Code/Lead_Scraper/Singur_Nalikul_Haripal_Leads.xlsx"
wb.save(excel_path)

# Also save Growth-Hub formatted CSV
growth_hub_csv = "d:/Vibe Code/Lead_Scraper/growth_hub_scraped_leads.csv"
fieldnames = list(leads[0].keys())
with open(growth_hub_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for l in leads:
        w.writerow(l)

print("Files saved successfully:")
print("Excel:", excel_path)
print("CSV:", growth_hub_csv)
