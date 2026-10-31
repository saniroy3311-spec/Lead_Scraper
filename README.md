# Lead Scraper & Business Intelligence Suite

Autonomous lead generation, multi-threaded enrichment, and business intelligence tool designed for scraping local businesses, clinics, gyms, and professional services across India.

---

## 🎯 Features

- **Google Maps & Local Directory Scraping**: Automated Playwright Chromium browser scraper extracts business names, categories, ratings, reviews, addresses, and maps URLs.
- **Deep Web Intel & Email Extraction**: Multi-threaded web crawler extracts email addresses, social profiles (LinkedIn, Facebook, Instagram), and website statuses.
- **Contact Standardization**: Formats and cleans Indian mobile numbers (`+91 ...`) and creates direct WhatsApp click-to-chat links (`wa.me/...`).
- **Production-Ready Excel & CSV Export**: Formatted with professional styling, navy headers, auto-fitting column dimensions, and gridlines.
- **Digital Opportunity Auditing**: Automatically identifies high-value digital marketing/web development pitches (e.g., missing websites, insecure HTTP, outdated subdomains).

---

## 📂 Key Datasets Generated

| File Name | Niche & Region | Description |
| :--- | :--- | :--- |
| [`Singur_Nalikul_Haripal_Leads.xlsx`](Singur_Nalikul_Haripal_Leads.xlsx) | Dentists, Gyms, Derma (Hooghly) | 14 verified leads with 10-digit mobile numbers and digital audits. |
| [`growth_hub_scraped_leads.csv`](growth_hub_scraped_leads.csv) | Dentists, Gyms, Derma (Hooghly) | Clean CSV formatted in Growth-Hub schema ready for CRM ingestion. |
| [`Banjara_Hills_Verified_Business_Leads.xlsx`](Banjara_Hills_Verified_Business_Leads.xlsx) | Hyderabad Premium Market | 56 verified business leads across premium niches. |
| [`singur_hooghly_gym_leads.csv`](singur_hooghly_gym_leads.csv) | Gyms (Singur) | Verified gyms with direct WhatsApp links and contact details. |
| [`nalikul_haripal_gym_leads.csv`](nalikul_haripal_gym_leads.csv) | Gyms (Nalikul & Haripal) | Verified gyms with contact numbers and locations. |

---

## 🛠️ Script Reference

- `universal_business_scraper.py`: Playwright scraper for Google Maps places and directories.
- `deep_intel_scraper.py`: Multi-threaded email and metadata extractor.
- `clean_production_leads.py`: Cleans raw scraped datasets and strips out boilerplate.
- `generate_target_leads.py`: Builds verified multi-speciality datasets into styled Excel and CSV files.
- `build_excel_dossier.py`: Generates styled Excel workbooks with openpyxl.

---

## 🚀 Getting Started

### Prerequisites

```bash
pip install playwright pandas openpyxl beautifulsoup4 requests
playwright install chromium
```

### Running the Scraper

```bash
# Generate target leads for Hooghly (Singur, Nalikul, Haripal)
python generate_target_leads.py

# Run universal scraper on custom queries
python universal_business_scraper.py
```
