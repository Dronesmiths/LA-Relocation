import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_comparisons():
    print("⚖️ Initializing Comparative Intelligence Engine...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=sf.SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    tabs_to_ensure = ['City_Comparisons']
    new_tabs = [{'addSheet': {'properties': {'title': t}}} for t in tabs_to_ensure if t not in existing_sheets]
    if new_tabs:
        service.spreadsheets().batchUpdate(spreadsheetId=sf.SPREADSHEET_ID, body={'requests': new_tabs}).execute()

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    cities_data = get_tab_data('Cities')
    cities = [c[0] for c in cities_data if c]
    
    comparisons = []
    
    # Custom initial pairs per specs
    priority_pairs = [
        ("Palmdale", "Lancaster"),
        ("Palmdale", "Santa Clarita"),
        ("Lancaster", "Quartz Hill"),
        ("Palmdale", "Victorville"),
        ("Lancaster", "Victorville")
    ]
    
    existing_comparisons = set()

    for city_a, city_b in priority_pairs:
        # Mocking data per prompt
        price_a = random.randint(400, 800) * 1000
        price_b = random.randint(400, 800) * 1000
        crime_a = random.randint(40, 70)
        crime_b = random.randint(40, 70)
        school_a = round(random.uniform(5.0, 9.0), 1)
        school_b = round(random.uniform(5.0, 9.0), 1)
        commute_a = random.randint(45, 90)
        commute_b = random.randint(45, 90)
        
        # 1. Housing Score Winner (Lower = better affordability for buyer logic)
        score_housing_a = 100000 / price_a * 100
        score_housing_b = 100000 / price_b * 100
        housing_winner = city_a if score_housing_a > score_housing_b else city_b
        
        # 2. Safety Winner (Lower index = higher safety score)
        safety_a = 100 - crime_a
        safety_b = 100 - crime_b
        safety_winner = city_a if safety_a > safety_b else city_b
        
        # 3. Schools Winner
        school_score_a = (school_a * 0.6) + (30 * 0.4)
        school_score_b = (school_b * 0.6) + (30 * 0.4)
        schools_winner = city_a if school_score_a > school_score_b else city_b
        
        # 4. Commute Winner (lower is better)
        commute_winner = city_a if commute_a < commute_b else city_b
        
        # Calculate final overall score
        # Housing 30%, Safety 25%, Schools 20%, Commute 15%, Lifestyle 10%
        final_score_a = (score_housing_a * 0.3) + (safety_a * 0.25) + (school_score_a * 0.2) + ((100-commute_a)*0.15) + (50 * 0.1)
        final_score_b = (score_housing_b * 0.3) + (safety_b * 0.25) + (school_score_b * 0.2) + ((100-commute_b)*0.15) + (50 * 0.1)
        
        overall_winner = city_a if final_score_a > final_score_b else city_b
        
        slug = sf.get_slug(f"{city_a}-vs-{city_b}")
        
        if slug not in existing_comparisons:
            comparisons.append([
                city_a, city_b, str(random.randint(5, 50)), str(round(abs(price_a - price_b) / price_b * 100, 1)),
                housing_winner, safety_winner, schools_winner, commute_winner, overall_winner, slug, "High", "Active"
            ])
            existing_comparisons.add(slug)

    # Dynamic Discovery Phase
    for ca in cities:
        for cb in cities:
            if ca != cb and f"{ca}-vs-{cb}" not in existing_comparisons and f"{cb}-vs-{ca}" not in existing_comparisons:
                # Randomize distance and prices
                price_a = random.randint(400, 800) * 1000
                price_b = random.randint(400, 800) * 1000
                price_diff = abs(price_a - price_b) / max(price_a, price_b)
                distance = random.randint(5, 120)
                
                # Rule: compare only if distance < 70 miles or price diff < 30%
                if distance < 70 or price_diff < 0.3:
                    comparisons.append([
                        ca, cb, str(distance), str(round(price_diff*100, 1)), ca, cb, cb, ca, ca,
                        sf.get_slug(f"{ca}-vs-{cb}"), "Medium", "Planned"
                    ])
                    existing_comparisons.add(f"{ca}-vs-{cb}")

    # Push to Sheets
    if comparisons:
        headers = sf.PHASE1_TABS['City_Comparisons']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'City_Comparisons'!A1",
            valueInputOption='RAW', body={'values': headers + comparisons}
        ).execute()

    print(f"✅ Comparative Intelligence Engine built {len(comparisons)} strategic City vs City comparison matrices.")
