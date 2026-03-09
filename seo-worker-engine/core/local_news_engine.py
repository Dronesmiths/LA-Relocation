import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_local_news():
    print("📰 Initializing Local News Content Engine...")

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
    signals = []
    pages = []
    logs = []

    # 1. Define News Topics
    core_topics = [
        ("market_update", "housing-market-update", "report_summary", "High"),
        ("inventory_update", "housing-inventory-update", "data_alert", "High"),
        ("migration_trend", "relocation-trend", "trend_analysis", "High"),
        ("price_change", "home-price-update", "market_flash", "Medium"),
        ("new_construction", "new-housing-development", "community_news", "Medium")
    ]

    for topic, slug, fmt, prio in core_topics:
        topics.append([topic, slug, fmt, prio])
        
    # 2. Mock Detecting Signals
    # We take a sample so it doesn't spam every city every time
    for city in random.sample(cities, min(3, len(cities))):
        c_slug = sf.get_slug(city)
        date_str = datetime.now().strftime('%B %Y')
        year_str = datetime.now().strftime('%Y')
        
        signal_examples = [
            ("price_growth", f"+{random.randint(1, 8)}.%", "housing_data", "High", "price_change", f"{c_slug}-home-price-update-{year_str}"),
            ("inventory_drop", f"-{random.randint(2, 12)}%", "housing_data", "Medium", "inventory_update", f"{c_slug}-housing-inventory-{date_str.replace(' ', '-').lower()}"),
            ("migration_increase", f"+{random.randint(5, 20)}%", "migration_engine", "High", "migration_trend", f"buyers-moving-to-{c_slug}-{year_str}")
        ]
        
        chosen = random.choice(signal_examples)
        
        # Add to Signals
        signals.append([city, chosen[0], chosen[1], chosen[2], chosen[3]])
        
        # Add to Pages
        pages.append([chosen[5], city, chosen[4], chosen[3], "No", "Yes"])
        
        # Add to Log (Assuming it's generated right after or tracking past execution)
        logs.append([datetime.now().strftime("%Y-%m-%d"), chosen[5], chosen[4], "Pending", "N/A"])


    # PUSH TO GOOGLE SHEETS
    if topics:
        headers = sf.PHASE1_TABS['News_Topics']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'News_Topics'!A1", valueInputOption='RAW', body={'values': headers + topics}).execute()

    if signals:
        headers = sf.PHASE1_TABS['News_Signals']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'News_Signals'!A1", valueInputOption='RAW', body={'values': headers + signals}).execute()

    if pages:
        headers = sf.PHASE1_TABS['News_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'News_Pages'!A1", valueInputOption='RAW', body={'values': headers + pages}).execute()

    if logs:
        headers = sf.PHASE1_TABS['News_Log']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'News_Log'!A1", valueInputOption='RAW', body={'values': headers + logs}).execute()

    print(f"✅ News Engine Generated: {len(pages)} Fresh Weekly Story Intercepts Queued.")
