import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_idx_traffic():
    print("🏠 Initializing IDX Traffic Generation Engine...")
    
    # Load registries
    idx_filters_path = os.path.join(sf.ENGINE_ROOT, 'core', 'registries', 'idx_filters.json')
    if not os.path.exists(idx_filters_path):
        print(f"❌ Missing IDX filters at: {idx_filters_path}")
        return
        
    with open(idx_filters_path, 'r') as f:
        idx_filters = json.load(f)
        
    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=sf.SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    if 'IDX_Filter_Plan' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=sf.SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'IDX_Filter_Plan'}}}]
        }).execute()

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    sitemap_data = get_tab_data('Sitemap Inventory')
    existing_urls = set([r[0] for r in sitemap_data if r])
    
    cities = get_tab_data('Cities')
    neighborhoods = get_tab_data('Neighborhoods')
    
    idx_plan_rows = []
    
    # 1. Expand City + Filters
    for c in cities:
        if not c: continue
        city = c[0]
        city_slug = sf.get_slug(city)
        
        # Price Ranges
        for price in idx_filters.get('price_ranges', []):
            slug_variant = f"{city_slug}-homes-{price}"
            idx_url = f"{sf.DOMAIN}/{slug_variant}/"
            if idx_url not in existing_urls:
                idx_plan_rows.append([city, "", "price", price, slug_variant, "IDX Landing", "High", "Planned"])

        # Bedrooms
        for bed in idx_filters.get('bedrooms', []):
            slug_variant = f"{city_slug}-{bed}-homes"
            idx_url = f"{sf.DOMAIN}/{slug_variant}/"
            if idx_url not in existing_urls:
                idx_plan_rows.append([city, "", "bedrooms", bed, slug_variant, "IDX Landing", "High", "Planned"])
                
        # Property Types
        for ptype in idx_filters.get('property_types', []):
            slug_variant = f"{city_slug}-{ptype}"
            idx_url = f"{sf.DOMAIN}/{slug_variant}/"
            if idx_url not in existing_urls:
                idx_plan_rows.append([city, "", "property_type", ptype, slug_variant, "IDX Landing", "Medium", "Planned"])

    # 2. Expand Neighborhood + Filters (Just Features and Property Types to prevent total bloat)
    for n in neighborhoods:
        if not n or len(n) < 2: continue
        hood = n[0]
        city = n[1]
        hood_slug = sf.get_slug(hood)
        
        # Features
        for feat in idx_filters.get('features', []):
            slug_variant = f"{hood_slug}-{feat}"
            idx_url = f"{sf.DOMAIN}/{hood_slug}/{slug_variant}/"
            if idx_url not in existing_urls:
                idx_plan_rows.append([city, hood, "feature", feat, slug_variant, "Neighborhood IDX", "Medium", "Planned"])

    if idx_plan_rows:
        headers = sf.PHASE1_TABS['IDX_Filter_Plan']
        
        # Clear and write
        service.spreadsheets().values().clear(
            spreadsheetId=sf.SPREADSHEET_ID, range="'IDX_Filter_Plan'!A1:H").execute()
            
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'IDX_Filter_Plan'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(idx_plan_rows, 4)}
        ).execute()

    print(f"✅ Generated {len(idx_plan_rows)} dynamic IDX long-tail landing pages successfully.")
