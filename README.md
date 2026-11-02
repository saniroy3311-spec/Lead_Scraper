# Master Workspace Directory Guide

This workspace is categorized into dedicated project directories:

---

## 📁 1. `01_Instagram_Trading_Intelligence/`
> **Purpose**: The complete batch trading intelligence extraction engine, containing pure trading rules, setup parameters, spoken audio transcripts from video reels, and raw datasets scraped across 27 Instagram trading creators.

- **`Trading_Intelligence_Database/`**:
  - `MASTER_TRADING_INTELLIGENCE_INDEX.md`: Master directory table of all 27 creators and 348 documented strategies.
  - `{creator}/`: 25 individual creator folders containing:
    - `{creator}_Trading_Intelligence.md`: Clean, numbered trading playbook (0 links, 0 social fluff).
    - `{creator}_raw_posts.csv`: Complete raw metadata export.
- **`Scraping_Engines/`**:
  - `run_full_autonomous_batch.py`: Autonomous batch scraper with Whisper video voiceover transcription and auto-retry logic.
  - `batch_trading_intelligence_scraper.py`: Core extraction engine.
  - `generate_master_index.py`: Index generator and validator.
- **`Caches/`**:
  - `carousel_slides_cache.json`: Cached multi-slide carousels.
  - `video_transcripts_cache.json`: Cached Whisper voiceover transcripts.
- **`Archive_Exports/`**:
  - Initial CSV, XLSX, and Markdown exports for Quantified Strategies.

---

## 📁 2. `03_Local_Business_Leads_Scraper/`
> **Purpose**: The original lead generation and business scraping project for local businesses across Banjara Hills, Singur, Nalikul, and Haripal.

- **`Lead_Datasets_And_Dossiers/`**:
  - Verified business leads, derma clinics, gyms, and enriched contact lists (`.csv` and `.xlsx`).
- **`Reports/`**:
  - `COLD_CALLING_DOSSIER.md`: Cold calling scripts and phone-ready prospect sheets.
  - `COMPREHENSIVE_BUSINESS_INTELLIGENCE_REPORT.md`: Comprehensive business audit report.
- **`Scrapers_And_Pipelines/`**:
  - `universal_business_scraper.py`: Core multi-platform scraper.
  - `deep_intel_scraper.py`: Deep web email and phone scraper.
  - `clean_production_leads.py`: Deduplication and verification script.
  - `build_excel_dossier.py` & `build_google_sheet_import.py`: Spreadsheet builders.

---

## 📁 3. `04_Sub_Repositories/`
> **Purpose**: Standalone sub-repositories and agent tools.

- `Agent-Reach/`
- `gods-eye-view/`
- `growth-hub-repo/`
- `temp_repo/`
