import csv
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_excel_dossier():
    input_csv = "d:/Vibe Code/Lead_Scraper/all_businesses_with_email_and_deep_intel.csv"
    output_excel = "d:/Vibe Code/Lead_Scraper/Banjara_Hills_Master_Lead_Dossier.xlsx"

    if not os.path.exists(input_csv):
        print(f"File not found: {input_csv}")
        return

    with open(input_csv, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    wb = openpyxl.Workbook()
    
    # -------------------------------------------------------------------------
    # Styles Definition
    # -------------------------------------------------------------------------
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid") # Dark Charcoal
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    hot_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Soft Red/Rose
    warm_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # Soft Yellow/Amber
    
    data_font = Font(name="Calibri", size=10)
    data_font_bold = Font(name="Calibri", size=10, bold=True)
    link_font = Font(name="Calibri", size=10, color="2563EB", underline="single")
    
    thin_border_side = Side(border_style="thin", color="E5E7EB")
    border_data = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    align_left = Alignment(horizontal="left", vertical="top", wrap_text=True)
    align_center = Alignment(horizontal="center", vertical="top", wrap_text=True)

    # -------------------------------------------------------------------------
    # Sheet 1: Master Leads Database
    # -------------------------------------------------------------------------
    ws_master = wb.active
    ws_master.title = "Master_Leads_Database"
    ws_master.views.sheetView[0].showGridLines = True

    headers = [
        "Lead Grade",
        "Business Name",
        "Category / Industry",
        "Mobile / Phone No.",
        "Scraped Email Address",
        "Website Status / URL",
        "Google Rating",
        "Review Count",
        "Google Maps Link",
        "Full Address",
        "Detailed Business Introduction",
        "Target Customer Profile",
        "Customer Ticket Size",
        "Strong Points (Business Strengths)",
        "Weak Points (Digital Leaks)",
        "What is Needed to Convert Lead to Customer",
        "Our Solution / Offer",
        "1-Client ROI Formula",
        "Gatekeeper Opener",
        "10-Second Cold Call Hook",
        "Value Pitch",
        "Closing CTA (WhatsApp Demo)",
        "Objection Rebuttal"
    ]

    ws_master.append(headers)

    # Style Header
    for col_idx in range(1, len(headers) + 1):
        cell = ws_master.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_data
    ws_master.row_dimensions[1].height = 28

    # Populate Data
    for row_idx, r in enumerate(reader, start=2):
        # Refine detailed business intro
        cat_lower = r.get("Category", "").lower()
        name = r.get("Business_Name", "")
        rating = r.get("Google_Rating", "4.5★")
        reviews = r.get("Review_Count", "20")
        has_web = "http" in r.get("Website_Status", "")
        
        # Build expanded intro
        base_intro = r.get("Business_Intro", "")
        detailed_intro = f"{name} is an active enterprise operating in Banjara Hills, Hyderabad. {base_intro} They maintain a Google review score of {rating} across {reviews} verified customer feedbacks."
        
        # Build specific conversion roadmap
        if not has_web:
            conversion_req = (
                "CONVERSION PLAYBOOK FOR UNLISTED / NO-WEBSITE LEADS:\n"
                "1. Hook: Call out that they have a strong Google rating but ZERO website link, causing high-intent local searchers to book nearby competitors.\n"
                "2. Offer: A turnkey 5-Day mobile booking website with 1-click WhatsApp reservation button.\n"
                "3. ROI Justification: Just 1-2 new high-ticket clients covers the ₹35,000–₹50,000 website cost.\n"
                "4. Closing Step: Do not hard sell. Ask: 'Can I WhatsApp you a 30-second mobile preview link right now?'"
            )
        else:
            conversion_req = (
                "CONVERSION PLAYBOOK FOR WEBSITE MODERNIZATION LEADS:\n"
                "1. Hook: Compliment their established reputation, but highlight that 85% of mobile visitors bounce if the page is slow or lacks direct WhatsApp ordering/booking.\n"
                "2. Offer: Mobile speed optimization, 1-click WhatsApp checkout/inquiry integration, and local SEO schema to outrank competitors.\n"
                "3. ROI Justification: Recovering even 5% of bounced mobile traffic pays for the redesign in month one.\n"
                "4. Closing Step: Send a free 60-second screen audit showing their mobile load speed vs their top local competitor on WhatsApp."
            )

        row_data = [
            r.get("Lead_Grade", ""),
            name,
            r.get("Category", ""),
            r.get("Phone_Number", ""),
            r.get("Email_Address", ""),
            r.get("Website_Status", ""),
            rating,
            int(reviews) if reviews.isdigit() else reviews,
            r.get("Google_Maps_URL", ""),
            r.get("Full_Address", ""),
            detailed_intro,
            r.get("Customer_Profile", ""),
            r.get("Customer_Ticket_Size", ""),
            r.get("Strong_Points", ""),
            r.get("Weak_Points", ""),
            conversion_req,
            r.get("Solution_We_Offer", ""),
            r.get("Financial_ROI_Anchor", ""),
            r.get("Gatekeeper_Opener", ""),
            r.get("Cold_Call_Hook", ""),
            r.get("Value_Pitch", ""),
            r.get("Closing_CTA", ""),
            r.get("Objection_Rebuttal", "")
        ]

        ws_master.append(row_data)

        # Style data row
        is_hot = "HOT" in r.get("Lead_Grade", "")
        row_fill = hot_fill if is_hot else (warm_fill if "WARM" in r.get("Lead_Grade", "") else None)

        for col_idx in range(1, len(row_data) + 1):
            cell = ws_master.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = border_data
            cell.alignment = align_left

            # Highlights
            if col_idx == 1:
                cell.font = data_font_bold
                cell.alignment = align_center
                if row_fill:
                    cell.fill = row_fill
            elif col_idx in [7, 8]:
                cell.alignment = align_center
            elif col_idx in [6, 9] and "http" in str(cell.value):
                cell.font = link_font

        ws_master.row_dimensions[row_idx].height = 45

    # -------------------------------------------------------------------------
    # Sheet 2: HOT Priority Leads (Priority 1 Dial List)
    # -------------------------------------------------------------------------
    ws_hot = wb.create_sheet(title="HOT_Leads_Priority_1")
    ws_hot.views.sheetView[0].showGridLines = True
    ws_hot.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws_hot.cell(row=1, column=col_idx)
        cell.fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid") # Dark Red
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_data
    ws_hot.row_dimensions[1].height = 28

    hot_row_idx = 2
    for r in reader:
        if "HOT" in r.get("Lead_Grade", ""):
            name = r.get("Business_Name", "")
            rating = r.get("Google_Rating", "4.5★")
            reviews = r.get("Review_Count", "20")
            base_intro = r.get("Business_Intro", "")
            detailed_intro = f"{name} is an active enterprise operating in Banjara Hills, Hyderabad. {base_intro} They maintain a Google review score of {rating} across {reviews} verified customer feedbacks."
            
            conversion_req = (
                "HOW TO CONVERT THIS HOT LEAD:\n"
                "1. Call Dr./Owner directly using Gatekeeper Opener.\n"
                "2. Hook: 'You have high reviews on Google Maps, but ZERO website button. High-intent searchers are booking competitors on Road 12.'\n"
                "3. ROI Anchor: 'Just 1-2 new clients completely pays for the 5-day website.'\n"
                "4. CTA: Send 30-sec WhatsApp preview demo immediately."
            )

            row_data = [
                r.get("Lead_Grade", ""),
                name,
                r.get("Category", ""),
                r.get("Phone_Number", ""),
                r.get("Email_Address", ""),
                r.get("Website_Status", ""),
                rating,
                int(reviews) if reviews.isdigit() else reviews,
                r.get("Google_Maps_URL", ""),
                r.get("Full_Address", ""),
                detailed_intro,
                r.get("Customer_Profile", ""),
                r.get("Customer_Ticket_Size", ""),
                r.get("Strong_Points", ""),
                r.get("Weak_Points", ""),
                conversion_req,
                r.get("Solution_We_Offer", ""),
                r.get("Financial_ROI_Anchor", ""),
                r.get("Gatekeeper_Opener", ""),
                r.get("Cold_Call_Hook", ""),
                r.get("Value_Pitch", ""),
                r.get("Closing_CTA", ""),
                r.get("Objection_Rebuttal", "")
            ]
            ws_hot.append(row_data)

            for col_idx in range(1, len(row_data) + 1):
                cell = ws_hot.cell(row=hot_row_idx, column=col_idx)
                cell.font = data_font
                cell.border = border_data
                cell.alignment = align_left
                if col_idx == 1:
                    cell.font = data_font_bold
                    cell.fill = hot_fill
                    cell.alignment = align_center
                elif col_idx in [7, 8]:
                    cell.alignment = align_center
                elif col_idx in [6, 9] and "http" in str(cell.value):
                    cell.font = link_font

            ws_hot.row_dimensions[hot_row_idx].height = 45
            hot_row_idx += 1

    # -------------------------------------------------------------------------
    # Sheet 3: Cold Calling & Conversion Playbook
    # -------------------------------------------------------------------------
    ws_playbook = wb.create_sheet(title="Conversion_Playbook")
    ws_playbook.views.sheetView[0].showGridLines = True
    
    playbook_headers = ["Phase", "Time Window", "Objective", "Exact Script & Action Item", "Psychological Trigger"]
    ws_playbook.append(playbook_headers)
    for col_idx in range(1, len(playbook_headers) + 1):
        cell = ws_playbook.cell(row=1, column=col_idx)
        cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Navy
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_data
    ws_playbook.row_dimensions[1].height = 28

    playbook_steps = [
        (
            "Phase 1: Gatekeeper Bypass",
            "00:00 - 00:30",
            "Get past the receptionist / clinic front desk without sounding like a sales rep.",
            "'Hello, good afternoon! I am calling regarding customer appointment inquiries from your Google Maps profile in Banjara Hills. Could you connect me with Dr. [Name] or the general manager?'",
            "Authority & Technical Relevance (Sounds like a patient coordination / platform call, not a cold telemarketer)."
        ),
        (
            "Phase 2: The Compliment & Digital Leak Hook",
            "00:30 - 01:00",
            "Lower the owner's defenses by praising their reputation, then expose their hidden financial leak.",
            "'Congratulations on your [X] reviews and 4.8★ rating on Google Maps. However, when local clients search for you in Banjara Hills, there is NO website button to click. They bounce and book the competitor directly below you.'",
            "Ego Validation + FOMO (Fear Of Missing Out to local rivals)."
        ),
        (
            "Phase 3: The 1-Client ROI Formula",
            "01:00 - 01:45",
            "Remove all pricing resistance by comparing website cost against their customer ticket size.",
            "'We build a turnkey, high-speed booking site in 5 days with direct WhatsApp integration. Just ONE single client or customer purchase (₹25k–₹50k) completely pays for the whole website.'",
            "Financial Asymmetry (The upside of 1 client dwarfs the cost of the website)."
        ),
        (
            "Phase 4: The Low-Friction Closing CTA",
            "01:45 - 02:15",
            "Secure permission to send a 30-second mobile video preview on WhatsApp (Do NOT ask for money on call 1).",
            "'I do not expect you to decide anything right now. I have already designed a 30-second interactive preview of how your booking site will look on a phone. Can I WhatsApp the preview link to this number right now?'",
            "Zero Commitment / Micro-Yes (It costs them nothing to say yes to a 30-second preview)."
        ),
        (
            "Phase 5: Objection Handling - 'We use Practo / Zomato'",
            "When Raised",
            "Neutralize reliance on third-party aggregators.",
            "'Aggregators are great for brand new reach, but they display 10 competitor businesses right below your listing and take 15%-30% commissions. Your own direct website gives you 100% customer ownership forever.'",
            "Ownership & Margin Protection."
        ),
        (
            "Phase 6: Objection Handling - 'Send Details on Email'",
            "When Raised",
            "Pivot from an email blow-off into a high-converting WhatsApp message.",
            "'I will definitely send an email, but an email will not show you how fast the booking button works on a phone. May I send a 30-second video demo directly to your WhatsApp? It takes 15 seconds to view.'",
            "Speed & Sensory Proof."
        )
    ]

    for p_idx, step in enumerate(playbook_steps, start=2):
        ws_playbook.append(step)
        for c_idx in range(1, len(step) + 1):
            cell = ws_playbook.cell(row=p_idx, column=c_idx)
            cell.font = data_font
            cell.border = border_data
            cell.alignment = align_left
            if c_idx == 1:
                cell.font = data_font_bold
            elif c_idx == 2:
                cell.alignment = align_center
        ws_playbook.row_dimensions[p_idx].height = 40

    # -------------------------------------------------------------------------
    # Auto-adjust column widths for all sheets
    # -------------------------------------------------------------------------
    for ws in [ws_master, ws_hot, ws_playbook]:
        ws.freeze_panes = "A2"
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                # Ignore very long multi-line text for width calculation
                first_line = val.split('\n')[0]
                if len(first_line) > max_len:
                    max_len = len(first_line)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 45)

    wb.save(output_excel)
    print(f"Successfully generated Master Excel Dossier at: {output_excel}")

if __name__ == "__main__":
    build_excel_dossier()
