import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_idx_filter_pages():
    print("🏠 Initializing IDX Filter SEO Engine...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    cities = [row[0] for row in get_tab_data('Cities') if row]
    if not cities:
        cities = ["Palmdale", "Lancaster", "Santa Clarita", "Burbank", "Glendale"]
        
    topics = []
    pages = []
    data = []
    rankings = []

    # Map core semantic filters people search for
    common_filters = [
        ("price", "under-500k", "homes-under-500k", "High"),
        ("price", "under-400k", "homes-under-400k", "High"),
        ("features", "pool", "pool-homes", "Medium"),
        ("bedrooms", "4-bedroom", "4-bedroom-homes", "Medium"),
        ("bedrooms", "3-bedroom", "3-bedroom-homes", "Medium"),
        ("property_type", "new-construction", "new-construction-homes", "High"),
        ("land", "acreage", "homes-with-acreage", "Medium"),
        ("property_type", "townhomes", "townhomes", "Medium"),
        ("price", "luxury", "luxury-homes", "Low")
    ]

    for city in cities:
        c_slug = sf.get_slug(city)
        
        # Select 4-6 popular filters for this city to mock local search variance
        selected_filters = random.sample(common_filters, random.randint(4, 6))
        
        for f_type, f_val, f_label, prio in selected_filters:
            slug = f"{f_label}-{c_slug}"
            
            # Map Topic
            topics.append([city, f_type, f_val, slug, prio])
            
            # Request Page Generation
            pages.append([city, slug, f_type, f_val, prio, "No", "Yes"])
            
            # Mock Data Pull (Like hitting the actual IDX feed)
            listings_count = random.randint(2, 60)
            avg_price = random.randint(350000, 1500000)
            
            data.append([
                city, f_type, f_val, str(listings_count), f"${avg_price:,}", datetime.now().strftime("%Y-%m-%d")
            ])
            
            # Target Keyword Ranking Metrics (Hypothetical)
            search_vol = random.randint(50, 1500)
            kw = f"{f_label.replace('-', ' ')} in {city}"
            rankings.append([
                slug, "Pending", str(search_vol), kw, prio
            ])

    # PUSH TO GOOGLE SHEETS
    if topics:
        headers = sf.PHASE1_TABS['IDX_Filter_Topics']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'IDX_Filter_Topics'!A1", valueInputOption='RAW', body={'values': headers + topics}).execute()

    if pages:
        headers = sf.PHASE1_TABS['IDX_Filter_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'IDX_Filter_Pages'!A1", valueInputOption='RAW', body={'values': headers + pages}).execute()

    if data:
        headers = sf.PHASE1_TABS['IDX_Filter_Data']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'IDX_Filter_Data'!A1", valueInputOption='RAW', body={'values': headers + data}).execute()
        
    if rankings:
        headers = sf.PHASE1_TABS['IDX_Filter_Rankings']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'IDX_Filter_Rankings'!A1", valueInputOption='RAW', body={'values': headers + rankings}).execute()

    print(f"✅ Extracted {len(topics)} high-intent Search Filter SEO Pages across the index.")
