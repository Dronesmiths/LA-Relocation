import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_topic_authority():
    print("🧠 Initializing Topical Authority Layer...")

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

    pillars = []
    clusters = []
    pages = []
    links = []

    core_clusters = [
        "cost_of_living", "crime_and_safety", "best_neighborhoods", "schools",
        "things_to_do", "housing_market_trends", "pros_and_cons", "moving_to_city"
    ]

    for city in cities:
        c_slug = sf.get_slug(city)
        
        # 1. Define Primary Pillars
        pillar_slug = f"living-in-{c_slug}-california"
        pillars.append([
            city, f"living_in_{c_slug}", pillar_slug, "city_lifestyle", "High", "No", "Yes"
        ])
        
        # 2. Build Cluster Pages
        for cluster in core_clusters:
            # We don't generate all chapters for all cities exactly the same randomly mock it up
            if random.random() > 0.15:
                cluster_slug = f"{cluster.replace('_', '-')}-in-{c_slug}"
                
                clusters.append([
                    city, pillar_slug, cluster, cluster_slug, "support_article", "High", "No", "Yes"
                ])
                
                pages.append([
                    city, cluster_slug, "support_article", pillar_slug, "High", "No", "Yes"
                ])
                
                # Bi-directional linking map
                links.append([
                    f"/{cluster_slug}/", f"/{pillar_slug}/", "parent_pillar_link", "High"
                ])
                links.append([
                    f"/{pillar_slug}/", f"/{cluster_slug}/", "cluster_support_link", "Medium"
                ])

    if pillars:
        headers = sf.PHASE1_TABS['Topic_Pillars']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Topic_Pillars'!A1", valueInputOption='RAW', body={'values': headers + pillars}).execute()

    if clusters:
        headers = sf.PHASE1_TABS['Topic_Clusters']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Topic_Clusters'!A1", valueInputOption='RAW', body={'values': headers + clusters}).execute()

    if pages:
        headers = sf.PHASE1_TABS['Topic_Pages']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Topic_Pages'!A1", valueInputOption='RAW', body={'values': headers + pages}).execute()

    if links:
        headers = sf.PHASE1_TABS['Topic_Links']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Topic_Links'!A1", valueInputOption='RAW', body={'values': headers + links}).execute()

    print(f"✅ Topical Authority Generation complete: Mapped {len(pillars)} Pillars and {len(clusters)} Support Clusters.")
