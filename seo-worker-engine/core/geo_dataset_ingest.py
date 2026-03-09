import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_geo_grid():
    print("🌍 Initializing Geo-Grid Discovery Engine...")
    
    # 1. Load Geodata (Mocking discovery for now as we don't have actual census tracts)
    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=sf.SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # Ensure tabs
    tabs_to_ensure = ['Geo_Dataset', 'Zip_Pages', 'Geo_Grid_Plan']
    new_tabs = [{'addSheet': {'properties': {'title': t}}} for t in tabs_to_ensure if t not in existing_sheets]
    if new_tabs:
        service.spreadsheets().batchUpdate(spreadsheetId=sf.SPREADSHEET_ID, body={'requests': new_tabs}).execute()
        
    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    cities = get_tab_data('Cities')
    neighborhoods = get_tab_data('Neighborhoods')
    
    geo_dataset = []
    zip_pages = []
    geo_grid_plan = []
    
    discovered_neighborhoods = set([n[0].lower() for n in neighborhoods if n])
    new_neighborhoods = []
    
    # Example logic mapping cities into discovered regions
    city_zip_map = {
        "Palmdale": ["93550", "93551", "93552"],
        "Lancaster": ["93534", "93535", "93536"],
        "Santa Clarita": ["91350", "91351", "91354", "91355"]
    }
    
    osm_suburbs = {
        "Palmdale": ["Desert View Highlands", "Ana Verde", "Ritter Ranch", "Leona Valley"],
        "Lancaster": ["Quartz Hill", "Lake Los Angeles", "Antelope Acres"]
    }
    
    for c in cities:
        if not c: continue
        city = c[0]
        slug = sf.get_slug(city)
        
        # 1. Discover Cities
        geo_dataset.append([slug, city, "city", "Los Angeles County", "", "", "", "Los Angeles", "CA", "Active"])
        
        # 2. Discover ZIP Codes
        zips = city_zip_map.get(city, ["90001"])
        for z in zips:
            geo_dataset.append([f"{slug}-{z}", z, "zip", city, "", "", "", "Los Angeles", "CA", "Active"])
            zip_pages.append([z, city, f"{slug}-{z}-real-estate", "", "High", "Planned"])
            geo_grid_plan.append(["zip", city, z, f"{slug}-{z}-real-estate", "ZIP Hub", "High", "Planned"])
            
        # 3. Discover Neighborhoods via Mock OSM nodes
        subs = osm_suburbs.get(city, [])
        for sub in subs:
            if sub.lower() not in discovered_neighborhoods:
                new_neighborhoods.append([sub, city, "Planned"])
                discovered_neighborhoods.add(sub.lower())
                
            sub_slug = sf.get_slug(sub)
            geo_dataset.append([sub_slug, sub, "neighborhood", city, "", "", "", "Los Angeles", "CA", "Active"])
            geo_grid_plan.append(["neighborhood", city, sub, f"{sub_slug}-homes-for-sale", "Neighborhood Hub", "High", "Planned"])

    # existing neighborhoods map to geo grid plan too
    for n in neighborhoods:
        if not n or len(n) < 2: continue
        hood = n[0]
        city = n[1]
        hood_slug = sf.get_slug(hood)
        geo_grid_plan.append(["neighborhood", city, hood, f"{hood_slug}-homes-for-sale", "Neighborhood Hub", "High", "Planned"])
        geo_dataset.append([hood_slug, hood, "neighborhood", city, "", "", "", "Los Angeles", "CA", "Active"])

    # Push to Geo_Dataset
    if geo_dataset:
        headers = sf.PHASE1_TABS['Geo_Dataset']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Geo_Dataset'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(geo_dataset, 0)}
        ).execute()

    # Push to Zip_Pages
    if zip_pages:
        headers = sf.PHASE1_TABS['Zip_Pages']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Zip_Pages'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(zip_pages, 2)}
        ).execute()

    # Push to Geo_Grid_Plan
    if geo_grid_plan:
        headers = sf.PHASE1_TABS['Geo_Grid_Plan']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Geo_Grid_Plan'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(geo_grid_plan, 3)}
        ).execute()
        
    # Inject new neighborhoods
    if new_neighborhoods:
        service.spreadsheets().values().append(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Neighborhoods'!A2",
            valueInputOption='RAW', body={'values': new_neighborhoods}
        ).execute()
        print(f"🗺️ Discovered {len(new_neighborhoods)} new micro-neighborhoods from geospatial nodes.")

    print(f"✅ Geo-Grid Discovery Complete. Mapped {len(geo_dataset)} geo-locations.")
