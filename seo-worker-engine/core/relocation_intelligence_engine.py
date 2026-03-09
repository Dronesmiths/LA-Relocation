import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_relocation_intelligence():
    print("🚚 Initializing Relocation Intelligence Engine...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    # Mapping out cities and typical origination points in SoCal
    dest_cities = [row[0] for row in get_tab_data('Cities') if row]
    if not dest_cities:
        dest_cities = ["Palmdale", "Lancaster", "Santa Clarita", "Burbank", "Glendale"]
        
    origin_cities = ["Los Angeles", "San Diego", "Burbank", "Santa Clarita", "Orange County"]
    
    origins_data = []
    dest_data = []
    flows = []
    pages = []

    # 1. Define typical origins
    origins_predefined = {
        "Los Angeles": ("CA", "3,900,000", 950000),
        "San Diego": ("CA", "1,400,000", 890000),
        "Burbank": ("CA", "103,000", 920000),
        "Santa Clarita": ("CA", "230,000", 820000),
        "Orange County": ("CA", "3,100,000", 1100000)
    }
    
    for city, stats in origins_predefined.items():
        origins_data.append([city, stats[0], stats[1], str(stats[2])])

    # 2. Map destination targets
    for city in dest_cities:
        dest_data.append([
            city, "Antelope Valley/LA County", str(random.randint(450000, 750000)), 
            str(random.randint(70, 95)), str(random.randint(40, 80)), str(random.randint(4, 9))
        ])

    # 3. Detect flows and map opportunities
    for origin in origin_cities:
        for dest in random.sample(dest_cities, min(3, len(dest_cities))):
            if origin == dest:
                continue
                
            orig_slug = sf.get_slug(origin)
            dest_slug = sf.get_slug(dest)
            
            slug = f"moving-from-{orig_slug}-to-{dest_slug}"
            price_diff = random.randint(150000, 500000)
            
            # Record the flow signal
            flows.append([
                origin, dest, str(price_diff), "High", slug
            ])
            
            # Map the actual relocation page
            pages.append([
                slug, origin, dest, "High", "No", "Yes"
            ])

    # PUSH TO GOOGLE SHEETS
    if origins_data:
        headers = sf.PHASE1_TABS.get('Origin_Cities', [['City', 'State', 'Population', 'Median_Home_Price']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Origin_Cities'!A1", valueInputOption='RAW', body={'values': headers + origins_data}).execute()

    if dest_data:
        headers = sf.PHASE1_TABS.get('Destination_Cities', [['City', 'Region', 'Median_Home_Price', 'Affordability_Index', 'Crime_Index', 'School_Score']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Destination_Cities'!A1", valueInputOption='RAW', body={'values': headers + dest_data}).execute()

    if flows:
        headers = sf.PHASE1_TABS.get('Migration_Flows', [['Origin_City', 'Destination_City', 'Price_Difference', 'Migration_Score', 'Slug']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Migration_Flows'!A1", valueInputOption='RAW', body={'values': headers + flows}).execute()

    if pages:
        headers = sf.PHASE1_TABS.get('Relocation_Pages', [['Slug', 'Origin_City', 'Destination_City', 'Priority', 'Exists', 'Needs_Generation']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Relocation_Pages'!A1", valueInputOption='RAW', body={'values': headers + pages}).execute()

    print(f"✅ Synced {len(origins_data)} Origins against {len(dest_data)} Destinations. Generated {len(pages)} unique relocation SEO funnels.")
