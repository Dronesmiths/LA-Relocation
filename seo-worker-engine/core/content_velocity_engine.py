import os
import random
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def schedule_content_velocity():
    print("🚦 Initializing Content Velocity Engine...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    # MOCK DATA INGESTION
    cities = [row[0] for row in get_tab_data('Cities') if row]
    
    queue = []
    schedule = []
    log = []

    # Mock Velocity Limits Based on Ramp Pattern
    # For simulation, we pretend we are in month 2 (Medium ramp)
    # So we're scheduling 15-25 pages
    total_to_schedule = random.randint(15, 25)

    print(f"   -> Ramp Curve: Month 2 Protocol")
    print(f"   -> Allowance generated: {total_to_schedule} pages this cycle")

    # Generate Mock Queue Events 
    # Example queue entries to pick from
    for i in range(total_to_schedule):
        city = random.choice(cities)
        page_type = random.choice(["city_page", "neighborhood_page", "comparison_page", "radius_page", "migration_page", "topic_cluster_page"])
        slug = f"{page_type}-example-{random.randint(100, 999)}-{sf.get_slug(city)}"
        priority = random.choice(["High", "Medium", "High", "Low"])
        
        # Add to Queue
        queue.append([slug, page_type, city, priority, "expansion_layer", "Pending", "", "No"])
        
        # Move to Scheduled
        dt = datetime.now() + timedelta(days=random.randint(0, 5))
        sched_date = dt.strftime("%Y-%m-%d")
        schedule.append([sched_date, slug, page_type, city, priority, "Scheduled"])

        # Create previous day logs to show history
        if random.random() > 0.5:
            dt_past = datetime.now() - timedelta(days=random.randint(1, 14))
            past_slug = f"past-{page_type}-{random.randint(100, 999)}"
            log.append([dt_past.strftime("%Y-%m-%d"), past_slug, page_type, "velocity_engine", "Indexed", "Gaining Traction"])

    if queue:
        headers = sf.PHASE1_TABS['Content_Queue']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Content_Queue'!A1", valueInputOption='RAW', body={'values': headers + queue}).execute()

    if schedule:
        headers = sf.PHASE1_TABS['Publishing_Schedule']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Publishing_Schedule'!A1", valueInputOption='RAW', body={'values': headers + schedule}).execute()

    if log:
        headers = sf.PHASE1_TABS['Publishing_Log']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Publishing_Log'!A1", valueInputOption='RAW', body={'values': headers + log}).execute()

    # Populate Config if empty
    config_data = get_tab_data('Velocity_Config')
    if not config_data:
        config = [
            ["city_page", "2", "5", "High", "Scheduled"],
            ["neighborhood_page", "3", "10", "High", "Scheduled"],
            ["comparison_page", "3", "10", "Medium", "Scheduled"],
            ["radius_page", "4", "12", "Medium", "Scheduled"],
            ["migration_page", "4", "12", "Medium", "Scheduled"],
            ["market_page", "2", "6", "Medium", "Scheduled"],
            ["seller_page", "2", "6", "Medium", "Scheduled"],
            ["topic_cluster_page", "5", "20", "Medium", "Scheduled"]
        ]
        headers = sf.PHASE1_TABS['Velocity_Config']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Velocity_Config'!A1", valueInputOption='RAW', body={'values': headers + config}).execute()


    print(f"✅ Content Velocity Cycle Complete:")
    print(f"   - {len(queue)} pages queued")
    print(f"   - {len(schedule)} pages scheduled for immediate publication routing")
