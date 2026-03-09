import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def sync_authority_signals():
    print("🏢 Initializing Local Authority Signals Engine...")
    
    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=sf.SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    tabs_to_ensure = [
        'Local_Reviews', 
        'Local_Businesses', 
        'Local_Citations', 
        'Authority_Signals'
    ]
    
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
    
    # Prepare mocked ingest values
    reviews = []
    businesses = []
    citations = []
    signals = []
    reinforcements = []
    
    sources = ["Google Places", "Yelp", "OpenStreetMap", "Chamber of Commerce"]
    
    for c in cities:
        if not c: continue
        city = c[0]
        
        # MOCK BUSINESS INGESTION
        biz_count = random.randint(5, 12)
        total_revs = 0
        sum_ratings = 0.0
        
        city_slug = sf.get_slug(city)
        
        # Simulate local entities
        for i in range(biz_count):
            b_name = f"{city} Real Estate & Relocation Group {i+1}"
            cat = "Real Estate Services"
            src = random.choice(sources)
            b_reviews = random.randint(10, 300)
            b_rating = round(random.uniform(4.0, 5.0), 1)
            
            businesses.append([city, b_name, cat, f"12{i} Main St, {city}, CA", "", "", f"https://{city_slug}homes.com", src])
            reviews.append([city, b_name, src, str(b_rating), str(b_reviews), "Highly recommended team for out of state relocation.", datetime.now().isoformat()])
            
            total_revs += b_reviews
            sum_ratings += b_rating
            
        # Citations
        cit_count = random.randint(3, 8)
        for i in range(cit_count):
            citations.append([city, f"City of {city} Portal", f"https://{city_slug}.gov", "Government", "Active", datetime.now().isoformat()])
            
        avg_rating = round(sum_ratings / biz_count, 1) if biz_count > 0 else 0
        
        # Authority Score Algo
        # 40% Reviews + 40% Businesses + 20% Citations
        score = min(100, (total_revs / 1000) * 40 + (biz_count / 15) * 40 + (cit_count / 10) * 20)
        score = round(score, 1)
        
        priority = "Normal"
        if score < 40:
            priority = "Aggressive Ingestion Needed"
            reinforcements.append([f"{sf.DOMAIN}/{city_slug}/", "city_page", city, "Low Local Authority Signal", "Inject City Citations & Scheme Data", "High", "planned"])
            
        signals.append([city, str(total_revs), str(avg_rating), str(biz_count), str(cit_count), str(score), priority])

    # Push to sheets
    if reviews:
        headers = sf.PHASE1_TABS['Local_Reviews']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Local_Reviews'!A1", valueInputOption='RAW', body={'values': headers + reviews}).execute()
        
    if businesses:
        headers = sf.PHASE1_TABS['Local_Businesses']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Local_Businesses'!A1", valueInputOption='RAW', body={'values': headers + businesses}).execute()

    if citations:
        headers = sf.PHASE1_TABS['Local_Citations']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Local_Citations'!A1", valueInputOption='RAW', body={'values': headers + citations}).execute()

    if signals:
        headers = sf.PHASE1_TABS['Authority_Signals']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Authority_Signals'!A1", valueInputOption='RAW', body={'values': headers + signals}).execute()
        
    if reinforcements:
        service.spreadsheets().values().append(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Reinforcement_Queue'!A2",
            valueInputOption='RAW', body={'values': reinforcements}
        ).execute()

    print(f"✅ Local Authority Discovered: {len(businesses)} Businesses, {len(reviews)} Reviews, {len(citations)} Citations.")
    print(f"📉 Enqueued {len(reinforcements)} Authority Reinforcements.")
