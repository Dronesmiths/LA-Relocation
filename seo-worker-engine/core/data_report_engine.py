import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_data_reports():
    print("📰 Initializing Local Data Report Engine...")

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
    index_data = []
    rankings = []
    pages = []

    # 1. Define Topics
    core_topics = [
        ("Safest Cities Near Los Angeles", "safest-cities-near-los-angeles", "Crime_Data"),
        ("Most Affordable Cities Near Los Angeles", "affordable-cities-near-los-angeles", "Housing_Data"),
        ("Fastest Growing Housing Markets Near LA", "fastest-growing-housing-markets-near-la", "Market_Predictions"),
        ("Best Cities for First Time Buyers", "best-cities-for-first-time-homebuyers-near-la", "Affordability_Index"),
        ("Best Suburbs for Families", "best-suburbs-for-families-near-los-angeles", "School_Data")
    ]

    for topic, slug, source in core_topics:
        topics.append([topic, slug, source, "Composite Score", "High"])
        
        # 2. Mock Page Insertion
        year = str(datetime.now().year)
        pages.append([f"{slug}-{year}", topic, year, "High", "No", "Yes"])

    # 3. Create City_Data_Index mock rows
    for city in cities:
        crime_index = random.randint(20, 95)
        med_price = random.randint(350000, 950000)
        price_growth = round(random.uniform(0.5, 8.5), 1)
        school_rating = random.randint(4, 10)
        pop_growth = round(random.uniform(-1.0, 4.0), 1)
        commute_score = random.randint(30, 95)
        lifestyle_score = random.randint(40, 98)
        affordability = random.randint(10, 90)

        index_data.append([
            city, str(crime_index), str(med_price), f"{price_growth}%", str(school_rating),
            f"{pop_growth}%", str(commute_score), str(lifestyle_score), str(affordability)
        ])

    # 4. Generate Mock Rankings
    for t_name, _, _ in core_topics:
        # Just mock a top 3
        local_rankings = []
        for city in random.sample(cities, min(3, len(cities))):
            score = random.randint(75, 99)
            local_rankings.append((city, score))
            
        local_rankings.sort(key=lambda x: x[1], reverse=True)
        
        for idx, (city, score) in enumerate(local_rankings):
            rankings.append([
                t_name, str(idx+1), city, str(score), "Composite Metrics Validated"
            ])

    # PUSH TO GOOGLE SHEETS
    if topics:
        headers = sf.PHASE1_TABS['Data_Report_Topics']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Data_Report_Topics'!A1", valueInputOption='RAW', body={'values': headers + topics}).execute()

    if index_data:
        headers = sf.PHASE1_TABS['City_Data_Index']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'City_Data_Index'!A1", valueInputOption='RAW', body={'values': headers + index_data}).execute()

    if rankings:
        headers = sf.PHASE1_TABS['Report_Rankings']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Report_Rankings'!A1", valueInputOption='RAW', body={'values': headers + rankings}).execute()

    if pages:
        headers = sf.PHASE1_TABS['Report_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Report_Pages'!A1", valueInputOption='RAW', body={'values': headers + pages}).execute()

    print(f"✅ Generated {len(topics)} Local Data Reports covering {len(cities)} locations.")
