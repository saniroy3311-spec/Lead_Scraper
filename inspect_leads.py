import csv

with open('d:/Vibe Code/Lead_Scraper/all_businesses_with_email_and_deep_intel.csv', encoding='utf-8') as f:
    reader = list(csv.DictReader(f))

print(f"Total leads: {len(reader)}")
for i, r in enumerate(reader[:15], start=1):
    print(f"{i}. {r['Business_Name']} | {r['Phone_Number']} | {r['Email_Address']} | {r['Website_Status']}")
