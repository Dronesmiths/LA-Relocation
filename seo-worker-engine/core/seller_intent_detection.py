import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def detect_seller_intent():
    print("🏡 Initializing Seller Intent Engine...")

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

    queries = []
    insights = []
    pages = []
    leads = []

    mock_queries = [
        {"q": "what is my home worth", "intent": "home_value"},
        {"q": "best time to sell", "intent": "market_timing"},
        {"q": "housing market forecast", "intent": "market_forecast"}
    ]

    for city in cities:
        for mq in mock_queries:
            count = random.randint(10, 100)
            queries.append([
                f"{mq['q']} in {city}", city, "Citywide", mq['intent'], str(count), "AutoSuggest", "High" if count > 50 else "Medium"
            ])

        # Generate Seller Insights
        if random.random() > 0.5:
            insights.append([
                city, "Citywide", "seller_opportunity", "Low inventory and steady demand may favor sellers",
                "inventory_low + demand_high", f"{sf.get_slug(city)}-seller-guide", "High"
            ])

        # Generate Seller Page Opportunities
        slug_value = f"what-is-my-home-worth-{sf.get_slug(city)}"
        pages.append([city, "Citywide", slug_value, "home value pages", "seller_page", "High", "No", "Yes"])
        
        slug_timing = f"best-time-to-sell-in-{sf.get_slug(city)}"
        pages.append([city, "Citywide", slug_timing, "market timing pages", "seller_page", "Medium", "No", "Yes"])

        # Generates some mock leads
        if random.random() > 0.7:
            leads.append([
                datetime.now().isoformat(), city, "Citywide", "Single Family", "home_value_request", "Web Form", "New"
            ])

    if queries:
        headers_queries = sf.PHASE1_TABS['Seller_Intent_Queries']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Seller_Intent_Queries'!A1", valueInputOption='RAW', body={'values': headers_queries + queries}).execute()

    if insights:
        headers_insights = sf.PHASE1_TABS['Seller_Insights']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Seller_Insights'!A1", valueInputOption='RAW', body={'values': headers_insights + insights}).execute()

    if pages:
        headers_pages = sf.PHASE1_TABS['Seller_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Seller_Pages'!A1", valueInputOption='RAW', body={'values': headers_pages + pages}).execute()

    if leads:
        headers_leads = sf.PHASE1_TABS['Home_Value_Leads']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Home_Value_Leads'!A1", valueInputOption='RAW', body={'values': headers_leads + leads}).execute()

    print(f"✅ Seller Intent Engine logged queries, generated {len(insights)} insights, and queued {len(pages)} seller page targets.")
