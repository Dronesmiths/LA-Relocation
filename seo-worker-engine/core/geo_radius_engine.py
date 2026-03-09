import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_radius_pages():
    print("📍 Initializing Geo Grid Radius Engine...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    hubs_data = get_tab_data('Radius_Hubs')
    cities_data = get_tab_data('Cities')
    
    if not hubs_data:
        default_hubs = [
            ["Los Angeles", "metro", "34.052", "-118.243", "Los Angeles", "CA", "High", "Active"],
            ["Burbank", "employment_center", "34.180", "-118.308", "Los Angeles", "CA", "High", "Active"],
            ["Santa Clarita", "lifestyle_hub", "34.391", "-118.542", "Los Angeles", "CA", "Medium", "Active"],
            ["LAX", "airport", "33.941", "-118.408", "Los Angeles", "CA", "High", "Active"],
        ]
        headers_hubs = sf.PHASE1_TABS['Radius_Hubs']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Radius_Hubs'!A1",
            valueInputOption='RAW', body={'values': headers_hubs + default_hubs}
        ).execute()
        hubs_data = default_hubs

    radius_pairs = []
    radius_pages = []
    
    existing_pages = set()

    angles = [
        {"angle": "best suburbs within 50 miles", "type": "relocation", "format": "best-suburbs-within-50-miles-of-{hub}"},
        {"angle": "affordable cities near", "type": "affordability", "format": "affordable-cities-near-{hub}"},
        {"angle": "safest cities near", "type": "safety", "format": "safest-cities-near-{hub}"},
        {"angle": "cities within 30 minutes", "type": "commute", "format": "cities-within-30-minutes-of-{hub}"},
        {"angle": "homes near airport", "type": "buyer", "format": "homes-near-{hub}"},
        {"angle": "commuter towns near", "type": "commute", "format": "commuter-towns-near-{hub}"}
    ]

    for hub_row in hubs_data:
        hub_name = hub_row[0]
        
        hub_angles = random.sample(angles, k=random.randint(2, 4))
        
        for city_row in cities_data[:5]:
            city_name = city_row[0]
            if city_name != hub_name:
                dist = random.randint(5, 60)
                time = dist + random.randint(-5, 15)
                rel_type = "Nearby Suburb" if dist <= 20 else ("Within 50 Miles" if dist <= 50 else "Commuter City")
                radius_pairs.append([
                    hub_name, city_name, "City", str(dist), f"{time} mins", rel_type, "Medium", "Active"
                ])
                
        for ang in hub_angles:
            slug = ang["format"].replace("{hub}", sf.get_slug(hub_name))
            if slug not in existing_pages:
                radius_pages.append([
                    hub_name, "Multiple", ang["angle"], slug, ang["type"], "High", "No", "Yes"
                ])
                existing_pages.add(slug)

    if radius_pairs:
        headers_pairs = sf.PHASE1_TABS['Radius_Pairs']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Radius_Pairs'!A1",
            valueInputOption='RAW', body={'values': headers_pairs + radius_pairs}
        ).execute()
        
    if radius_pages:
        headers_pages = sf.PHASE1_TABS['Radius_Pages']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Radius_Pages'!A1",
            valueInputOption='RAW', body={'values': headers_pages + radius_pages}
        ).execute()

    print(f"✅ Geo Grid Radius Engine generated {len(radius_pages)} new radius page opportunities.")
