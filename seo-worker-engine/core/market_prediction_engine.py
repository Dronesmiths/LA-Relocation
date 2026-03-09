import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_market_predictions():
    print("📈 Initializing Market Prediction Engine...")

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

    signals = []
    predictions = []
    insights = []
    opportunities = []

    for city in cities:
        # Mock Market Signals
        price = random.randint(350000, 950000)
        sqft = round(price / random.randint(1200, 2500))
        yearly_change = round(random.uniform(-5.0, 15.0), 1)
        inventory_change = round(random.uniform(-10.0, 20.0), 1)
        dom = random.randint(15, 60)
        buyer_demand_score = random.randint(1, 100)
        
        signals.append([
            city, "Citywide", str(price), str(sqft), str(inventory_change), str(dom), 
            f"{yearly_change}%", f"{round(yearly_change/4, 1)}%", "Stable", "Average", "Positive", "Positive", datetime.now().isoformat()
        ])
        
        # Calculate Momentum Score
        score = 50 + (yearly_change * 2) - (inventory_change) + (buyer_demand_score * 0.2)
        score = min(max(int(score), 1), 100)

        # Labels
        if score > 80: trend = "rising_fast"
        elif score > 60: trend = "moderately_rising"
        elif score > 40: trend = "stable"
        else: trend = "cooling"

        predictions.append([
            city, "Citywide", str(score), trend, "High", "Price Growth + Low Inventory" if trend in ["rising_fast"] else "Supply Dynamics", 
            "Interest Rates", datetime.now().isoformat(), "High" if score > 70 else "Medium"
        ])

        if trend == "rising_fast":
            insights.append([city, "price_momentum", f"Home prices are rising faster in {city} with strong buyer demand.", "price_growth + high_demand", "market_forecast_page", "High"])
            
            slug = f"{sf.get_slug(city)}-housing-market-forecast-2026"
            opportunities.append([city, "Citywide", slug, "housing market forecast", "market_forecast_page", "High", "No", "Yes"])
        
        # Generate some comparison forecast pages
        if random.random() > 0.7:
            comp_city = random.choice([c for c in cities if c != city])
            slug_comp = f"{sf.get_slug(city)}-vs-{sf.get_slug(comp_city)}-housing-market-forecast"
            opportunities.append([city, "Comparison", slug_comp, f"{city} vs {comp_city} housing market forecast", "market_comparison_forecast", "High", "No", "Yes"])

    # Push to Sheets
    if signals:
        headers_signals = sf.PHASE1_TABS['Market_Signals']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Market_Signals'!A1", valueInputOption='RAW', body={'values': headers_signals + signals}).execute()
        
    if predictions:
        headers_preds = sf.PHASE1_TABS['Market_Predictions']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Market_Predictions'!A1", valueInputOption='RAW', body={'values': headers_preds + predictions}).execute()
        
    if insights:
        headers_insights = sf.PHASE1_TABS['Trend_Insights']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Trend_Insights'!A1", valueInputOption='RAW', body={'values': headers_insights + insights}).execute()
        
    if opportunities:
        headers_pages = sf.PHASE1_TABS['Prediction_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Prediction_Pages'!A1", valueInputOption='RAW', body={'values': headers_pages + opportunities}).execute()

    print(f"✅ Market Prediction Engine identified {len(insights)} insights and queued {len(opportunities)} prediction pages.")
