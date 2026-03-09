import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_migration_pages():
    print("🚚 Initializing Migration Intelligence Engine...")

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

    flows = []
    signals = []
    insights = []
    pages = []

    origins = ["Los Angeles", "Burbank", "Pasadena", "Glendale", "San Fernando"]

    for origin in origins:
        for dest in cities:
            if origin == dest: continue

            # generate mock migration flows
            if random.random() > 0.6: 
                dist = random.randint(15, 75)
                price_diff = random.randint(100000, 500000)
                commute_diff = f"-{random.randint(10, 45)} mins"
                search_demand = random.randint(50, 500)
                score = (search_demand * 0.4) + (price_diff / 10000)

                priority = "High" if score > 80 else "Medium"
                
                flows.append([
                    origin, dest, str(dist), f"-${price_diff}", "Lower", "Better", commute_diff, "Accelerating", str(search_demand), priority
                ])

                # mock detection signal
                if random.random() > 0.5:
                    signals.append([
                        f"MIG-{random.randint(1000,9999)}", "Buyer_Query", origin, dest, str(random.randint(70, 99)), datetime.now().isoformat()
                    ])

                if price_diff > 300000:
                    insights.append([
                        origin, dest, "affordability_shift", f"Buyers leaving {origin} are targeting {dest} for significant housing savings.", "price_gap + buyer_queries", f"moving-from-{sf.get_slug(origin)}-to-{sf.get_slug(dest)}", priority
                    ])

                slug = f"moving-from-{sf.get_slug(origin)}-to-{sf.get_slug(dest)}"
                pages.append([
                    origin, dest, slug, f"Cost of Living: {origin} vs {dest}", "migration_page", priority, "No", "Yes"
                ])

    if flows:
        headers_flows = sf.PHASE1_TABS['Migration_Flows']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Migration_Flows'!A1", valueInputOption='RAW', body={'values': headers_flows + flows}).execute()

    if signals:
        headers_signals = sf.PHASE1_TABS['Migration_Signals']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Migration_Signals'!A1", valueInputOption='RAW', body={'values': headers_signals + signals}).execute()

    if insights:
        headers_insights = sf.PHASE1_TABS['Migration_Insights']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Migration_Insights'!A1", valueInputOption='RAW', body={'values': headers_insights + insights}).execute()

    if pages:
        headers_pages = sf.PHASE1_TABS['Migration_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Migration_Pages'!A1", valueInputOption='RAW', body={'values': headers_pages + pages}).execute()

    print(f"✅ Migration Intelligence Engine mapped {len(flows)} relocation flows and queued {len(pages)} migration targets.")
