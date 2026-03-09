import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_discovery_pages():
    print("🌍 Initializing Property Discovery Intelligence Engine...")

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
        
    discovery_topics = []
    discovery_pages = []
    discovery_clusters = []

    # Map core exploration semantic queries typical of SoCal Relocation
    intents = [
        ("affordable cities near los angeles", "affordability", "High", "affordable cities near los angeles"),
        ("best cities for families near los angeles", "family", "High", "safest cities near los angeles with good schools"),
        ("best commuter cities near los angeles", "commute", "High", "cities within 60 miles of los angeles"),
        ("cities with land near los angeles", "lifestyle", "Medium", "horse property near los angeles"),
        ("best investment cities near los angeles", "investment", "Medium", "where are home prices rising near los angeles")
    ]
    
    clusters = [
        ("affordable_cities", "buyer", "Palmdale, Lancaster", "affordable-cities-near-los-angeles"),
        ("family_friendly", "relocation", "Santa Clarita, Palmdale", "best-cities-for-families-near-los-angeles"),
        ("commuter_cities", "relocation", "Burbank, Glendale, Palmdale", "best-commuter-cities-near-los-angeles"),
        ("investment_markets", "investment", "Lancaster, Palmdale", "best-investment-cities-near-los-angeles")
    ]

    for topic, category, prio, example in intents:
        slug = topic.replace(" ", "-").lower()
        discovery_topics.append([topic, category, prio, example])
        
        # Decide which cluster this belongs to
        cluster_assignment = "affordable_cities"
        if category == "family":
            cluster_assignment = "family_friendly"
        elif category == "commute":
            cluster_assignment = "commuter_cities"
        elif category == "investment":
            cluster_assignment = "investment_markets"
            
        discovery_pages.append([slug, cluster_assignment, prio, "No", "Yes"])

    for cluster_name, i_type, c_included, p_slug in clusters:
        discovery_clusters.append([cluster_name, i_type, c_included, p_slug])

    # PUSH TO GOOGLE SHEETS
    if discovery_topics:
        headers = sf.PHASE1_TABS.get('Discovery_Topics', [['Topic', 'Category', 'Priority', 'Example_Query']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Discovery_Topics'!A1", valueInputOption='RAW', body={'values': headers + discovery_topics}).execute()

    if discovery_clusters:
        headers = sf.PHASE1_TABS.get('Discovery_Clusters', [['Cluster', 'Intent_Type', 'Cities_Included', 'Primary_Slug']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Discovery_Clusters'!A1", valueInputOption='RAW', body={'values': headers + discovery_clusters}).execute()

    if discovery_pages:
        headers = sf.PHASE1_TABS.get('Discovery_Pages', [['Slug', 'Cluster', 'Priority', 'Exists', 'Needs_Generation']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Discovery_Pages'!A1", valueInputOption='RAW', body={'values': headers + discovery_pages}).execute()

    print(f"✅ Property Discovery Built. Organized {len(discovery_topics)} semantic hubs linking back to City Nodes.")
