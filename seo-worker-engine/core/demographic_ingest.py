import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

def fetch_demographic_data(city):
    """
    Simulates fetching data from US Census / ACS.
    In production, this would use requests to call the Census API.
    """
    # Mock data with some randomization for variety
    base_population = random.randint(100000, 250000)
    growth = random.uniform(0.5, 4.5)
    income = random.randint(55000, 95000)
    
    return {
        'City': city,
        'Population': f"{base_population:,}",
        'Population_Growth': f"+{growth:.1f}%",
        'Median_Age': str(random.randint(28, 42)),
        'Median_Household_Income': f"${income:,}",
        'Owner_Occupied_Percent': f"{random.randint(55, 75)}%",
        'Renter_Occupied_Percent': f"{random.randint(25, 45)}%",
        'Median_Rent': f"${random.randint(1600, 2800):,}",
        'Median_Home_Value': f"${random.randint(400000, 850000):,}",
        'Households_With_Children': f"{random.randint(30, 50)}%",
        'Education_Level': f"{random.randint(25, 45)}% Bachelor's or Higher",
        'Last_Updated': datetime.now().strftime("%Y-%m-%d"),
        'Data_Source': "US Census ACS 2024 (Simulated)"
    }

def ingest_demographics(spreadsheet_id, service_account_file):
    """Main ingestion logic."""
    print(f"📈 Starting Demographic Ingestion for Sheet: {spreadsheet_id}")
    
    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    # 1. Identify cities from 'Sitemap Inventory' or '📍 LOCATIONS'
    # We'll try 'Sitemap Inventory' first as it seems to be the main registry
    inventory = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="'Sitemap Inventory'!A2:B").execute().get('values', [])
    
    cities = []
    for row in inventory:
        if len(row) >= 2 and (row[1] == '📍' or row[1] == 'City'):
            # Extract city name from URL or name
            url = row[0]
            city_slug = url.strip('/').split('/')[-1]
            city_name = city_slug.replace('-', ' ').title()
            if city_name not in cities and 'Blog' not in city_name:
                cities.append(city_name)

    if not cities:
        # Fallback to known list if sheet is empty or unparseable
        cities = ['Palmdale', 'Lancaster', 'Burbank', 'Glendale', 'Santa Clarita', 'Long Beach']

    print(f"Found {len(cities)} cities to process.")
    
    demo_data = []
    for city in cities:
        print(f"Processing {city}...")
        try:
            data = fetch_demographic_data(city)
            demo_data.append([
                data['City'], data['Population'], data['Population_Growth'], data['Median_Age'],
                data['Median_Household_Income'], data['Owner_Occupied_Percent'], data['Renter_Occupied_Percent'],
                data['Median_Rent'], data['Median_Home_Value'], data['Households_With_Children'],
                data['Education_Level'], data['Last_Updated'], data['Data_Source']
            ])
        except Exception as e:
            print(f"Error processing {city}: {e}")

    # 2. Ensure Demographic_Data tab exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
    
    if 'Demographic_Data' not in existing_sheets:
        print("Creating 'Demographic_Data' tab...")
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={
            'requests': [{'addSheet': {'properties': {'title': 'Demographic_Data'}}}]
        }).execute()

    header = [['City', 'Population', 'Population_Growth', 'Median_Age', 'Median_Household_Income', 
               'Owner_Occupied_Percent', 'Renter_Occupied_Percent', 'Median_Rent', 'Median_Home_Value', 
               'Households_With_Children', 'Education_Level', 'Last_Updated', 'Data_Source']]
    
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, 
        range="'Demographic_Data'!A1",
        valueInputOption='RAW',
        body={'values': header + demo_data}
    ).execute()
    
    print("✅ Demographic Data Ingested Successfully.")


if __name__ == "__main__":
    # This allow running as a standalone script if needed
    import sys
    if len(sys.argv) > 2:
        ingest_demographics(sys.argv[1], sys.argv[2])
